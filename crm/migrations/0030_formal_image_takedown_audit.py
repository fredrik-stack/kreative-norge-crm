# Generated manually from the phase 3E.4 model contract on 2026-08-24.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("crm", "0029_release_selection_revision_gate")]

    operations = [
        migrations.RemoveConstraint(
            model_name="imagereviewevent",
            name="img_evt_previous_contract",
        ),
        migrations.RemoveConstraint(
            model_name="imagereviewevent",
            name="img_evt_selection_kind_contract",
        ),
        migrations.AddField(
            model_name="imagereviewevent",
            name="release_id_snapshot",
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="imagereviewevent",
            name="takedown_reason_code",
            field=models.CharField(
                blank=True,
                choices=[
                    ("rights_request", "Rights request"),
                    ("privacy_safety", "Privacy or safety"),
                    ("legal_compliance", "Legal compliance"),
                    ("editorial_policy", "Editorial policy"),
                ],
                default="",
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="imagereviewevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("selection_locked", "Selection locked"),
                    ("selection_replaced", "Selection replaced"),
                    ("selection_removed_to_fallback", "Selection removed to fallback"),
                    ("selection_restored", "Selection restored"),
                    ("formal_takedown", "Formal takedown"),
                ],
                max_length=29,
            ),
        ),
        migrations.AddConstraint(
            model_name="imagereviewevent",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        event_type="selection_locked",
                        previous_selection_id_snapshot__isnull=True,
                        previous_selection_revision_snapshot__isnull=True,
                    )
                    | models.Q(
                        event_type="selection_replaced",
                        previous_selection_id_snapshot__isnull=False,
                        previous_selection_id_snapshot__gt=0,
                        previous_selection_revision_snapshot__isnull=False,
                        previous_selection_revision_snapshot__gt=0,
                    )
                    | models.Q(
                        event_type="selection_removed_to_fallback",
                        selection_kind_snapshot="system_fallback",
                        previous_selection_id_snapshot__isnull=False,
                        previous_selection_id_snapshot__gt=0,
                        previous_selection_revision_snapshot__isnull=False,
                        previous_selection_revision_snapshot__gt=0,
                    )
                    | models.Q(
                        event_type="selection_restored",
                        previous_selection_id_snapshot__isnull=False,
                        previous_selection_id_snapshot__gt=0,
                        previous_selection_revision_snapshot__isnull=False,
                        previous_selection_revision_snapshot__gt=0,
                    )
                    | models.Q(
                        event_type="formal_takedown",
                        previous_selection_id_snapshot__isnull=False,
                        previous_selection_id_snapshot__gt=0,
                        previous_selection_revision_snapshot__isnull=False,
                        previous_selection_revision_snapshot__gt=0,
                    )
                ),
                name="img_evt_previous_contract",
            ),
        ),
        migrations.AddConstraint(
            model_name="imagereviewevent",
            constraint=models.CheckConstraint(
                condition=(
                    (
                        models.Q(
                            event_type__in=["selection_locked", "selection_replaced"],
                            selection_kind_snapshot="asset",
                            rendition_set_id_snapshot__isnull=False,
                            rendition_set_id_snapshot__gt=0,
                            asset_id_snapshot__isnull=False,
                            asset_id_snapshot__gt=0,
                        )
                        & ~models.Q(asset_checksum_sha256_snapshot="")
                        & ~models.Q(asset_validation_version_snapshot="")
                        & ~models.Q(source_type_snapshot="")
                        & ~models.Q(approval_text_version_snapshot="")
                        & ~models.Q(approval_text_snapshot="")
                    )
                    | (
                        models.Q(
                            event_type="selection_restored",
                            selection_kind_snapshot="asset",
                            rendition_set_id_snapshot__isnull=False,
                            rendition_set_id_snapshot__gt=0,
                            asset_id_snapshot__isnull=False,
                            asset_id_snapshot__gt=0,
                            source_type_snapshot="",
                            source_url_snapshot="",
                            source_page_url_snapshot="",
                            provider_snapshot="",
                            technical_warnings_snapshot=[],
                            approval_text_version_snapshot="",
                            approval_text_snapshot="",
                        )
                        & ~models.Q(asset_checksum_sha256_snapshot="")
                        & ~models.Q(asset_validation_version_snapshot="")
                    )
                    | models.Q(
                        selection_kind_snapshot="system_fallback",
                        rendition_set_id_snapshot__isnull=True,
                        asset_id_snapshot__isnull=True,
                        asset_checksum_sha256_snapshot="",
                        asset_validation_version_snapshot="",
                        source_type_snapshot="",
                        source_url_snapshot="",
                        source_page_url_snapshot="",
                        provider_snapshot="",
                        technical_warnings_snapshot=[],
                        approval_text_version_snapshot="",
                        approval_text_snapshot="",
                    )
                    | (
                        models.Q(
                            event_type="formal_takedown",
                            selection_kind_snapshot="system_fallback",
                            rendition_set_id_snapshot__isnull=False,
                            rendition_set_id_snapshot__gt=0,
                            asset_id_snapshot__isnull=False,
                            asset_id_snapshot__gt=0,
                            source_type_snapshot="",
                            source_url_snapshot="",
                            source_page_url_snapshot="",
                            provider_snapshot="",
                            technical_warnings_snapshot=[],
                            approval_text_version_snapshot="",
                            approval_text_snapshot="",
                        )
                        & ~models.Q(asset_checksum_sha256_snapshot="")
                        & ~models.Q(asset_validation_version_snapshot="")
                    )
                ),
                name="img_evt_selection_kind_contract",
            ),
        ),
        migrations.AddConstraint(
            model_name="imagereviewevent",
            constraint=models.CheckConstraint(
                condition=(
                    (
                        models.Q(
                            event_type="formal_takedown",
                            release_id_snapshot__isnull=False,
                        )
                        & ~models.Q(takedown_reason_code="")
                    )
                    | (
                        ~models.Q(event_type="formal_takedown")
                        & models.Q(
                            release_id_snapshot__isnull=True,
                            takedown_reason_code="",
                        )
                    )
                ),
                name="img_evt_takedown_contract",
            ),
        ),
    ]
