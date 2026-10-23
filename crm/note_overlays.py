"""Storage gate only; deliberately grants no user access or backfill authority."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class NoteOverlayError(ValidationError):
    pass


def require_overlay_storage():
    if getattr(settings, "TENANT_NOTE_OVERLAYS_ENABLED", False) is not True:
        raise NoteOverlayError("OVERLAY_STORAGE_DISABLED")


class NoteOverlayQuerySet(models.QuerySet):
    def update(self, **kwargs):
        require_overlay_storage()
        if set(kwargs) - {"note"}:
            raise NoteOverlayError("OVERLAY_IDENTITY_IMMUTABLE")
        return super().update(**kwargs)

    def _update(self, values):
        require_overlay_storage()
        # Model.save includes the unchanged assignment; the DB trigger checks it.
        if any(field.name not in {"note", "assignment"} for field, _, _ in values):
            raise NoteOverlayError("OVERLAY_IDENTITY_IMMUTABLE")
        return super()._update(values)

    _update.queryset_only = False

    def _insert(self, objs, fields, returning_fields=None, raw=False, using=None,
                on_conflict=None, update_fields=None, unique_fields=None):
        require_overlay_storage()
        if on_conflict is not None:
            raise NoteOverlayError("OVERLAY_UPSERT_UNSUPPORTED")
        return super()._insert(objs, fields, returning_fields=returning_fields, raw=raw,
                              using=using, on_conflict=on_conflict,
                              update_fields=update_fields, unique_fields=unique_fields)

    def bulk_create(self, objs, **kwargs):
        require_overlay_storage()
        return super().bulk_create(objs, **kwargs)

    def bulk_update(self, objs, fields, batch_size=None):
        require_overlay_storage()
        if set(fields) - {"note"}:
            raise NoteOverlayError("OVERLAY_IDENTITY_IMMUTABLE")
        return super().bulk_update(objs, fields, batch_size=batch_size)

    def delete(self):
        require_overlay_storage()
        return super().delete()

    def _raw_delete(self, using):
        require_overlay_storage()
        return super()._raw_delete(using)


class NoteOverlayManager(models.Manager.from_queryset(NoteOverlayQuerySet)):
    pass


class NoteOverlayMixin(models.Model):
    objects = NoteOverlayManager()
    note = models.TextField(null=True, blank=True)

    class Meta:
        abstract = True
        base_manager_name = "objects"
        default_manager_name = "objects"

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._loaded_overlay_pk = instance.pk
        return instance

    def save_base(self, *args, **kwargs):
        require_overlay_storage()
        if hasattr(self, "_loaded_overlay_pk") and self.pk != self._loaded_overlay_pk:
            raise NoteOverlayError("OVERLAY_IDENTITY_IMMUTABLE")
        result = super().save_base(*args, **kwargs)
        self._loaded_overlay_pk = self.pk
        return result

    def delete(self, *args, **kwargs):
        require_overlay_storage()
        return super().delete(*args, **kwargs)
