from django.db import migrations, models


def require_empty_release_table(apps, schema_editor):
    Release = apps.get_model("crm", "OrganizationImageRelease")
    if Release._base_manager.exists():
        raise RuntimeError(
            "OrganizationImageRelease must be empty before applying the 3E.1B "
            "selection revision gate; reconcile existing immutable releases first."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0028_image_rendition_zoom"),
    ]

    operations = [
        migrations.AddField(
            model_name="organizationimagerelease",
            name="selection_revision_snapshot",
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.RunPython(require_empty_release_table, require_empty_release_table),
        migrations.AlterField(
            model_name="organizationimagerelease",
            name="selection_revision_snapshot",
            field=models.PositiveIntegerField(),
        ),
        migrations.AddConstraint(
            model_name="organizationimagerelease",
            constraint=models.CheckConstraint(
                condition=models.Q(selection_revision_snapshot__gt=0),
                name="img_release_selection_rev_gt_0",
            ),
        ),
        migrations.AddConstraint(
            model_name="organizationimagerelease",
            constraint=models.UniqueConstraint(
                fields=("selection",),
                name="img_release_selection_uniq",
            ),
        ),
    ]
