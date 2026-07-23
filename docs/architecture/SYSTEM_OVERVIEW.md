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