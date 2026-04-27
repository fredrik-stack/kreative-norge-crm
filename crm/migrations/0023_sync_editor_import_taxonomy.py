from django.db import migrations
from django.utils.text import slugify


EXACT_SUBCATEGORIES = {
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
        "Filmproduksjon",
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
}


def sync_editor_import_taxonomy(apps, schema_editor):
    Category = apps.get_model("crm", "Category")
    Subcategory = apps.get_model("crm", "Subcategory")

    for category_name, subcategory_names in EXACT_SUBCATEGORIES.items():
        category = Category.objects.filter(name=category_name).first()
        if not category:
            category = Category.objects.create(name=category_name, slug=slugify(category_name) or "category")

        for subcategory_name in subcategory_names:
            slug = slugify(subcategory_name) or "subcategory"
            Subcategory.objects.get_or_create(
                category=category,
                slug=slug,
                defaults={"name": subcategory_name},
            )

        allowed = {name.casefold() for name in subcategory_names}
        for subcategory in Subcategory.objects.filter(category=category):
            if subcategory.name.casefold() in allowed:
                continue
            if category_name == "Film" and subcategory.name.casefold() == "produksjon":
                subcategory.name = "Filmproduksjon"
                subcategory.slug = slugify("Filmproduksjon")
                subcategory.save(update_fields=["name", "slug"])
                continue
            if category_name == "Film" and subcategory.name.casefold() == "arenaer":
                subcategory.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0022_rename_crm_internt_tenant__f8fd65_idx_crm_interna_tenant__605165_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(sync_editor_import_taxonomy, migrations.RunPython.noop),
    ]
