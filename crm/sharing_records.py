"""Immutable agreement records. PostgreSQL also enforces this for SQL/bulk paths."""
from django.core.exceptions import ValidationError
from django.db import models


class SharingRecordError(ValidationError):
    pass


class SharingRecordQuerySet(models.QuerySet):
    def denied(self, *args, **kwargs):
        raise SharingRecordError("Sharing history is immutable; append a new event.")

    update = delete = bulk_update = update_or_create = _update = _raw_delete = denied
    _update.queryset_only = False

    def bulk_create(self, objs, **kwargs):
        if kwargs.get("update_conflicts") or kwargs.get("ignore_conflicts"):
            self.denied()
        return super().bulk_create(objs, **kwargs)


class SharingRecord(models.Model):
    objects = models.Manager.from_queryset(SharingRecordQuerySet)()

    class Meta:
        abstract = True
        base_manager_name = "objects"
        default_manager_name = "objects"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise SharingRecordError("Sharing history cannot be changed.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise SharingRecordError("Sharing history cannot be removed.")
