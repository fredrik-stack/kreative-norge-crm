from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any


CATEGORIES = {"logo", "photo", "mobile_photo", "poster", "illustration", "other"}
FITS = {"contain", "cover"}
VARIANTS = {"square", "landscape", "share"}
RIGHTS_BASES = {"owned", "explicit_permission", "open_license", "internal_test_only"}
REVIEW_THEMES = {
    "crop",
    "relevant_content",
    "color_shift",
    "sharpness",
    "compression",
    "logo_legibility",
    "internal_whitespace",
    "poster_or_text",
    "watermark",
}
EXPECTED_RESULTS = {"success", "controlled_error"}
ROOT_FIELDS = {"$schema", "version", "fixtures"}
FIXTURE_FIELDS = {
    "fixture_id",
    "filename",
    "category",
    "intended_fit",
    "expected_variants",
    "rights_basis",
    "redistribution_allowed",
    "contains_person",
    "expected_color_profile",
    "review_themes",
    "notes",
    "expected_result",
    "expected_error_code",
}
REQUIRED_FIXTURE_FIELDS = FIXTURE_FIELDS - {"expected_result", "expected_error_code"}
FIXTURE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,79}$")


class ManifestError(ValueError):
    """A deterministic, user-facing dataset-contract error."""


@dataclass(frozen=True)
class Fixture:
    fixture_id: str
    filename: str
    path: Path
    category: str
    intended_fit: str
    expected_variants: tuple[str, ...]
    rights_basis: str
    redistribution_allowed: bool
    contains_person: bool
    expected_color_profile: str | None
    review_themes: tuple[str, ...]
    notes: str
    expected_result: str
    expected_error_code: str | None

    def worker_payload(self) -> dict[str, Any]:
        return {
            "fixture_id": self.fixture_id,
            "path": str(self.path),
            "category": self.category,
            "intended_fit": self.intended_fit,
            "expected_variants": list(self.expected_variants),
            "rights_basis": self.rights_basis,
            "redistribution_allowed": self.redistribution_allowed,
            "contains_person": self.contains_person,
            "expected_color_profile": self.expected_color_profile,
            "review_themes": list(self.review_themes),
            "notes": self.notes,
            "expected_result": self.expected_result,
            "expected_error_code": self.expected_error_code,
        }


@dataclass(frozen=True)
class Manifest:
    path: Path
    dataset_root: Path
    fixtures: tuple[Fixture, ...]
    checksum: str


def _exact_type(value: Any, expected: type, label: str) -> None:
    if type(value) is not expected:
        raise ManifestError(f"{label} must be {expected.__name__}")


def _string(value: Any, label: str, *, max_length: int | None = None) -> str:
    _exact_type(value, str, label)
    if not value:
        raise ManifestError(f"{label} cannot be empty")
    if max_length is not None and len(value) > max_length:
        raise ManifestError(f"{label} exceeds {max_length} characters")
    return value


def _string_list(value: Any, label: str, *, allowed: set[str], require_value: bool) -> tuple[str, ...]:
    _exact_type(value, list, label)
    if require_value and not value:
        raise ManifestError(f"{label} cannot be empty")
    values: list[str] = []
    for index, item in enumerate(value):
        item = _string(item, f"{label}[{index}]")
        if item not in allowed:
            raise ManifestError(f"{label}[{index}] has unknown value: {item}")
        values.append(item)
    if len(values) != len(set(values)):
        raise ManifestError(f"{label} contains duplicates")
    return tuple(values)


def _source_path(dataset_root: Path, filename: str) -> Path:
    candidate = PurePosixPath(filename)
    if candidate.is_absolute() or Path(filename).is_absolute():
        raise ManifestError(f"filename must be relative: {filename}")
    if ".." in candidate.parts:
        raise ManifestError(f"filename contains path traversal: {filename}")
    if not candidate.parts or candidate.parts[0] != "files":
        raise ManifestError(f"filename must be below files/: {filename}")
    files_root = (dataset_root / "files").resolve()
    resolved = (dataset_root / Path(*candidate.parts)).resolve()
    if resolved == files_root or files_root not in resolved.parents:
        raise ManifestError(f"filename escapes files/: {filename}")
    if not resolved.is_file():
        raise ManifestError(f"source file is missing: {filename}")
    return resolved


