# ADR-001: Tenant-arkitektur

## Status

Godkjent og implementert.

**Målarkitekturpresisering 2026-08-31:**
[ADR-011](ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md)
er godkjent, men ikke implementert. Dagens kjernedata er fortsatt direkte
tenant-scopet etter ADR-001. I målarkitekturen erstatter ADR-011 tenant som
canonical eier av Organization og Person innen eksakt SharingDomain, mens
Tenant fortsatt er sikkerhetsscope for membership, assignments, private
overlays og operativ import/eksport. Deling utenfor eksakt SharingDomain er
fortsatt forbudt.

## Bakgrunn

Eksterne organisasjoner skal kunne ha egne rom uten innsyn på tvers.

## Beslutning

Kjernedata scopes til `Tenant`, og brukerens tilgang styres gjennom `TenantMembership`.

## Konsekvenser

All import, eksport, CRUD og tilgangskontroll må håndheve tenant-isolasjon.
