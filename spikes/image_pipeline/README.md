# Phase 3B.1 image rendition lab

**Status:** Isolated prototype. Not production-ready and not imported by the CRM runtime.

This lab tests the image-processing choices approved for investigation in ADR-007. It generates only synthetic fixtures and performs no network fetches.

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

Pillow and pyvips/libvips are both tested. The exact `pyvips-binary` package that the official binary extra resolves to is pinned explicitly, together with its Python bridge dependencies, so the comparison can be repeated without changing the production Docker image. The report records its operational trade-offs; this file does not select a production dependency.

## Prototype contract

- prototype variants: `square` 512 × 512 and `landscape` 800 × 450
- approved share size: `share` 1200 × 630
- logo/name mark: `contain`, controlled 8% padding, preserved alpha, no upscaling
- photo: `cover`, one normalized focus point, EXIF orientation before crop, no upscaling
- maximum file size: 15 MiB
- maximum decoded size: 20 megapixels
- public rendition encoders strip EXIF, ICC, XMP and comments
- output keys include source checksum, processing version and canonical render configuration

Square and landscape sizes, byte/pixel limits and quality bands are prototype recommendations only. They require owner approval before phase 3C.
