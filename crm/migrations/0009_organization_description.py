from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0008_category_subcategory_and_assignments"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
    ]
