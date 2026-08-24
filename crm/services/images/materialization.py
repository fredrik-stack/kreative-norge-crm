from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import os
from pathlib import Path
import stat
import uuid

from django.conf import settings
from django.core.files.storage import storages
from PIL import Image, UnidentifiedImageError

from crm.validators import validate_storage_key
from image_safety.release_keys import REQUIRED_RELEASE_VARIANTS, build_public_release_key


class ImageMaterializationError(RuntimeError):
    pass


class ImageMaterializationConflict(ImageMaterializationError):
    pass


@dataclass(frozen=True)
class MaterializationInput:
    release_id: str
    variant: str
    output_format: str
    width: int
    height: int
    file_size_bytes: int
    artifact_storage_key: str
    checksum_sha256: str
    public_storage_key: str


@dataclass(frozen=True)
class MaterializationResult:
    public_storage_key: str
    created: bool


@dataclass(frozen=True)
class DeliveryDeletionResult:
    public_storage_key: str
    deleted: bool


_FORMAT_NAMES = {"jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
_READ_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)


def _read_artifact(item: MaterializationInput) -> bytes:
    validate_storage_key(item.artifact_storage_key)
    storage = storages["image_renditions_public"]
    try:
        with storage.open(item.artifact_storage_key, "rb") as source:
            data = source.read(item.file_size_bytes + 1)
    except (OSError, ValueError) as error:
        raise ImageMaterializationError("Rendition artifact is unavailable.") from error
    if len(data) != item.file_size_bytes:
        raise ImageMaterializationConflict("Rendition artifact size has changed.")
    _verify_bytes(data, item)
    return data


def _verify_bytes(data: bytes, item: MaterializationInput) -> None:
    if sha256(data).hexdigest() != item.checksum_sha256:
        raise ImageMaterializationConflict("Rendition checksum does not match its snapshot.")
    try:
        with Image.open(BytesIO(data)) as image:
            image.load()
            actual_format = image.format
            actual_size = image.size
            frames = getattr(image, "n_frames", 1)
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ImageMaterializationConflict("Rendition bytes are not a valid image.") from error
    if (
        actual_format != _FORMAT_NAMES.get(item.output_format)
        or actual_size != (item.width, item.height)
        or frames != 1
    ):
        raise ImageMaterializationConflict(
            "Rendition image metadata does not match its database snapshot."
        )


def _open_delivery_root(*, create: bool) -> int:
    root = Path(settings.PUBLIC_IMAGE_DELIVERY_ROOT)
    if (
        not root.is_absolute()
        or root == Path(root.anchor)
        or any(component in {".", ".."} for component in root.parts)
    ):
        raise ImageMaterializationError("Delivery root is not a safe absolute path.")
    descriptor = os.open("/", _DIRECTORY_FLAGS)
    try:
        components = root.parts[1:]
        for index, component in enumerate(components):
            try:
                child = os.open(component, _DIRECTORY_FLAGS, dir_fd=descriptor)
            except FileNotFoundError:
                if not create or index != len(components) - 1:
                    raise ImageMaterializationError(
                        "Delivery root is not provisioned."
                    )
                os.mkdir(component, mode=0o750, dir_fd=descriptor)
                child = os.open(component, _DIRECTORY_FLAGS, dir_fd=descriptor)
            except OSError as error:
                raise ImageMaterializationError(
                    "Delivery root contains an unsafe path component."
                ) from error
            os.close(descriptor)
            descriptor = child
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _open_or_create_directory(parent_fd: int, name: str) -> int:
    try:
        return os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
    except FileNotFoundError:
        try:
            os.mkdir(name, mode=0o750, dir_fd=parent_fd)
        except FileExistsError:
            pass
        try:
            return os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
        except OSError as error:
            raise ImageMaterializationError(
                "Delivery directory is not a safe directory."
            ) from error
    except OSError as error:
        raise ImageMaterializationError(
            "Delivery directory is not a safe directory."
        ) from error


def _read_existing(directory_fd: int, filename: str, item: MaterializationInput) -> None:
    try:
        descriptor = os.open(filename, _READ_FLAGS, dir_fd=directory_fd)
    except FileNotFoundError:
        raise
    except OSError as error:
        raise ImageMaterializationError("Delivery object cannot be opened safely.") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ImageMaterializationConflict("Delivery object is not a regular file.")
        chunks = []
        remaining = item.file_size_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
    finally:
        os.close(descriptor)
    if len(data) != item.file_size_bytes:
        raise ImageMaterializationConflict("Delivery object size conflicts with the snapshot.")
    _verify_bytes(data, item)


