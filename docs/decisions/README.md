# Architecture Decision Records

ADR-er dokumenterer viktige valg som påvirker arkitektur, data eller arbeidsflyt.

## Beslutningsoversikt

| ADR | Beslutning | Kort status |
| --- | --- | --- |
| [ADR-001](ADR-001-TENANT_ARCHITECTURE.md) | Tenant-arkitektur | Godkjent og implementert |
| [ADR-002](ADR-002-PERSON_CONTACT_MODEL.md) | `PersonContact` som egen modell | Godkjent og implementert |
| [ADR-003](ADR-003-PUBLICATION_MODEL.md) | Separat intern og offentlig publiseringsmodell | Godkjent og implementert som grunnmodell |
| [ADR-004](ADR-004-IMPORT_ARCHITECTURE.md) | Import med preview og review før commit | Godkjent og implementert |
| [ADR-005](ADR-005-CONTACT_ARCHITECTURE.md) | Helhetlig kontaktarkitektur | Godkjent målarkitektur, delvis implementert |
| [ADR-006](ADR-006-SESSION_WORKFLOW.md) | Sesjonsflyt og varig prosjektminne | Godkjent og implementert |
| [ADR-007](ADR-007-IMAGE_ASSET_ARCHITECTURE.md) | Tenant-eid bildeassetarkitektur | Godkjent arkitekturgrunnlag; fase 3B og implementering gjenstår |

Detaljstatusen i hvert ADR er autoritativ dersom kortstatusen her ikke har alle nyanser.

## Minstekrav

Hver ADR skal inneholde:

- status
- bakgrunn
- beslutning
- begrunnelse
- konsekvenser

Små UI- og kodevalg skal ikke få egne ADR-er.
