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
        "Lyd",
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


def seed_categories_and_subcategories(apps, schema_editor):
    Category = apps.get_model("crm", "Category")
    Subcategory = apps.get_model("crm", "Subcategory")

    for category_name, subcategories in SEED_CATEGORIES.items():
        category_slug = slugify(category_name) or "category"
        category, _ = Category.objects.get_or_create(
            slug=category_slug,
            defaults={"name": category_name},
        )

        if category.name != category_name:
            category.name = category_name
            category.save(update_fields=["name"])

        for subcategory_name in subcategories:
            subcategory_slug = slugify(subcategory_name) or "subcategory"
            Subcategory.objects.get_or_create(
                category=category,
                slug=subcategory_slug,
                defaults={"name": subcategory_name},
            )


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0011_organization_thumbnail_fields"),
    ]

    operations = [
        migrations.RunPython(seed_categories_and_subcategories, migrations.RunPython.noop),
    ]
