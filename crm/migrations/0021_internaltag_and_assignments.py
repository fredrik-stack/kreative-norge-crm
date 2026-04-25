from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0020_tenantmembership"),
    ]

    operations = [
        migrations.CreateModel(
            name="InternalTag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64)),
                ("slug", models.SlugField(max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="internal_tags", to="crm.tenant")),
            ],
            options={
                "ordering": ["name"],
                "indexes": [
                    models.Index(fields=["tenant", "name"], name="crm_internt_tenant__f8fd65_idx"),
                    models.Index(fields=["tenant", "slug"], name="crm_internt_tenant__d46dfb_idx"),
                ],
                "unique_together": {("tenant", "name"), ("tenant", "slug")},
            },
        ),
        migrations.AddField(
            model_name="organization",
            name="internal_tags",
            field=models.ManyToManyField(blank=True, related_name="organizations", to="crm.internaltag"),
        ),
        migrations.AddField(
            model_name="person",
            name="internal_tags",
            field=models.ManyToManyField(blank=True, related_name="persons", to="crm.internaltag"),
        ),
    ]
