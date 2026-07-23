# Staging and Deployment

**Status:** staging eksisterer, automatisk deploy planlagt

Dagens dokumenterte stagingoppsett bruker Docker Compose, PostgreSQL, Django/Gunicorn og nginx.

Public HTML-visning brukes foreløpig bare i staging.

## Ønsket neste steg

Push til avtalt branch skal kunne utløse en sikker automatisk deploy til staging etter at obligatoriske tester er bestått.

Før dette etableres må vi beslutte:

- hvilken branch som deployer
- GitHub Actions eller annen mekanisme
- secrets og servertilgang
- migrasjonsflyt
- helse-/smoke-test
- rollback ved feil