from django.db import migrations, models


def backfill_categories_from_subcategories(apps, schema_editor):
    Organization = apps.get_model("crm", "Organization")
    Person = apps.get_model("crm", "Person")
    Subcategory = apps.get_model("crm", "Subcategory")

    org_categories_through = Organization.categories.through
    person_categories_through = Person.categories.through

    subcategories = {
        subcategory.id: subcategory.category_id
        for subcategory in Subcategory.objects.all().only("id", "category_id")
    }

    for organization in Organization.objects.all():
        category_ids = {
            subcategories[subcategory_id]
            for subcategory_id in organization.subcategories.values_list("id", flat=True)
            if subcategory_id in subcategories
        }
        for category_id in category_ids:
            org_categories_through.objects.get_or_create(
                organization_id=organization.id,
                category_id=category_id,
            )

    for person in Person.objects.all():
        category_ids = {
            subcategories[subcategory_id]
            for subcategory_id in person.subcategories.values_list("id", flat=True)
            if subcategory_id in subcategories
        }
        for category_id in category_ids:
            person_categories_through.objects.get_or_create(
                person_id=person.id,
                category_id=category_id,
            )

    Subcategory.objects.filter(name="Filmlyd", slug="filmlyd").update(name="Lyd", slug="lyd")


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0013_rename_lyd_to_filmlyd"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="categories",
            field=models.ManyToManyField(blank=True, related_name="organizations", to="crm.category"),
        ),
        migrations.AddField(
            model_name="person",
            name="categories",
            field=models.ManyToManyField(blank=True, related_name="persons", to="crm.category"),
        ),
        migrations.RunPython(backfill_categories_from_subcategories, migrations.RunPython.noop),
    ]
