from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
import os
from pathlib import Path
import stat
import time

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage, storages
from django.db import connection, transaction

from crm.models import ImageAsset, ImageRendition
from crm.validators import validate_storage_key

from .runtime_lock import (
    ImageStorageRuntimeLockError,
    acquire_image_storage_cleanup_lock,
)


class ImageOrphanCleanupError(RuntimeError):
    pass


@dataclass(frozen=True)
class StorageCleanupPlan:
    alias: str
    root: Path
    referenced_keys: frozenset[str]
    file_keys: frozenset[str]
    orphan_keys: tuple[str, ...]
    young_orphan_keys: tuple[str, ...]


@dataclass(frozen=True)
class ImageOrphanCleanupResult:
    plans: tuple[StorageCleanupPlan, ...]
    deleted_keys: tuple[tuple[str, str], ...]

    @property
    def orphan_count(self) -> int:
        return sum(len(plan.orphan_keys) for plan in self.plans)

    @property
    def young_orphan_count(self) -> int:
        return sum(len(plan.young_orphan_keys) for plan in self.plans)


STORAGE_SPECS = (
    (
        "image_originals_private",
        "IMAGE_ORIGINALS_ROOT",
        ImageAsset,
        "private_storage_key",
    ),
    (
        "image_renditions_public",
        "IMAGE_RENDITIONS_ROOT",
        ImageRendition,
        "artifact_storage_key",
    ),
)


def _require_explicit_root(alias: str, setting_name: str) -> Path:
    raw_root = os.environ.get(setting_name)
    if raw_root is None or not raw_root.strip():
        raise ImageOrphanCleanupError(
            f"{setting_name} must be explicitly configured for orphan cleanup."
        )

    raw_path = Path(raw_root)
    if not raw_path.is_absolute():
        raise ImageOrphanCleanupError(f"{setting_name} must be absolute.")
    normalized = Path(os.path.normpath(raw_root))
    if raw_path != normalized:
        raise ImageOrphanCleanupError(f"{setting_name} must be normalized.")

    current = Path(raw_path.anchor)
    for part in raw_path.parts[1:]:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError as error:
            raise ImageOrphanCleanupError(
                f"{setting_name} does not exist: {raw_path}"
            ) from error
        if stat.S_ISLNK(mode):
            raise ImageOrphanCleanupError(
                f"{setting_name} must not contain symlink components."
            )

    if not raw_path.is_dir():
        raise ImageOrphanCleanupError(f"{setting_name} must be a directory.")

    configured_root = Path(getattr(settings, setting_name))
    if configured_root != raw_path:
        raise ImageOrphanCleanupError(
            f"{setting_name} does not match the loaded Django setting."
        )

    storage = storages[alias]
    if not isinstance(storage, FileSystemStorage):
        raise ImageOrphanCleanupError(
            f"{alias} must use FileSystemStorage for local orphan cleanup."
        )
    if Path(storage.location) != raw_path:
        raise ImageOrphanCleanupError(
            f"{alias} location does not match {setting_name}."
        )
    return raw_path


def _scan_files(root: Path) -> dict[str, float]:
    files: dict[str, float] = {}
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            entries = list(os.scandir(directory))
        except OSError as error:
            raise ImageOrphanCleanupError(
                f"Cannot scan image storage directory: {directory}"
            ) from error
        for entry in entries:
            path = Path(entry.path)
            if entry.is_symlink():
                raise ImageOrphanCleanupError(
                    f"Image storage contains a symlink and cleanup is blocked: {path}"
                )
            if entry.is_dir(follow_symlinks=False):
                pending.append(path)
                continue
            if not entry.is_file(follow_symlinks=False):
                raise ImageOrphanCleanupError(
                    f"Image storage contains an unsupported filesystem entry: {path}"
                )
            key = path.relative_to(root).as_posix()
            try:
                validate_storage_key(key)
            except ValidationError as error:
                raise ImageOrphanCleanupError(
                    f"Image storage contains an invalid key: {key}"
                ) from error
            try:
                files[key] = entry.stat(follow_symlinks=False).st_mtime
            except OSError as error:
                raise ImageOrphanCleanupError(
                    f"Cannot inspect image storage file: {path}"
                ) from error
    return files


def _build_plan(*, minimum_age_seconds: int, now: float) -> tuple[StorageCleanupPlan, ...]:
    plans: list[StorageCleanupPlan] = []
    cutoff = now - minimum_age_seconds
    for alias, setting_name, model, field_name in STORAGE_SPECS:
        root = _require_explicit_root(alias, setting_name)
        files = _scan_files(root)
        referenced = frozenset(model.objects.values_list(field_name, flat=True))
        missing = sorted(referenced - files.keys())
        if missing:
            raise ImageOrphanCleanupError(
                f"{alias} has {len(missing)} database-referenced file(s) missing; cleanup is blocked."
            )
        unreferenced = sorted(files.keys() - referenced)
        old = tuple(key for key in unreferenced if files[key] <= cutoff)
        young = tuple(key for key in unreferenced if files[key] > cutoff)
        plans.append(
            StorageCleanupPlan(
                alias=alias,
                root=root,
                referenced_keys=referenced,
                file_keys=frozenset(files),
                orphan_keys=old,
                young_orphan_keys=young,
            )
        )
    return tuple(plans)


