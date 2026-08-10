from __future__ import annotations

from django.db import connection


class ImageStorageRuntimeLockError(RuntimeError):
    pass


# A single project-owned PostgreSQL advisory lock namespace for the immutable
# image storage -> database reference boundary. Ingests may run concurrently
# under the shared variant; destructive cleanup requires the exclusive variant.
IMAGE_STORAGE_RUNTIME_LOCK_KEY = 4_927_312_846_031_001


def _acquire_transaction_lock(*, shared: bool) -> None:
    if connection.vendor != "postgresql":
        raise ImageStorageRuntimeLockError(
            "Image storage runtime locking requires PostgreSQL."
        )
    if not connection.in_atomic_block:
        raise ImageStorageRuntimeLockError(
            "Image storage runtime locking requires an active database transaction."
        )
    function_name = "pg_advisory_xact_lock_shared" if shared else "pg_advisory_xact_lock"
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT {function_name}(%s)",
            [IMAGE_STORAGE_RUNTIME_LOCK_KEY],
        )


def acquire_image_storage_ingest_lock() -> None:
    _acquire_transaction_lock(shared=True)


def acquire_image_storage_cleanup_lock() -> None:
    _acquire_transaction_lock(shared=False)
