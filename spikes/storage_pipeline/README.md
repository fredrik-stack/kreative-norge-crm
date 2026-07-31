# Phase 3B.2 storage, takedown and restore lab

**Status:** Isolated prototype evidence. This is not production storage and is not imported by the CRM runtime.

The lab exercises the storage boundary approved for investigation in ADR-007. It uses only synthetic bytes and the three static emergency fallbacks from phase 3B.1. Moto Server is an S3 protocol emulator, not a selected storage provider.

## Isolation contract

- all Python dependencies are exact pins in this directory
- `test_settings.py` declares `default`, `staticfiles`, `image_originals_private` and `image_renditions_public` without changing `config/settings.py`
- the phase 3B.1 immutable rendition-key function is imported as a prototype contract; no new key algorithm is introduced
- no model, migration, API, Editor, PUBLIC, root requirement, production container or deployment configuration is changed
- the deny journal lives outside the application-state snapshot
- the cache purge is a recording fake and does not claim to implement a real CDN API

## Reproduce locally

```bash
python3 -m venv /tmp/phase3b2-storage-lab-venv
/tmp/phase3b2-storage-lab-venv/bin/pip install -r spikes/storage_pipeline/requirements.txt

PHASE3B2_S3_ENDPOINT=http://localhost:5000 \
  /tmp/phase3b2-storage-lab-venv/bin/moto_server -H localhost -p 5000
```

In another terminal:

```bash
PYTHONPATH=spikes/storage_pipeline:spikes/image_pipeline \
DJANGO_SETTINGS_MODULE=test_settings \
PHASE3B2_S3_ENDPOINT=http://localhost:5000 \
  /tmp/phase3b2-storage-lab-venv/bin/python -m unittest discover \
  -s spikes/storage_pipeline/tests -v

PYTHONPATH=spikes/storage_pipeline:spikes/image_pipeline \
DJANGO_SETTINGS_MODULE=test_settings \
PHASE3B2_S3_ENDPOINT=http://localhost:5000 \
  /tmp/phase3b2-storage-lab-venv/bin/python spikes/storage_pipeline/run_lab.py \
  --output /tmp/phase3b2-storage-evidence.json
```

Stop Moto after the run. No AWS, staging or production credentials are required.

## Reproduce in isolated containers

The build context is the repository root because this lab deliberately imports the phase 3B.1 key contract and fallback files:

```bash
docker compose -f spikes/storage_pipeline/docker-compose.yml up \
  --build --abort-on-container-exit --exit-code-from lab
docker compose -f spikes/storage_pipeline/docker-compose.yml down --volumes
```

The Compose file contains only the disposable Moto emulator and the lab container. It is unrelated to the repository's ordinary development and staging Compose files.

## What the lab proves

- separate Django storage aliases while default filesystem storage and staticfiles remain present
- private and public S3 buckets with explicit access, content-type and cache behavior in Moto
- private version history and delete-marker behavior
- the risk of old version IDs in a publicly readable versioned bucket
- distinct processing-artifact and public-release identities
- immutable object conflict detection
- append/replay/idempotency for an append-only-oriented deny journal
- T0–T5 takedown, stale-cache purge, old-snapshot restore, reconciliation and R2 release
- direct active-rendition backup versus deterministic regeneration through a recording renderer
- host-independent absolute public-origin construction
- static fallback without S3, database, renderer or provider

It does not prove complete IAM conditions, cloud-provider consistency, signed private access, a production CDN purge API, durable tamper evidence, cross-region backup, or any CRM runtime integration.
