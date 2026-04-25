from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0006_organization_tiktok_url_person_social_links"),
    ]

    operations = [
        migrations.CreateModel(
            name="Tag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64)),
                ("slug", models.SlugField(max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "tenant",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="tags", to="crm.tenant"),
                ),
            ],
            options={
                "ordering": ["name"],
                "unique_together": {("tenant", "name"), ("tenant", "slug")},
            },
        ),
        migrations.AddIndex(
            model_name="tag",
            index=models.Index(fields=["tenant", "name"], name="crm_tag_tenant__013be9_idx"),
        ),
        migrations.AddIndex(
            model_name="tag",
            index=models.Index(fields=["tenant", "slug"], name="crm_tag_tenant__1c474d_idx"),
        ),
        migrations.AddField(
            model_name="person",
            name="tags",
            field=models.ManyToManyField(blank=True, related_name="persons", to="crm.tag"),
        ),
        migrations.AddField(
            model_name="organization",
            name="tags",
            field=models.ManyToManyField(blank=True, related_name="organizations", to="crm.tag"),
        ),
    ]
