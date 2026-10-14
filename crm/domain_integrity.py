"""Narrow ORM boundary for phase 6A.2; database triggers provide structural safety."""
from contextlib import contextmanager
from contextvars import ContextVar

from django.core.exceptions import ValidationError
from django.db import models, transaction


class DomainStructureError(ValidationError):
    pass


class DomainBindingQuerySet(models.QuerySet):
    def update(self, **kwargs):
        if {"sharing_domain", "sharing_domain_id"} & kwargs.keys():
            raise DomainStructureError("Domain binding requires the explicit backfill service.")
        return super().update(**kwargs)

    def _update(self, values):
        for field, _, value in values:
            if field.name == "sharing_domain" and (hasattr(value, "resolve_expression") or self.exclude(sharing_domain_id=value).exists()):
                raise DomainStructureError("Private domain change is not supported.")
        return super()._update(values)

    _update.queryset_only = False

    def bulk_update(self, objs, fields, batch_size=None):
        if {"sharing_domain", "sharing_domain_id"} & set(fields):
            raise DomainStructureError("Domain binding cannot be bulk-updated.")
        return super().bulk_update(objs, fields, batch_size=batch_size)

    def bulk_create(self, objs, **kwargs):
        objs = list(objs)
        if any(obj.sharing_domain_id is not None for obj in objs):
            raise DomainStructureError("New legacy profiles must be unbound.")
        if {"sharing_domain", "sharing_domain_id"} & set(kwargs.get("update_fields") or []):
            raise DomainStructureError("Domain upsert is not supported.")
        return super().bulk_create(objs, **kwargs)


class DomainBindingManager(models.Manager.from_queryset(DomainBindingQuerySet)):
    pass


class DomainBindingMixin(models.Model):
    objects = DomainBindingManager()

    class Meta:
        abstract = True
        base_manager_name = "objects"

    def save(self, *args, **kwargs):
        fields = kwargs.get("update_fields")
        if fields is None or {"sharing_domain", "sharing_domain_id"} & set(fields):
            old = None if self._state.adding else type(self).objects.using(
                kwargs.get("using") or self._state.db or "default"
            ).filter(pk=self.pk).values_list("sharing_domain_id", flat=True).first()
            if self.sharing_domain_id != old:
                raise DomainStructureError("Domain binding requires the explicit backfill service.")
        return super().save(*args, **kwargs)


_assignment_scope = ContextVar("legacy_assignment_scope", default=None)


@contextmanager
def _legacy_assignment_scope(allowed):
    """Private service-only insert scope; never authorizes updates or removal."""
    if not transaction.get_connection().in_atomic_block:
        raise DomainStructureError("Assignment insert requires an atomic backfill.")
    token = _assignment_scope.set(frozenset(allowed))
    try:
        yield
    finally:
        _assignment_scope.reset(token)


class AssignmentQuerySet(models.QuerySet):
    def _denied(self, *args, **kwargs):
        raise DomainStructureError("Assignments are managed only by the legacy backfill service.")

    create = get_or_create = update_or_create = update = delete = bulk_create = bulk_update = _denied
    _update = _denied
    _update.queryset_only = False
    _raw_delete = _denied

    def _insert(self, objs, fields, returning_fields=None, raw=False, using=None,
                on_conflict=None, update_fields=None, unique_fields=None):
        scope = _assignment_scope.get()
        entity = "organization_id" if self.model._meta.model_name.startswith("organization") else "person_id"
        if scope is None or on_conflict is not None or not transaction.get_connection(using or self.db).in_atomic_block:
            raise DomainStructureError("Private assignment insert requires the backfill scope.")
        if any((self.model._meta.label_lower, getattr(obj, entity), obj.tenant_id) not in scope for obj in objs):
            raise DomainStructureError("Private assignment insert outside scope.")
        return super()._insert(objs, fields, returning_fields=returning_fields, raw=raw,
                              using=using, on_conflict=on_conflict,
                              update_fields=update_fields, unique_fields=unique_fields)


class AssignmentManager(models.Manager.from_queryset(AssignmentQuerySet)):
    def _insert_for_backfill(self, objects):
        objects = list(objects)
        scope = _assignment_scope.get()
        if scope is None or not transaction.get_connection(self.db).in_atomic_block:
            raise DomainStructureError("No active backfill insert scope.")
        entity = "organization_id" if self.model._meta.model_name.startswith("organization") else "person_id"
        for obj in objects:
            if (self.model._meta.label_lower, getattr(obj, entity), obj.tenant_id) not in scope:
                raise DomainStructureError("Assignment outside the approved backfill scope.")
            obj.full_clean()
        return models.QuerySet.bulk_create(self.get_queryset(), objects)


class AssignmentMixin(models.Model):
    objects = AssignmentManager()

    class Meta:
        abstract = True
        base_manager_name = "objects"
        default_manager_name = "objects"

    def save(self, *args, **kwargs):
        raise DomainStructureError("Assignment save is not a supported writer.")

    def delete(self, *args, **kwargs):
        raise DomainStructureError("Assignment removal requires a later authorized lifecycle.")
