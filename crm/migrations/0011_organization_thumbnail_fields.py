from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0010_rename_crm_subcate_categor_1c5e10_idx_crm_subcate_categor_829f2b_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="auto_thumbnail_url",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="organization",
            name="thumbnail_image_url",
            field=models.URLField(blank=True, null=True),
        ),
    ]
