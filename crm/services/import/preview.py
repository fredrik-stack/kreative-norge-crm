from __future__ import annotations

from django.db import transaction

from crm.models import ImportJob, ImportRow, Tenant
from .ai_suggestions import build_pending_ai_suggestions, generate_ai_suggestions, openai_is_ready
from .matchers import match_row_entities
from .normalizers import normalize_import_row
from .parsers import parse_import_job_file
from .validators import validate_normalized_row

AI_BATCH_SIZE = 1


def _runtime_error_suggestions(*, stage: str, exc: Exception) -> dict:
    error_text = str(exc).strip() or exc.__class__.__name__
    provider_status = f"fallback_{stage}_error"
    return {
        "organization_match_candidates": [],
        "person_match_candidates": [],
        "suggested_fields": {},
        "provider": "heuristic_fallback",
        "diagnostic": {
            "primary_provider": "heuristic_fallback",
            "provider_status": provider_status,
            "fallback_reason": f"{stage}_error",
            "openai_attempted": stage == "openai",
            "openai_error": error_text,
            "useful_suggestion_count": 0,
        },
    }


def _ai_summary(rows: list[ImportRow]) -> dict:
    diagnostics = [row.ai_suggestions_json.get("diagnostic", {}) for row in rows]
    provider_statuses = [str(diagnostic.get("provider_status") or "") for diagnostic in diagnostics]
    pending_count = sum(1 for status in provider_statuses if status == "pending_openai")
    completed_count = sum(1 for status in provider_statuses if status in {"openai", "openai_empty", "openai_web_search"})
    failed_count = sum(1 for status in provider_statuses if status.startswith("fallback_") and status.endswith("_error"))
    if pending_count:
        generation_status = "running" if completed_count or failed_count else "pending"
    elif failed_count and completed_count:
        generation_status = "partially_failed"
    elif failed_count:
        generation_status = "failed"
    else:
        generation_status = "completed"
    return {
        "ai_generation_status": generation_status,
        "rows_ai_pending": pending_count,
        "rows_ai_completed": completed_count,
        "rows_ai_failed": failed_count,
    }


def _eligible_ai_rows(import_job: ImportJob) -> list[ImportRow]:
    return list(
        import_job.rows.exclude(
            row_status__in=[
                ImportRow.RowStatus.INVALID,
                ImportRow.RowStatus.SKIPPED,
                ImportRow.RowStatus.COMMITTED,
            ]
        ).order_by("row_number")
    )


def _reset_rows_for_ai(import_job: ImportJob) -> None:
    for row in _eligible_ai_rows(import_job):
        try:
            row.ai_suggestions_json = build_pending_ai_suggestions(
                import_job.tenant,
                row.normalized_payload_json,
                row.match_result_json,
            )
        except Exception as exc:
            row.ai_suggestions_json = _runtime_error_suggestions(stage="preview", exc=exc)
        row.save(update_fields=["ai_suggestions_json", "updated_at"])


def summarize_job_rows(import_job: ImportJob) -> dict:
    rows = list(import_job.rows.all())
    organization_matches = [row.match_result_json.get("organization", {}) for row in rows]
    person_matches = [row.match_result_json.get("person", {}) for row in rows]
    diagnostics = [row.ai_suggestions_json.get("diagnostic", {}) for row in rows]
    summary = {
        "rows_total": len(rows),
        "valid_rows": sum(1 for row in rows if row.row_status == ImportRow.RowStatus.VALID),
        "invalid_rows": sum(1 for row in rows if row.row_status == ImportRow.RowStatus.INVALID),
        "review_required_rows": sum(1 for row in rows if row.row_status == ImportRow.RowStatus.REVIEW_REQUIRED),
        "skipped_rows": sum(1 for row in rows if row.row_status == ImportRow.RowStatus.SKIPPED),
        "organizations_create": sum(1 for match in organization_matches if match.get("status") == "NEW"),
        "organizations_update": sum(1 for match in organization_matches if match.get("status") == "EXACT"),
        "persons_create": sum(1 for match in person_matches if match.get("status") == "NEW"),
        "persons_update": sum(1 for match in person_matches if match.get("status") == "EXACT"),
        "links_create": sum(
            1
            for row in rows
            if row.normalized_payload_json.get("organization", {}).get("name")
            and row.normalized_payload_json.get("person", {}).get("full_name")
        ),
        "tags_new": len(
            {
                tag.strip().casefold()
                for row in rows
                for tag in (
                    row.normalized_payload_json.get("organization", {}).get("tags", [])
                    + row.normalized_payload_json.get("person", {}).get("tags", [])
                )
                if tag.strip()
            }
        ),
        "internal_tags_new": len(
            {
                tag.strip().casefold()
                for row in rows
                for tag in (
                    row.normalized_payload_json.get("organization", {}).get("internal_tags", [])
                    + row.normalized_payload_json.get("person", {}).get("internal_tags", [])
                )
                if tag.strip()
            }
        ),
        "rows_using_openai": sum(1 for diagnostic in diagnostics if diagnostic.get("provider_status") in {"openai", "openai_empty"}),
        "rows_using_fallback": sum(1 for diagnostic in diagnostics if str(diagnostic.get("provider_status", "")).startswith("fallback")),
        "rows_with_no_useful_ai_suggestions": sum(1 for diagnostic in diagnostics if int(diagnostic.get("useful_suggestion_count", 0) or 0) == 0),
        "rows_with_ai_errors": sum(1 for diagnostic in diagnostics if diagnostic.get("openai_error")),
    }
    summary.update(_ai_summary(rows))
    return summary


