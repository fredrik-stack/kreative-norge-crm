# ADR-001: Tenant-arkitektur

## Status

Godkjent og implementert.

## Bakgrunn

Eksterne organisasjoner skal kunne ha egne rom uten innsyn på tvers.

## Beslutning

Kjernedata scopes til `Tenant`, og brukerens tilgang styres gjennom `TenantMembership`.

## Konsekvenser

All import, eksport, CRUD og tilgangskontroll må håndheve tenant-isolasjon.