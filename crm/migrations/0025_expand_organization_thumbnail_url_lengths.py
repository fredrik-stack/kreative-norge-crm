from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0024_publish_active_person_links_by_default"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="auto_thumbnail_url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name="organization",
            name="og_image_url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name="organization",
            name="thumbnail_image_url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
    ]
