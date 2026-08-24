from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ImportImageDecisionMigrationTests(TransactionTestCase):
    migrate_from = ("crm", "0030_formal_image_takedown_audit")
    migrate_to = ("crm", "0031_import_image_decision_contract")

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_additive_schema_preserves_old_jobs_rows_and_generic_decisions_without_backfill(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        Tenant = old_apps.get_model("crm", "Tenant")
        User = old_apps.get_model("auth", "User")
        ImportJob = old_apps.get_model("crm", "ImportJob")
        ImportRow = old_apps.get_model("crm", "ImportRow")
        ImportDecision = old_apps.get_model("crm", "ImportDecision")

        tenant = Tenant.objects.create(name="Old import", slug="old-import")
        user = User.objects.create(username="old-import-user")
        job = ImportJob.objects.create(
            tenant=tenant,
            created_by=user,
            source_type="CSV",
            import_mode="ORGANIZATIONS_ONLY",
            status="PREVIEW_READY",
        )
        row = ImportRow.objects.create(import_job=job, row_number=1)
        decision = ImportDecision.objects.create(
            import_row=row,
            decided_by=user,
            decision_type="CREATE_NEW_ORGANIZATION",
            payload_json={"unchanged": True},
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        new_apps = executor.loader.project_state([self.migrate_to]).apps
        NewJob = new_apps.get_model("crm", "ImportJob")
        NewRow = new_apps.get_model("crm", "ImportRow")
        NewDecision = new_apps.get_model("crm", "ImportDecision")
        ImageDecision = new_apps.get_model("crm", "ImportImageDecision")
        self.assertTrue(NewJob.objects.filter(pk=job.pk).exists())
        self.assertTrue(NewRow.objects.filter(pk=row.pk).exists())
        self.assertEqual(NewDecision.objects.get(pk=decision.pk).payload_json, {"unchanged": True})
        self.assertEqual(ImageDecision.objects.count(), 0)

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        reversed_apps = executor.loader.project_state([self.migrate_from]).apps
        self.assertTrue(reversed_apps.get_model("crm", "ImportRow").objects.filter(pk=row.pk).exists())
        self.assertTrue(
            reversed_apps.get_model("crm", "ImportDecision").objects.filter(pk=decision.pk).exists()
        )

    def test_reverse_is_blocked_after_first_typed_decision(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        apps = executor.loader.project_state([self.migrate_to]).apps
        Tenant = apps.get_model("crm", "Tenant")
        User = apps.get_model("auth", "User")
        ImportJob = apps.get_model("crm", "ImportJob")
        ImportRow = apps.get_model("crm", "ImportRow")
        ImportImageDecision = apps.get_model("crm", "ImportImageDecision")

        tenant = Tenant.objects.create(name="Guarded import", slug="guarded-import")
        user = User.objects.create(username="guarded-import-user")
        job = ImportJob.objects.create(
            tenant=tenant,
            created_by=user,
            source_type="CSV",
            import_mode="ORGANIZATIONS_ONLY",
            status="PREVIEW_READY",
        )
        row = ImportRow.objects.create(import_job=job, row_number=1)
        image_decision = ImportImageDecision(
            import_row=row,
            decided_by=user,
            decision_kind="KEEP_LOCKED_IMAGE",
            proposed_actor_snapshot={"name": "Guarded actor"},
            canonical_snapshot_hash_sha256=(
                "1eeb7922a1f1d5fc62d105a0a477e9f0b046629d1c0cd60b907ca9876289d4a8"
            ),
        )
        ImportImageDecision._base_objects._insert_from_import_service([image_decision])

        executor = MigrationExecutor(connection)
        with self.assertRaises(IrreversibleError):
            executor.migrate([self.migrate_from])
        self.assertIn("crm_importimagedecision", connection.introspection.table_names())
        self.assertEqual(ImportImageDecision.objects.count(), 1)
