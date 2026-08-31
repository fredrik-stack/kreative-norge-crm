# System Overview

**Status:** implementert grunnsystem, dokumentasjon under oppbygging

Kreative Norge CRM består av:

- Django og Django REST Framework
- React og Vite for intern editor
- PostgreSQL
- Docker Compose
- Gunicorn og nginx i staging

Hovedområder:

1. intern tenant-basert editor
2. public API og HTML-visning
3. importmotor
4. eksportgrunnlag
5. autentisering og roller

Public HTML brukes foreløpig bare i staging. Automatisk staging-deploy ved push er ønsket, men ikke etablert som dokumentert standard.

[ADR-011](../decisions/ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md)
og [ADR-012](../decisions/ADR-012-PLACE_IDENTITY_GEOGRAPHIC_CLASSIFICATION_AND_ACTOR_ONLY_MAPS.md)
er godkjent målarkitektur, ikke runtime. De legger senere canonical sharing,
provider-nøytrale steder, rådgivende geografiske tenantforslag og actor-only
kart oppå grunnsystemet. Dagens direkte tenantmodell og fritekststeder gjelder
fortsatt; personer inngår aldri i kartscope.
