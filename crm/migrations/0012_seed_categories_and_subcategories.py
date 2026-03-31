from django.db import migrations
from django.utils.text import slugify


SEED_CATEGORIES = {
    "Musikk": [
        "Artister & Band",
        "Musikere",
        "Komponister",
        "Produsenter",
        "Låtskrivere",
        "Studioer",
        "Plate- og musikkselskap",
        "Konsertarrangører",
        "Festivaler",
        "Management & booking",
        "Bransjeaktører",
    ],
    "Film": [
        "Produksjonsselskap",
        "Regissører",
        "Manusforfattere",
        "Produsenter",
        "Foto & kamera",
        "Postproduksjon",
        "Skuespillere",
        "Distribusjon",
        "Festivaler & visning",
    ],
    "Kunst & Design": [
        "Visuell kunst",
        "Illustrasjon",
        "Grafisk design",
        "Industridesign",
        "Interiørarkitektur",
        "Motedesign",
        "Gallerier",
        "Kunsthåndverk",
        "Kuratorer",
    ],
    "Scenekunst": [
        "Teater",
        "Dans",
        "Performance",
        "Kompani",
        "Scenografer",
        "Koreografer",
        "Utøvere",
        "Produsenter",
        "Festivaler",
    ],
    "Kreativ teknologi": [
        "Spillutvikling",
        "XR / VR / AR",
        "Interaktiv design",
        "Lydteknologi",
        "Kreativ koding",
        "AI & generative verktøy",
        "Digital kunst",
        "Teknisk produksjon",
    ],
    "Litteratur": [
        "Forfattere",
        "Forlag",
        "Oversettere",
        "Redaktører",
        "Litteraturhus",
        "Festivaler",
        "Tidsskrift",
        "Illustratører",
    ],
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
