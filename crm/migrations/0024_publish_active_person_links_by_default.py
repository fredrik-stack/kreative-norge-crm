from django.db import migrations, models


def publish_active_person_links(apps, schema_editor):
    OrganizationPerson = apps.get_model("crm", "OrganizationPerson")
    OrganizationPerson.objects.filter(status="ACTIVE").update(publish_person=True)


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0023_sync_editor_import_taxonomy"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organizationperson",
            name="publish_person",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(publish_active_person_links, migrations.RunPython.noop),
    ]
