from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class FormalImageTakedownAuditMigrationTests(TransactionTestCase):
    migrate_from = ("crm", "0029_release_selection_revision_gate")
    migrate_to = ("crm", "0030_formal_image_takedown_audit")

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_additive_audit_fields_preserve_existing_events_and_reverse_before_use(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        Tenant = old_apps.get_model("crm", "Tenant")
        Organization = old_apps.get_model("crm", "Organization")
        Selection = old_apps.get_model("crm", "OrganizationImageSelection")
        ReviewEvent = old_apps.get_model("crm", "ImageReviewEvent")
        User = old_apps.get_model("auth", "User")

        tenant = Tenant.objects.create(name="Takedown migration", slug="takedown-migration")
        organization = Organization.objects.create(
            tenant=tenant,
            name="Existing audit organization",
        )
        user = User.objects.create(username="takedown-migration-user")
        previous = Selection.objects.create(
            tenant=tenant,
            organization=organization,
            selection_kind="system_fallback",
            alt_text="Standardbilde",
            revision=1,
            status="archived",
            locked_by=user,
            locked_at=timezone.now(),
        )
        selection = Selection.objects.create(
            tenant=tenant,
            organization=organization,
            selection_kind="system_fallback",
            alt_text="Standardbilde",
            revision=2,
            status="active",
            locked_by=user,
            locked_at=timezone.now(),
        )
        event = ReviewEvent.objects.create(
            tenant=tenant,
            organization=organization,
            selection=selection,
            previous_selection=previous,
            actor_user=user,
            event_type="selection_removed_to_fallback",
            organization_id_snapshot=organization.pk,
            organization_name_snapshot=organization.name,
            selection_id_snapshot=selection.pk,
            selection_revision_snapshot=selection.revision,
            selection_kind_snapshot="system_fallback",
            previous_selection_id_snapshot=previous.pk,
            previous_selection_revision_snapshot=previous.revision,
            actor_user_id_snapshot=user.pk,
            actor_username_snapshot=user.username,
            alt_text_snapshot="Standardbilde",
            created_at=timezone.now(),
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        new_apps = executor.loader.project_state([self.migrate_to]).apps
        NewReviewEvent = new_apps.get_model("crm", "ImageReviewEvent")
        migrated = NewReviewEvent.objects.get(pk=event.pk)
        self.assertEqual(migrated.event_type, "selection_removed_to_fallback")
        self.assertEqual(migrated.takedown_reason_code, "")
        self.assertIsNone(migrated.release_id_snapshot)

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        reversed_apps = executor.loader.project_state([self.migrate_from]).apps
        ReversedReviewEvent = reversed_apps.get_model("crm", "ImageReviewEvent")
        reversed_event = ReversedReviewEvent.objects.get(pk=event.pk)
        self.assertEqual(reversed_event.event_type, "selection_removed_to_fallback")
        self.assertEqual(reversed_event.selection_id_snapshot, selection.pk)
