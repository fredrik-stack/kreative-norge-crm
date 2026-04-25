from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0007_tag_organization_tags_person_tags"),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80, unique=True)),
                ("slug", models.SlugField(max_length=96, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Subcategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80)),
                ("slug", models.SlugField(max_length=96)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "category",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="subcategories", to="crm.category"),
                ),
            ],
            options={
                "ordering": ["category__name", "name"],
                "unique_together": {("category", "name"), ("category", "slug")},
            },
        ),
        migrations.AddIndex(
            model_name="subcategory",
            index=models.Index(fields=["category", "name"], name="crm_subcate_categor_1c5e10_idx"),
        ),
        migrations.AddIndex(
            model_name="subcategory",
            index=models.Index(fields=["category", "slug"], name="crm_subcate_categor_91c48a_idx"),
        ),
        migrations.AddField(
            model_name="organization",
            name="subcategories",
            field=models.ManyToManyField(blank=True, related_name="organizations", to="crm.subcategory"),
        ),
        migrations.AddField(
            model_name="person",
            name="subcategories",
            field=models.ManyToManyField(blank=True, related_name="persons", to="crm.subcategory"),
        ),
    ]
