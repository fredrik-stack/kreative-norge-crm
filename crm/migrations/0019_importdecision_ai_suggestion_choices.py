from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0018_importjob_importrow_importdecision_importcommitlog_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="importdecision",
            name="decision_type",
            field=models.CharField(
                choices=[
                    ("USE_EXISTING_ORGANIZATION", "Use existing organization"),
                    ("CREATE_NEW_ORGANIZATION", "Create new organization"),
                    ("USE_EXISTING_PERSON", "Use existing person"),
                    ("CREATE_NEW_PERSON", "Create new person"),
                    ("MAP_CATEGORY", "Map category"),
                    ("MAP_SUBCATEGORY", "Map subcategory"),
                    ("ACCEPT_NEW_TAG", "Accept new tag"),
                    ("ACCEPT_AI_SUGGESTION", "Accept AI suggestion"),
                    ("IGNORE_AI_SUGGESTION", "Ignore AI suggestion"),
                    ("SKIP_ROW", "Skip row"),
                ],
                max_length=48,
            ),
        ),
    ]
