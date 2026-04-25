from django.db import migrations
from django.utils.text import slugify


def update_film_taxonomy(apps, schema_editor):
    Category = apps.get_model("crm", "Category")
    Subcategory = apps.get_model("crm", "Subcategory")

    film = Category.objects.filter(name="Film").first()
    if not film:
        return

    production = Subcategory.objects.filter(category=film, name="Produksjon").first()
    if production:
        production.name = "Filmproduksjon"
        production.slug = slugify("Filmproduksjon")
        production.save(update_fields=["name", "slug"])

    Subcategory.objects.filter(category=film, name="Arenaer").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0015_sync_public_taxonomy"),
    ]

    operations = [
        migrations.RunPython(update_film_taxonomy, migrations.RunPython.noop),
    ]