def update_job_preview_status(import_job: ImportJob) -> None:
    summary = summarize_job_rows(import_job)
    import_job.summary_json = summary
    if summary["review_required_rows"] or summary["invalid_rows"]:
        import_job.status = ImportJob.Status.AWAITING_REVIEW
    else:
        import_job.status = ImportJob.Status.PREVIEW_READY
    import_job.save(update_fields=["summary_json", "status", "updated_at"])


def _row_outcome(import_mode: str, normalized_payload: dict, errors: list[str], warnings: list[str], matches: dict) -> tuple[str, str]:
    if errors:
        return ImportRow.RowStatus.INVALID, ImportRow.ProposedAction.SKIP

    unknown_taxonomy_warning = any(
        warning.startswith("Unknown category:") or warning.startswith("Unknown subcategory:")
        for warning in warnings
    )
    fuzzy_match = any(match["status"] == "FUZZY" for match in matches.values())
    if unknown_taxonomy_warning or fuzzy_match:
        return ImportRow.RowStatus.REVIEW_REQUIRED, ImportRow.ProposedAction.SKIP

    org_match = matches["organization"]
    person_match = matches["person"]
    if import_mode == ImportJob.ImportMode.ORGANIZATIONS_ONLY and org_match["status"] == "EXACT":
        return ImportRow.RowStatus.REVIEW_REQUIRED, ImportRow.ProposedAction.UPDATE
    if org_match["status"] == "EXACT" or person_match["status"] == "EXACT":
        if org_match["status"] == "EXACT" and person_match["status"] == "EXACT":
            return ImportRow.RowStatus.VALID, ImportRow.ProposedAction.LINK_ONLY
        return ImportRow.RowStatus.VALID, ImportRow.ProposedAction.UPDATE

    return ImportRow.RowStatus.VALID, ImportRow.ProposedAction.CREATE


def run_import_preview(import_job: ImportJob) -> ImportJob:
    if not import_job.file:
        raise ValueError("Import job has no file to preview.")

    parsed_rows = parse_import_job_file(import_job)

    with transaction.atomic():
        import_job.commit_logs.all().delete()
        import_job.rows.all().delete()
        import_job.status = ImportJob.Status.PARSED
        import_job.save(update_fields=["status", "updated_at"])

        row_instances = []
        for index, raw_payload in enumerate(parsed_rows, start=1):
            normalized_payload = normalize_import_row(raw_payload, import_job.import_mode)
            errors, warnings = validate_normalized_row(import_job.tenant, normalized_payload)
            matches = match_row_entities(import_job.tenant, normalized_payload)
            try:
                ai_suggestions = build_pending_ai_suggestions(import_job.tenant, normalized_payload, matches)
            except Exception as exc:
                ai_suggestions = _runtime_error_suggestions(stage="preview", exc=exc)
            row_status, proposed_action = _row_outcome(import_job.import_mode, normalized_payload, errors, warnings, matches)
            row_instances.append(
                ImportRow(
                    import_job=import_job,
                    row_number=index,
                    raw_payload_json=raw_payload,
                    normalized_payload_json=normalized_payload,
                    detected_entities_json={
                        "has_organization": bool(normalized_payload["organization"]["name"]),
                        "has_person": bool(normalized_payload["person"]["full_name"]),
                    },
                    match_result_json=matches,
                    ai_suggestions_json=ai_suggestions,
                    validation_errors_json=errors,
                    warnings_json=warnings,
                    row_status=row_status,
                    proposed_action=proposed_action,
                )
            )
        ImportRow.objects.bulk_create(row_instances)

    update_job_preview_status(import_job)
    return import_job


def generate_import_job_ai(
    import_job: ImportJob,
    *,
    retry_failed: bool = False,
    force_rerun: bool = False,
    batch_size: int = AI_BATCH_SIZE,
) -> ImportJob:
    if batch_size < 1:
        batch_size = AI_BATCH_SIZE

    provider_ready = openai_is_ready()
    if force_rerun:
        if not provider_ready:
            update_job_preview_status(import_job)
            return import_job
        with transaction.atomic():
            _reset_rows_for_ai(import_job)

    pending_rows = []
    for row in import_job.rows.all().order_by("row_number"):
        status = str((row.ai_suggestions_json.get("diagnostic") or {}).get("provider_status") or "")
        if status == "pending_openai" or (retry_failed and status == "fallback_openai_error"):
            pending_rows.append(row)
        if len(pending_rows) >= batch_size:
            break

    if not pending_rows or not provider_ready:
        update_job_preview_status(import_job)
        return import_job

    with transaction.atomic():
        for row in pending_rows:
            try:
                row.ai_suggestions_json = generate_ai_suggestions(
                    import_job.tenant,
                    row.normalized_payload_json,
                    row.match_result_json,
                )
            except Exception as exc:
                row.ai_suggestions_json = _runtime_error_suggestions(stage="openai", exc=exc)
            row.save(update_fields=["ai_suggestions_json", "updated_at"])

    update_job_preview_status(import_job)
    return import_job
