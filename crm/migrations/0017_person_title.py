from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0016_update_film_taxonomy"),
    ]

    operations = [
        migrations.AddField(
            model_name="person",
            name="title",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
