# Codex Handover

This repository has active Codex-driven work on the branch `import-review-work-v2`.

## Current branch and baseline

- Active branch: `import-review-work-v2`
- Latest verified commit at handover time: `81c73ba` (`Fix people import review and safer person contact merging`)

Before starting new work, check:

```bash
git branch --show-current
git log --oneline -5
git status --short
```

## Project focus right now

Current work has centered on:

- import/review/commit flows for `AKTØRER` and `PERSONER`
- AI-assisted import enrichment
- duplicate handling
- taxonomy persistence on commit
- review UX in `frontend/src/pages/ImportExportPage.tsx`
- staging deploys and fast verification loops

## Most important files

- `frontend/src/pages/ImportExportPage.tsx`
  Main review UI and modal behavior for import jobs.
- `crm/services/import/commit.py`
  Commit behavior for organizations, persons, contacts, taxonomy, and linking.
- `crm/services/import/preview.py`
  Preview status, row outcome logic, and AI rerun reset behavior.
- `crm/services/import/ai_suggestions.py`
  Suggestion building and provider merge behavior.
- `crm/services/import/search_enrichment.py`
  Search retrieval, candidate filtering, website/social signal extraction.
- `crm/services/import/matchers.py`
  Duplicate and exact/fuzzy entity matching.
- `crm/tests.py`
  High-value regression coverage for import, review, commit, and staging-sensitive flows.

## Recent behavior changes already implemented

- PERSONER review modal now supports:
  - choosing an existing person on duplicate candidates
  - showing `person_secondary_emails`
  - safer email conflict handling for existing people
  - creating/linking organizations with inherited review taxonomy and publish state
- Duplicate persons inside the same import list are now flagged for review.
- Search enrichment now filters phone-directory style hosts such as:
  - `gulesider.no`
  - `1881.no`
  - `180.no`
- Actor card UI on staging was recently tuned heavily; avoid casual regressions there unless the user explicitly wants card/layout work.

## Local verification

Frontend:

```bash
cd frontend
PATH=/Users/fredrikforssman/local/node/bin:$PATH npm run build
```

Targeted Django tests used repeatedly in this project:

```bash
cd /Users/fredrikforssman/Documents/GitHub/kreative-norge-crm
DB_HOST=127.0.0.1 /Users/fredrikforssman/kreative-norge-crm/.venv/bin/python manage.py test crm.tests.ImportPhaseTwoApiTests -v 2 --keepdb --noinput
```

Useful smaller examples:

```bash
DB_HOST=127.0.0.1 /Users/fredrikforssman/kreative-norge-crm/.venv/bin/python manage.py test crm.tests.ImportPhaseTwoApiTests.test_preview_marks_duplicate_person_in_same_import_for_review -v 2 --keepdb --noinput

DB_HOST=127.0.0.1 /Users/fredrikforssman/kreative-norge-crm/.venv/bin/python manage.py test crm.tests.ImportPhaseTwoApiTests.test_commit_using_existing_person_preserves_primary_email_and_adds_secondary_email -v 2 --keepdb --noinput
```

## Staging deploy notes

Staging server path:

```text
/srv/kreative-norge-crm
```

Important staging quirk:

- The server currently works with `docker-compose`
- `docker compose` did not work reliably there during the last deploy session

Working deploy pattern:

```bash
git push origin import-review-work-v2
ssh root@<server>
cd /srv/kreative-norge-crm
git fetch origin
git checkout import-review-work-v2
git pull --ff-only origin import-review-work-v2
docker-compose -f docker-compose.staging.yml --env-file .env.staging down
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d --build
```

Quick verification on staging:

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging ps
curl -s http://127.0.0.1:8080/index.html | grep assets/index
docker-compose -f docker-compose.staging.yml --env-file .env.staging logs --tail=20 api
```

## Working style expectations

- Prefer targeted fixes with regression tests when touching import/review/commit logic.
- If the user mentions staging behavior, verify both code and actual deployed asset hash when possible.
- Avoid reverting user changes in a dirty worktree.
- Use `apply_patch` for manual edits.
- If changing import behavior, inspect both frontend review state and backend commit behavior together.

## Recommended pre-upgrade checklist

Before switching to a newer Codex version:

1. Make sure the working tree is clean.
2. Push the active branch to origin.
3. Keep this `AGENTS.md` committed in the repo.
4. Keep the latest validated commit hash handy.
5. After upgrading, ask the new agent to read:
   - `AGENTS.md`
   - `README.md`
   - `deploy/staging/README.md`
   - relevant diffs from the latest 5-10 commits
