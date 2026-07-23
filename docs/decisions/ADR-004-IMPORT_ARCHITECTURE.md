# ADR-004: Import med preview og review før commit

## Status

Godkjent og implementert.

## Bakgrunn

Import påvirker flere modeller og kan inneholde konflikter, feil og duplikater.

## Beslutning

Import kjøres som jobb med parsing, normalisering, validering, matching, forslag, radvis review og eksplisitt commit.

## Konsekvenser

Import skal ikke behandles som en enkel loop over ordinære CRUD-endepunkter. Beslutninger og commit-resultater skal være sporbare.