from __future__ import annotations

import csv
import io
from django.core.files.base import ContentFile


def build_error_report_content(import_job) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["row_number", "row_status", "proposed_action", "validation_errors", "warnings"])
    for row in import_job.rows.all().order_by("row_number"):
        if not row.validation_errors_json and not row.warnings_json:
            continue
        writer.writerow(
            [
                row.row_number,
                row.row_status,
                row.proposed_action,
                " | ".join(row.validation_errors_json),
                " | ".join(row.warnings_json),
            ]
        )
    return buffer.getvalue()


def save_error_report(import_job) -> None:
    content = build_error_report_content(import_job)
    filename = f"import-job-{import_job.id}-error-report.csv"
    import_job.error_report_file.save(filename, ContentFile(content.encode("utf-8")), save=False)
    import_job.save(update_fields=["error_report_file", "updated_at"])
