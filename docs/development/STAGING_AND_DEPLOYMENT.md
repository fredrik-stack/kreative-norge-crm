# Staging and Deployment

**Status:** staging eksisterer, automatisk deploy planlagt

Dagens dokumenterte stagingoppsett bruker Caddy foran Docker Compose, PostgreSQL, Django/Gunicorn og nginx.

Caddy terminerer HTTPS for `staging.northernsound.no` og sender trafikk videre til `127.0.0.1:8080`. `web`-containeren binder derfor `127.0.0.1:8080:80`. Nginx i `web`-containeren serverer frontend og proxyer `/api/`, `/admin/` og `/public/` til Django. Nginx må videresende `X-Forwarded-Proto` fra Caddy, ellers vil Django tolke proxied HTTPS-kall som HTTP og svare med redirect til samme HTTPS-URL.

Public HTML-visning brukes foreløpig bare i staging.

## Verifisert frontendbaseline 2026-07-29

Den skrivebeskyttede fase 1-kontrollen sammenlignet en ren frontendbuild fra `main` med filene i kjørende web-container og filene levert over HTTPS.

- JavaScript- og CSS-bundle hadde samme filnavn, størrelse og SHA-256 i ren build, web-container og HTTPS-respons
- cache-busting returnerte samme innhold som ordinære forespørsler
- nginx lastet forventet stagingkonfigurasjon
- Caddy var aktiv og videresendte til den lokale web-tjenesten
- proxy- eller cachekjeden var derfor ikke årsak til de observerte UI-avvikene
- ingen containere, tjenester, cache, DNS, data eller deploy ble endret under kontrollen

Kjørende serverrepo var eldre enn GitHub `main`, men forskjellen bestod av dokumentasjon og arbeidsflytfiler; de kontrollerte runtimefilene og frontendbundlene matchet dagens applikasjonskode. Se [datert evidensrapport](../status/FRONTEND_BASELINE_2026-07-29.md).

## Telefonreparasjon etter en senere fase 2-deploy

Fase 2 skal ikke gjøre dataendringer automatisk ved deploy. Etter at fase 2-koden eventuelt er deployet, er den eksakte skrivebeskyttede stagingkommandoen:

```bash
docker-compose -f docker-compose.staging.yml exec -T api python manage.py repair_person_contacts --contact-type PHONE
```

Kommandoen er dry-run fordi `--apply` ikke er angitt. Kandidater og konflikter skal kontrolleres uten rå kontaktverdier før prosjekteier eventuelt godkjenner en separat backup- og apply-økt. `--tenant <id-eller-slug>` kan legges til når kjøringen skal avgrenses.

## Ønsket neste steg

Push til avtalt branch skal kunne utløse en sikker automatisk deploy til staging etter at obligatoriske tester er bestått.

Før dette etableres må vi beslutte:

- hvilken branch som deployer
- GitHub Actions eller annen mekanisme
- secrets og servertilgang
- migrasjonsflyt
- helse-/smoke-test
- rollback ved feil
