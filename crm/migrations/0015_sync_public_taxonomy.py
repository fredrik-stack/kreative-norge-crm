from django.db import migrations
from django.utils.text import slugify


SEED_CATEGORIES = {
    "Musikk": [
        "Artister & Band",
        "Konsertarrangører",
        "Musikere",
        "Musikkbransjen",
    ],
    "Film": [
        "Produsent",
        "Regi & Manus",
        "Foto/ Lys",
        "Filmlyd",
        "Produksjon",
        "Arenaer",
    ],
    "Kunst & Design": [
        "Visuell kunst",
        "Grafisk design",
        "Klesdesign",
    ],
    "Scenekunst": [
        "Teater",
        "Dans",
    ],
    "Kreativ teknologi": [],
    "Litteratur": [],
}


def sync_public_taxonomy(apps, schema_editor):
    Category = apps.get_model("crm", "Category")
    Subcategory = apps.get_model("crm", "Subcategory")

    for category_name, subcategory_names in SEED_CATEGORIES.items():
        category_slug = slugify(category_name) or "category"
        category, _ = Category.objects.get_or_create(
            slug=category_slug,
            defaults={"name": category_name},
        )
        if category.name != category_name:
            category.name = category_name
            category.save(update_fields=["name"])

        for subcategory_name in subcategory_names:
            subcategory_slug = slugify(subcategory_name) or "subcategory"
            subcategory, created = Subcategory.objects.get_or_create(
                category=category,
                slug=subcategory_slug,
                defaults={"name": subcategory_name},
            )
            if not created and subcategory.name != subcategory_name:
                subcategory.name = subcategory_name
                subcategory.save(update_fields=["name"])

    for category in Category.objects.filter(name="Film"):
        lyd = Subcategory.objects.filter(category=category, name="Lyd", slug="lyd").first()
        filmlyd = Subcategory.objects.filter(category=category, name="Filmlyd", slug="filmlyd").first()
        if lyd and filmlyd:
            lyd.delete()
        elif lyd and not filmlyd:
            lyd.name = "Filmlyd"
            lyd.slug = "filmlyd"
            lyd.save(update_fields=["name", "slug"])


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0014_categories_for_orgs_and_people_and_restore_lyd"),
    ]

    operations = [
        migrations.RunPython(sync_public_taxonomy, migrations.RunPython.noop),
    ]