def _directory_open_flags() -> int:
    try:
        return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    except AttributeError as error:
        raise ImageOrphanCleanupError(
            "This platform cannot provide no-follow directory deletion."
        ) from error


def _open_child_directory(parent_fd: int, component: str) -> int:
    return os.open(component, _directory_open_flags(), dir_fd=parent_fd)


def _open_root_directory(root: Path, stack: ExitStack) -> int:
    try:
        current_fd = os.open(root.anchor, _directory_open_flags())
        stack.callback(os.close, current_fd)
        for component in root.parts[1:]:
            current_fd = _open_child_directory(current_fd, component)
            stack.callback(os.close, current_fd)
        return current_fd
    except OSError as error:
        raise ImageOrphanCleanupError(
            f"Cannot securely open image storage root: {root}"
        ) from error


def _delete_regular_file_no_follow(*, root: Path, key: str, cutoff: float) -> None:
    try:
        validate_storage_key(key)
    except ValidationError as error:
        raise ImageOrphanCleanupError(f"Invalid deletion candidate key: {key}") from error

    components = key.split("/")
    try:
        with ExitStack() as stack:
            parent_fd = _open_root_directory(root, stack)
            for component in components[:-1]:
                parent_fd = _open_child_directory(parent_fd, component)
                stack.callback(os.close, parent_fd)

            file_name = components[-1]
            metadata = os.stat(file_name, dir_fd=parent_fd, follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode):
                raise ImageOrphanCleanupError(
                    f"Candidate is no longer a regular file: {key}"
                )
            if metadata.st_mtime > cutoff:
                raise ImageOrphanCleanupError(
                    f"Candidate became too young for deletion: {key}"
                )
            os.unlink(file_name, dir_fd=parent_fd)
    except ImageOrphanCleanupError:
        raise
    except FileNotFoundError as error:
        raise ImageOrphanCleanupError(
            f"Candidate disappeared before deletion: {key}"
        ) from error
    except OSError as error:
        raise ImageOrphanCleanupError(
            f"Failed secure no-follow deletion for orphan candidate: {key}"
        ) from error


def cleanup_image_storage_orphans(
    *,
    apply: bool = False,
    minimum_age_hours: int = 24,
    now: float | None = None,
) -> ImageOrphanCleanupResult:
    if isinstance(minimum_age_hours, bool) or minimum_age_hours < 0:
        raise ImageOrphanCleanupError("minimum_age_hours must be a non-negative integer.")
    minimum_age_seconds = minimum_age_hours * 60 * 60
    plan_now = time.time() if now is None else now
    plans = _build_plan(
        minimum_age_seconds=minimum_age_seconds,
        now=plan_now,
    )
    if not apply:
        return ImageOrphanCleanupResult(plans=plans, deleted_keys=())

    deleted: list[tuple[str, str]] = []
    model_by_alias = {
        alias: (model, field_name)
        for alias, _, model, field_name in STORAGE_SPECS
    }
    with transaction.atomic():
        try:
            acquire_image_storage_cleanup_lock()
        except ImageStorageRuntimeLockError as error:
            raise ImageOrphanCleanupError(
                "Apply requires PostgreSQL advisory locking and is unavailable."
            ) from error

        table_names = ", ".join(
            connection.ops.quote_name(model._meta.db_table)
            for model in (ImageAsset, ImageRendition)
        )
        with connection.cursor() as cursor:
            cursor.execute(f"LOCK TABLE {table_names} IN SHARE MODE")

        # Rebuild the complete plan while writes to both reference tables are
        # blocked. A new reference, missing file, symlink, special entry, or
        # root/backend mismatch blocks deletion.
        apply_now = time.time() if now is None else now
        plans = _build_plan(
            minimum_age_seconds=minimum_age_seconds,
            now=apply_now,
        )
        cutoff = apply_now - minimum_age_seconds
        for plan in plans:
            model, field_name = model_by_alias[plan.alias]
            for key in plan.orphan_keys:
                if model.objects.filter(**{field_name: key}).exists():
                    raise ImageOrphanCleanupError(
                        f"{plan.alias} key became referenced; cleanup stopped before deleting it."
                    )
                _delete_regular_file_no_follow(root=plan.root, key=key, cutoff=cutoff)
                deleted.append((plan.alias, key))
    return ImageOrphanCleanupResult(plans=plans, deleted_keys=tuple(deleted))
