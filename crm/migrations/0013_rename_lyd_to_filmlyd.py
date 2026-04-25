from django.db import migrations


def rename_lyd_to_filmlyd(apps, schema_editor):
    Subcategory = apps.get_model("crm", "Subcategory")
    Subcategory.objects.filter(name="Lyd", slug="lyd").update(name="Filmlyd", slug="filmlyd")


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0012_seed_categories_and_subcategories"),
    ]

    operations = [
        migrations.RunPython(rename_lyd_to_filmlyd, migrations.RunPython.noop),
    ]