def _fixture(raw: Any, index: int, dataset_root: Path) -> Fixture:
    label = f"fixtures[{index}]"
    _exact_type(raw, dict, label)
    unknown = set(raw) - FIXTURE_FIELDS
    missing = REQUIRED_FIXTURE_FIELDS - set(raw)
    if unknown:
        raise ManifestError(f"{label} has unexpected fields: {', '.join(sorted(unknown))}")
    if missing:
        raise ManifestError(f"{label} is missing fields: {', '.join(sorted(missing))}")

    fixture_id = _string(raw["fixture_id"], f"{label}.fixture_id")
    if not FIXTURE_ID.fullmatch(fixture_id):
        raise ManifestError(f"{label}.fixture_id has invalid format")
    filename = _string(raw["filename"], f"{label}.filename")
    category = _string(raw["category"], f"{label}.category")
    if category not in CATEGORIES:
        raise ManifestError(f"{label}.category has unknown value: {category}")
    intended_fit = _string(raw["intended_fit"], f"{label}.intended_fit")
    if intended_fit not in FITS:
        raise ManifestError(f"{label}.intended_fit has unknown value: {intended_fit}")
    rights_basis = _string(raw["rights_basis"], f"{label}.rights_basis")
    if rights_basis not in RIGHTS_BASES:
        raise ManifestError(f"{label}.rights_basis has unknown value: {rights_basis}")
    _exact_type(raw["redistribution_allowed"], bool, f"{label}.redistribution_allowed")
    _exact_type(raw["contains_person"], bool, f"{label}.contains_person")
    color_profile = raw["expected_color_profile"]
    if color_profile is not None:
        color_profile = _string(color_profile, f"{label}.expected_color_profile", max_length=100)
    notes = raw["notes"]
    _exact_type(notes, str, f"{label}.notes")
    if len(notes) > 500:
        raise ManifestError(f"{label}.notes exceeds 500 characters")
    expected_result = raw.get("expected_result", "success")
    expected_result = _string(expected_result, f"{label}.expected_result")
    if expected_result not in EXPECTED_RESULTS:
        raise ManifestError(f"{label}.expected_result has unknown value: {expected_result}")
    expected_error_code = raw.get("expected_error_code")
    if expected_result == "success":
        if expected_error_code is not None:
            raise ManifestError(
                f"{label}.expected_error_code must be omitted or null when expected_result is success"
            )
    else:
        if expected_error_code is None:
            raise ManifestError(
                f"{label}.expected_error_code is required when expected_result is controlled_error"
            )
        expected_error_code = _string(
            expected_error_code,
            f"{label}.expected_error_code",
            max_length=100,
        )
        if not expected_error_code.strip():
            raise ManifestError(f"{label}.expected_error_code cannot be empty")

    return Fixture(
        fixture_id=fixture_id,
        filename=filename,
        path=_source_path(dataset_root, filename),
        category=category,
        intended_fit=intended_fit,
        expected_variants=_string_list(
            raw["expected_variants"],
            f"{label}.expected_variants",
            allowed=VARIANTS,
            require_value=True,
        ),
        rights_basis=rights_basis,
        redistribution_allowed=raw["redistribution_allowed"],
        contains_person=raw["contains_person"],
        expected_color_profile=color_profile,
        review_themes=_string_list(
            raw["review_themes"],
            f"{label}.review_themes",
            allowed=REVIEW_THEMES,
            require_value=False,
        ),
        notes=notes,
        expected_result=expected_result,
        expected_error_code=expected_error_code,
    )


def load_manifest(dataset_root: Path) -> Manifest:
    dataset_root = dataset_root.resolve()
    if not dataset_root.is_dir():
        raise ManifestError(f"dataset root is missing: {dataset_root}")
    manifest_path = dataset_root / "manifest.json"
    if not manifest_path.is_file():
        raise ManifestError(f"manifest is missing: {manifest_path}")
    data = manifest_path.read_bytes()
    try:
        raw = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"manifest is not valid UTF-8 JSON: {exc}") from exc
    _exact_type(raw, dict, "manifest")
    unknown = set(raw) - ROOT_FIELDS
    missing = {"version", "fixtures"} - set(raw)
    if unknown:
        raise ManifestError(f"manifest has unexpected fields: {', '.join(sorted(unknown))}")
    if missing:
        raise ManifestError(f"manifest is missing fields: {', '.join(sorted(missing))}")
    if type(raw["version"]) is not int or raw["version"] != 1:
        raise ManifestError("manifest.version must be integer 1")
    if "$schema" in raw:
        _string(raw["$schema"], "manifest.$schema")
    _exact_type(raw["fixtures"], list, "manifest.fixtures")
    if not raw["fixtures"]:
        raise ManifestError("manifest.fixtures cannot be empty")
    fixtures = tuple(_fixture(item, index, dataset_root) for index, item in enumerate(raw["fixtures"]))
    ids = [item.fixture_id for item in fixtures]
    filenames = [item.path for item in fixtures]
    if len(ids) != len(set(ids)):
        raise ManifestError("manifest contains duplicate fixture_id")
    if len(filenames) != len(set(filenames)):
        raise ManifestError("manifest contains duplicate source file")
    from hashlib import sha256

    return Manifest(
        path=manifest_path,
        dataset_root=dataset_root,
        fixtures=fixtures,
        checksum=sha256(data).hexdigest(),
    )