def _materialize_one(item: MaterializationInput, data: bytes) -> MaterializationResult:
    validate_storage_key(item.public_storage_key)
    expected_key = build_public_release_key(
        item.release_id, item.variant, item.output_format
    )
    if item.public_storage_key != expected_key:
        raise ImageMaterializationError("Delivery key is not canonical.")

    root_fd = _open_delivery_root(create=True)
    releases_fd = release_fd = None
    temporary_name = f".materializing-{uuid.uuid4().hex}"
    try:
        releases_fd = _open_or_create_directory(root_fd, "releases")
        release_fd = _open_or_create_directory(releases_fd, item.release_id)
        filename = item.public_storage_key.rsplit("/", 1)[-1]
        try:
            _read_existing(release_fd, filename, item)
            return MaterializationResult(item.public_storage_key, False)
        except FileNotFoundError:
            pass

        temporary_fd = os.open(
            temporary_name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0),
            0o640,
            dir_fd=release_fd,
        )
        try:
            view = memoryview(data)
            while view:
                written = os.write(temporary_fd, view)
                if written <= 0:
                    raise ImageMaterializationError("Delivery write did not make progress.")
                view = view[written:]
            os.fsync(temporary_fd)
        finally:
            os.close(temporary_fd)
        _read_existing(release_fd, temporary_name, item)
        try:
            os.link(
                temporary_name,
                filename,
                src_dir_fd=release_fd,
                dst_dir_fd=release_fd,
                follow_symlinks=False,
            )
            created = True
            os.fsync(release_fd)
        except FileExistsError:
            created = False
        _read_existing(release_fd, filename, item)
        return MaterializationResult(item.public_storage_key, created)
    finally:
        if release_fd is not None:
            try:
                os.unlink(temporary_name, dir_fd=release_fd)
            except FileNotFoundError:
                pass
            os.close(release_fd)
        if releases_fd is not None:
            os.close(releases_fd)
        os.close(root_fd)


def verify_materialized_rendition(item: MaterializationInput) -> None:
    root_fd = _open_delivery_root(create=False)
    releases_fd = release_fd = None
    try:
        releases_fd = os.open("releases", _DIRECTORY_FLAGS, dir_fd=root_fd)
        release_fd = os.open(item.release_id, _DIRECTORY_FLAGS, dir_fd=releases_fd)
        _read_existing(
            release_fd,
            item.public_storage_key.rsplit("/", 1)[-1],
            item,
        )
    except (FileNotFoundError, OSError) as error:
        raise ImageMaterializationError(
            "Complete delivery set cannot be opened safely."
        ) from error
    finally:
        if release_fd is not None:
            os.close(release_fd)
        if releases_fd is not None:
            os.close(releases_fd)
        os.close(root_fd)


def materialize_release(
    items: tuple[MaterializationInput, ...],
) -> tuple[MaterializationResult, ...]:
    if not settings.PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED:
        raise ImageMaterializationError("Public image materialization is disabled.")
    if len(items) != 3:
        raise ImageMaterializationError("A release requires exactly three renditions.")
    if {item.variant for item in items} != REQUIRED_RELEASE_VARIANTS:
        raise ImageMaterializationError(
            "A release requires square, landscape, and share exactly once."
        )
    results = []
    for item in items:
        data = _read_artifact(item)
        results.append(_materialize_one(item, data))
    # Re-open the complete set only after all writes/reuses have succeeded so
    # activation can never rely on a partial or earlier-only verification.
    for item in items:
        verify_materialized_rendition(item)
    return tuple(results)


def delete_materialized_release(
    items: tuple[MaterializationInput, ...],
) -> tuple[DeliveryDeletionResult, ...]:
    """Delete exactly one canonical three-variant release without following links."""
    if len(items) != 3 or {item.variant for item in items} != REQUIRED_RELEASE_VARIANTS:
        raise ImageMaterializationError(
            "Release deletion requires square, landscape, and share exactly once."
        )
    release_ids = {item.release_id for item in items}
    if len(release_ids) != 1:
        raise ImageMaterializationError("Release deletion scope is inconsistent.")
    release_id = next(iter(release_ids))
    for item in items:
        validate_storage_key(item.public_storage_key)
        if item.public_storage_key != build_public_release_key(
            release_id, item.variant, item.output_format
        ):
            raise ImageMaterializationError("Release deletion key is not canonical.")

    root_fd = _open_delivery_root(create=False)
    releases_fd = release_fd = None
    results: list[DeliveryDeletionResult] = []
    try:
        releases_fd = os.open("releases", _DIRECTORY_FLAGS, dir_fd=root_fd)
        release_fd = os.open(release_id, _DIRECTORY_FLAGS, dir_fd=releases_fd)
        for item in sorted(items, key=lambda value: value.variant):
            filename = item.public_storage_key.rsplit("/", 1)[-1]
            try:
                descriptor = os.open(filename, _READ_FLAGS, dir_fd=release_fd)
            except FileNotFoundError:
                results.append(DeliveryDeletionResult(item.public_storage_key, False))
                continue
            except OSError as error:
                raise ImageMaterializationError(
                    "Delivery object cannot be opened safely for deletion."
                ) from error
            try:
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise ImageMaterializationError(
                        "Delivery deletion target is not a regular file."
                    )
            finally:
                os.close(descriptor)
            try:
                os.unlink(filename, dir_fd=release_fd)
            except FileNotFoundError:
                results.append(DeliveryDeletionResult(item.public_storage_key, False))
            except OSError as error:
                raise ImageMaterializationError(
                    "Delivery object could not be deleted safely."
                ) from error
            else:
                results.append(DeliveryDeletionResult(item.public_storage_key, True))
        os.fsync(release_fd)
        return tuple(results)
    except (FileNotFoundError, OSError) as error:
        raise ImageMaterializationError(
            "Release delivery directory cannot be opened safely."
        ) from error
    finally:
        if release_fd is not None:
            os.close(release_fd)
        if releases_fd is not None:
            os.close(releases_fd)
        os.close(root_fd)
