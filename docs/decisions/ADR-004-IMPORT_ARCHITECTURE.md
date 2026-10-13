# ADR-004: Import med preview og review før commit

**Datert videreføring 2026-10-13:** ADR-004 beskriver den implementerte legacyimportens jobb-/preview-/review-/commitprinsipp. [ADR-013](ADR-013-IMPORT_2_0_EXECUTION_AND_COMMIT_CONTRACT.md) presiserer godkjent v2-målkontrakt uten runtimeimplementering; [5E-planen](../status/PHASE_5E_IMPLEMENTATION_AND_TEST_PLAN_2026-10-13.md) angir senere leveranser og tester. Dagens legacykode er fortsatt aktiv. Dokumentasjonsleveransen er lagret på `docs/phase5e-approved-plan` og leveres gjennom [PR #74](https://github.com/fredrik-stack/kreative-norge-crm/pull/74); review er gjennomført uten blokkerende funn og kontrollert merge er bestilt 2026-10-13. Faktisk mergestatus og CI følger GitHub.

## Status

Godkjent og implementert.

## Bakgrunn

Import påvirker flere modeller og kan inneholde konflikter, feil og duplikater.

## Beslutning

Import kjøres som jobb med parsing, normalisering, validering, matching, forslag, radvis review og eksplisitt commit.

## Konsekvenser

Import skal ikke behandles som en enkel loop over ordinære CRUD-endepunkter. Beslutninger og commit-resultater skal være sporbare.