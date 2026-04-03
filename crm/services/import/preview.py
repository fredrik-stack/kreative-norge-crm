from __future__ import annotations

from django.db import transaction

from crm.models import ImportJob, ImportRow, Tenant
from .ai_suggestions import generate_ai_suggestions
from .matchers import match_row_entities
from .normalizers import normalize_import_row
from .parsers import parse_import_job_file
from .validators import validate_normalized_row


def summarize_job_rows(import_job: ImportJob) -> dict:
    rows = list(import_job.rows.all())
    organization_matches = [row.match_result_json.get("organization", {}) for row in rows]
    person_matches = [row.match_result_json.get("person", {}) for row in rows]
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
    }
    return summary


def update_job_preview_status(import_job: ImportJob) -> None:
    summary = summarize_job_rows(import_job)
    import_job.summary_json = summary
    if summary["review_required_rows"] or summary["invalid_rows"]:
        import_job.status = ImportJob.Status.AWAITING_REVIEW
    else:
        import_job.status = ImportJob.Status.PREVIEW_READY
    import_job.save(update_fields=["summary_json", "status", "updated_at"])


def _row_outcome(normalized_payload: dict, errors: list[str], warnings: list[str], matches: dict) -> tuple[str, str]:
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
            ai_suggestions = generate_ai_suggestions(import_job.tenant, normalized_payload, matches)
            row_status, proposed_action = _row_outcome(normalized_payload, errors, warnings, matches)
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
