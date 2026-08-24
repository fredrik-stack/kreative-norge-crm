# Generated from the approved phase 3F typed import-image contract on 2026-08-24.

import crm.models
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.migrations.exceptions import IrreversibleError


def preserve_typed_image_decisions_on_reverse(apps, schema_editor):
    ImportImageDecision = apps.get_model("crm", "ImportImageDecision")
    ImageReviewEvent = apps.get_model("crm", "ImageReviewEvent")
    if ImportImageDecision._base_manager.exists() or ImageReviewEvent._base_manager.filter(
        import_image_decision__isnull=False
    ).exists():
        raise IrreversibleError(
            "Migration 0031 cannot be reversed after an import image decision "
            "or applied review-event binding has been stored."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0030_formal_image_takedown_audit"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ImportImageDecision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("decision_kind", models.CharField(choices=[("KEEP_LOCKED_IMAGE", "Keep locked image"), ("SET_APPROVED_IMAGE", "Set approved image"), ("USE_APPROVED_FALLBACK", "Use approved fallback")], max_length=24)),
                ("expected_selection_revision", models.PositiveIntegerField(default=0)),
                ("approved_alt_text", models.CharField(blank=True, default="", max_length=500)),
                ("approved_public_credit", models.CharField(blank=True, default="", max_length=500)),
                ("source_type_snapshot", models.CharField(blank=True, choices=[("official_website", "Official website"), ("open_graph", "Open Graph"), ("website_image", "Website image"), ("brave_image_search", "Brave image search"), ("upload", "Upload"), ("pasted_url", "Pasted URL")], default="", max_length=32)),
                ("source_url_snapshot", models.URLField(blank=True, default="", max_length=2048)),
                ("source_page_url_snapshot", models.URLField(blank=True, default="", max_length=2048)),
                ("provider_snapshot", models.CharField(blank=True, default="", max_length=255)),
                ("technical_warnings_snapshot", models.JSONField(blank=True, default=list, validators=[crm.models.validate_technical_warnings])),
                ("approval_text_version_snapshot", models.CharField(blank=True, default="", max_length=64)),
                ("approval_text_snapshot", models.TextField(blank=True, default="")),
                ("asset_checksum_sha256_snapshot", models.CharField(blank=True, default="", max_length=64, validators=[django.core.validators.RegexValidator(code="invalid_sha256", message="Enter a lowercase hexadecimal SHA-256 checksum.", regex="^[0-9a-f]{64}$")])),
                ("asset_validation_version_snapshot", models.CharField(blank=True, default="", max_length=64)),
                ("rendition_set_snapshot", models.JSONField(blank=True, default=dict)),
                ("rendition_set_snapshot_hash_sha256", models.CharField(blank=True, default="", max_length=64, validators=[django.core.validators.RegexValidator(code="invalid_sha256", message="Enter a lowercase hexadecimal SHA-256 checksum.", regex="^[0-9a-f]{64}$")])),
                ("proposed_actor_snapshot", models.JSONField(default=dict)),
                ("canonical_snapshot_hash_sha256", models.CharField(max_length=64, validators=[django.core.validators.RegexValidator(code="invalid_sha256", message="Enter a lowercase hexadecimal SHA-256 checksum.", regex="^[0-9a-f]{64}$")])),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("asset", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="import_image_decisions", to="crm.imageasset")),
                ("decided_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="import_image_decisions", to=settings.AUTH_USER_MODEL)),
                ("expected_selection", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="expected_by_import_image_decisions", to="crm.organizationimageselection")),
                ("import_row", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="image_decision", to="crm.importrow")),
                ("rendition_set", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="import_image_decisions", to="crm.imagerenditionset")),
                ("target_organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="import_image_decisions", to="crm.organization")),
            ],
            managers=[
                ("_base_objects", crm.models.ImmutableImportImageDecisionManager()),
                ("objects", crm.models.ImmutableImportImageDecisionManager()),
            ],
        ),
        migrations.AddField(
            model_name="imagereviewevent",
            name="import_image_decision",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="applied_review_event", to="crm.importimagedecision"),
        ),
        migrations.AddIndex(
            model_name="importimagedecision",
            index=models.Index(fields=["import_row", "decision_kind"], name="imp_img_row_kind_idx"),
        ),
        migrations.AddConstraint(
            model_name="importimagedecision",
            constraint=models.CheckConstraint(condition=models.Q(models.Q(("expected_selection__isnull", True), ("expected_selection_revision", 0)), models.Q(("expected_selection__isnull", False), ("expected_selection_revision__gt", 0)), _connector="OR"), name="imp_img_expected_selection_contract"),
        ),
        migrations.AddConstraint(
            model_name="importimagedecision",
            constraint=models.CheckConstraint(condition=models.Q(models.Q(("asset__isnull", False), ("decision_kind", "SET_APPROVED_IMAGE"), ("rendition_set__isnull", False)), models.Q(("asset__isnull", True), ("decision_kind__in", ["KEEP_LOCKED_IMAGE", "USE_APPROVED_FALLBACK"]), ("rendition_set__isnull", True)), _connector="OR"), name="imp_img_decision_asset_xor"),
        ),
        migrations.AddConstraint(
            model_name="importimagedecision",
            constraint=models.CheckConstraint(condition=models.Q(models.Q(("decision_kind", "SET_APPROVED_IMAGE"), models.Q(("source_type_snapshot", ""), _negated=True), models.Q(("approval_text_version_snapshot", ""), _negated=True), models.Q(("approval_text_snapshot", ""), _negated=True), models.Q(("asset_checksum_sha256_snapshot", ""), _negated=True), models.Q(("asset_validation_version_snapshot", ""), _negated=True), models.Q(("rendition_set_snapshot", {}), _negated=True), models.Q(("rendition_set_snapshot_hash_sha256", ""), _negated=True)), models.Q(("approval_text_snapshot", ""), ("approval_text_version_snapshot", ""), ("asset_checksum_sha256_snapshot", ""), ("asset_validation_version_snapshot", ""), ("decision_kind__in", ["KEEP_LOCKED_IMAGE", "USE_APPROVED_FALLBACK"]), ("provider_snapshot", ""), ("rendition_set_snapshot", {}), ("rendition_set_snapshot_hash_sha256", ""), ("source_page_url_snapshot", ""), ("source_type_snapshot", ""), ("source_url_snapshot", ""), ("technical_warnings_snapshot", [])), _connector="OR"), name="imp_img_approval_snapshot_contract"),
        ),
        migrations.AddConstraint(
            model_name="importimagedecision",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(decision_kind="SET_APPROVED_IMAGE")
                    | models.Q(
                        decision_kind="KEEP_LOCKED_IMAGE",
                        approved_alt_text="",
                        approved_public_credit="",
                    )
                    | (
                        models.Q(
                            decision_kind="USE_APPROVED_FALLBACK",
                            approved_public_credit="",
                        )
                        & ~models.Q(approved_alt_text="")
                    )
                ),
                name="imp_img_presentation_contract",
            ),
        ),
        migrations.RunPython(
            migrations.RunPython.noop,
            reverse_code=preserve_typed_image_decisions_on_reverse,
        ),
    ]
