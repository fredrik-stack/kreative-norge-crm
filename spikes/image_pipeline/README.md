# Phase 3B.1 image rendition lab

**Status:** Isolated prototype. Not production-ready and not imported by the CRM runtime.

This lab tests the image-processing choices investigated in ADR-007. The owner-approved processing profile v1 and the remaining quality gates are documented in [ADR-007](../../docs/decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md#23-fase-3b1-godkjent-processingkontrakt-v1). The lab generates only synthetic fixtures and performs no network fetches.

## Isolation contract

- dependencies are pinned in this directory and are not added to root `requirements.txt`
- the package is not a Django app and is not imported by `crm/`, `config/`, Editor or PUBLIC
- no models, migrations, API routes, storage settings or deployment files are changed
- generated working output should be written outside the repository or to an ignored local directory
- the dedicated Dockerfile builds only this lab

## Reproduce locally

```bash
python3 -m venv /tmp/phase3b1-image-lab-venv
/tmp/phase3b1-image-lab-venv/bin/pip install -r spikes/image_pipeline/requirements.txt
PYTHONPATH=spikes/image_pipeline \
  /tmp/phase3b1-image-lab-venv/bin/python -m unittest discover \
  -s spikes/image_pipeline/tests -v
PYTHONPATH=spikes/image_pipeline \
  /tmp/phase3b1-image-lab-venv/bin/python spikes/image_pipeline/run_lab.py \
  --output /tmp/phase3b1-image-lab-output --iterations 3
```

## Reproduce in the isolated container

```bash
docker build -t kreative-norge-phase3b1-lab spikes/image_pipeline
docker run --rm kreative-norge-phase3b1-lab
```

Pillow and pyvips/libvips are both tested. The exact `pyvips-binary` package that the official binary extra resolves to is pinned explicitly, together with its Python bridge dependencies, so the comparison can be repeated without changing the production Docker image. ADR-007 records Pillow as the first MVP direction; these lab pins remain isolated and do not introduce a root runtime dependency.

## Prototype contract

- processing profile v1 variants: `square` 512 × 512, `landscape` 800 × 450 and `share` 1200 × 630
- logo/name mark: `contain`, controlled 8% padding, preserved alpha, no upscaling
- photo: `cover`, one normalized focus point, EXIF orientation before crop, no upscaling
- approved configurable maximum file-size default: 15 MiB
- prototype-only maximum decoded size: 20 megapixels
- public rendition encoders strip EXIF, ICC, XMP and comments
- output keys include source checksum, processing version and canonical render configuration

The 20-megapixel limit, universal shortest-side bands and edge-variance/blur bands remain prototype values. Phase 3B.1R must set representative pixel, dimension and quality rules and prove explicit sRGB normalization before actual image processing or storage runtime.

## Representative-quality harness

Phase 3B.1R-A extends this isolated lab with a local dataset contract and runner; see [`representative/README.md`](representative/README.md). It validates a private, Git-ignored manifest, analyzes each fixture in a child process, compares profile-free and standard-sRGB-profile output candidates, records advisory quality/resource measurements, and creates a local static review report plus a redacted machine-readable summary.

The harness performs no downloads and is not imported by CRM runtime. Its existence does not complete phase 3B.1R: a rights-cleared local dataset, a representative run, manual evidence review, and separate approval of any final quality or sRGB rule are still required.
