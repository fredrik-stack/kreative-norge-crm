from decimal import Decimal

from django.db import migrations, models
from django.db.migrations.exceptions import IrreversibleError


def preserve_zoom_out_on_reverse(apps, schema_editor):
    model = apps.get_model("crm", "ImageRenditionSet")
    if model.objects.using(schema_editor.connection.alias).filter(zoom__lt=1).exists():
        raise IrreversibleError("Keep additive schema 0040: zoom-out image recipes must be preserved.")


class Migration(migrations.Migration):
    dependencies = [("crm", "0039_access_management_journey")]
    operations = [
        migrations.RemoveConstraint(model_name="imagerenditionset", name="image_rset_zoom_range"),
        migrations.AddConstraint(
            model_name="imagerenditionset",
            constraint=models.CheckConstraint(
                condition=models.Q(zoom__gte=Decimal("0.1"), zoom__lte=3),
                name="image_rset_zoom_range",
            ),
        ),
        migrations.RunPython(migrations.RunPython.noop, reverse_code=preserve_zoom_out_on_reverse),
    ]
