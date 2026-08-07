# Phase 3B.1R representative dataset

**Status:** Local contract for a rights-cleared dataset. No representative source files are committed.

This directory defines the input contract for the isolated representative-quality lab. It does not make phase 3B.1R complete and it does not set final image-quality thresholds.

## Local layout

```text
representative/
  manifest.schema.json
  manifest.example.json
  private_dataset/       # Git-ignored
    manifest.json        # Git-ignored with its parent
    files/               # Git-ignored with its parent
```

Copy `manifest.example.json` to `private_dataset/manifest.json`, place rights-cleared files below `private_dataset/files/`, and replace the example fixtures. Filenames must be relative, remain below `files/`, and must not contain `..`. Symlinks that resolve outside the dataset are rejected.

Allowed categories are `logo`, `photo`, `mobile_photo`, `poster`, `illustration`, and `other`. Fit is `contain` or `cover`. Rights basis is `owned`, `explicit_permission`, `open_license`, or `internal_test_only`. Review themes are selected from `crop`, `relevant_content`, `color_shift`, `sharpness`, `compression`, `logo_legibility`, `internal_whitespace`, `poster_or_text`, and `watermark`.

`expected_result=controlled_error` is only for a deliberately retained corrupt/unsupported test source and requires a non-empty `expected_error_code`. The runner requires an exact error-code match; no wildcard is supported. Ordinary files default to `success`, where `expected_error_code` must be omitted or `null`.

## Run locally

Use an output directory outside the source dataset, normally below `/tmp`:

```bash
PYTHONPATH=spikes/image_pipeline \
  python spikes/image_pipeline/run_representative_lab.py \
  --dataset-root spikes/image_pipeline/representative/private_dataset \
  --output-root /tmp/kreative-phase3b1r-evidence
```

The runner performs no network access and does not modify the dataset. Every fixture is analyzed in an isolated child process. Local `review.html`, previews, renditions, and the contact sheet may contain source pixels and must remain local unless **every** included fixture has `redistribution_allowed=true`.

Opaque original previews use metadata-stripped JPEG. Transparent previews use metadata-stripped PNG so alpha is preserved. The local HTML shows transparent previews on a deterministic neutral checkerboard, and the JPEG contact sheet explicitly composites them onto the same checkerboard rather than flattening them to an implicit background.

`redacted-summary.json` contains fixture IDs, checksums, technical measurements, and aggregates only. It never contains previews or base64 image data. The harness and schema may be committed. Generated visual evidence requires the redistribution gate; private source files and manifests must never be committed.

Candidate pixel limits and all blur, blockiness, logo-legibility, dimension, warning, and sRGB-output choices remain advisory until a separate phase 3B.1R-B evidence review approves them.
