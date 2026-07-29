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

## Tenant-avgrenset telefonreparasjon 2026-07-30

Fase 2 gjør ikke dataendringer automatisk ved deploy. Etter at fase 2-applikasjonsversjonen var verifisert på staging, ble følgende tenant-avgrensede dry-run brukt:

```bash
docker-compose -f docker-compose.staging.yml exec -T api python manage.py repair_person_contacts --contact-type PHONE --tenant musikkontoretnord
```

Kommandoen er dry-run fordi `--apply` ikke er angitt. Den undersøkte `49` personer og rapporterte kandidat-ID `1`, `2`, `132` og `150` uten konflikter eller kontaktverdier. Etter streng kontroll av tenant, direkte telefon, eksisterende kontaktsett og normaliserte duplikater ble backupfilen `staging-pre-phone-repair-20260729T222953Z.sql` opprettet og beholdt på stagingserveren. Den var `5 644 648` byte og hadde SHA-256 `e0cb54f1686f2b48c98ebd8b9a0ca3a9b5f1c52184d9b3b1a9258ec1012c5518`.

Prosjekteiers eksplisitt godkjente `--apply`-kjøring opprettet kontakt-ID `233`–`236` som private primære `PHONE`-kontakter for de fire kandidatene og rapporterte `changes_applied=4`. Umiddelbar dry-run etterpå rapporterte null kandidater, null konflikter og `changes_applied=0`. Felt- og fingeravtrykkskontroll bekreftet at eksisterende `PHONE`, samtlige `EMAIL`, direkte persontelefoner og publiseringsflagg var uendret. Editor-API og PUBLIC-smoke bekreftet henholdsvis intern tilgang og fravær av offentlig telefon-eksponering.

Serveren bruker fortsatt eldre Docker Compose `1.29.2`. Denne økten oppgraderte ikke Compose og kjørte ingen restart, recreate eller deploy. Ved fremtidig drift skal unødvendig recreate unngås; dersom den kjente `ContainerConfig`-feilen oppstår, skal kjøringen stoppes og håndteres som kontrollert feilretting med ny helsekontroll, ikke som del av en datareparasjon.

## Ønsket neste steg

Push til avtalt branch skal kunne utløse en sikker automatisk deploy til staging etter at obligatoriske tester er bestått.

Før dette etableres må vi beslutte:

- hvilken branch som deployer
- GitHub Actions eller annen mekanisme
- secrets og servertilgang
- migrasjonsflyt
- helse-/smoke-test
- rollback ved feil
