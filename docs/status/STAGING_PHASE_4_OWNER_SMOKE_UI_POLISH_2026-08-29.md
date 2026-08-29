# Staging – fase 4 siste owner-smoke UI-polish 2026-08-29

**Status:** `PHASE 4 TECHNICALLY VERIFIED / READY_FOR_OWNER_SMOKE`

**Deployet merge:** `c5027018d6549c4237ca6092210e5fbe11b05025`

## Konklusjon

De tre siste UI-polishpunktene fra prosjekteiers andre owner-smoke er
implementert, reviewet, merget og teknisk reverifisert i shared staging uten
schemaendring, datamigrasjon, backfill eller endret publiseringssemantikk.

Aktøroversiktens hovedkort viser ikke lenger Organization-telefon. Telefonen er
fortsatt tilgjengelig i oversiktsmodal, redigering og søk. Interne read-only
Organization-, Person- og PHONE-`PersonContact`-responser leverer et
backend-avledet landkodehint for utenlandske nasjonale formater, mens råtekst
og canonical `tel:`-mål forblir separate. Koblingsknappen til
personredigeringen heter nå `Rediger`.

Fase 4 markeres ikke `CLOSED / VERIFIED`; en siste kort eierkontroll av disse
tre punktene gjenstår.

## PR, review og CI

- implementerings-PR: [#68](https://github.com/fredrik-stack/kreative-norge-crm/pull/68)
- frozen head: `4c64698e9b69235906be632a9d989a336f8690b6`
- frozen-head-review: ingen kritiske, viktige eller forbedringsblokkerende funn
- PR-CI: run `33275943958`, 6/6 grønn
- merge: `c5027018d6549c4237ca6092210e5fbe11b05025`
- main-CI: run `33276159553`, 6/6 grønn

Lokal sluttmatrise før PR:

- backend: 570/570
- frontend: 41/41
- Playwright: 17/17
- frontend-produksjonsbuild og API-/web-Dockerbuild: grønne
- Django systemcheck: grønn
- migrasjonsdrift: `No changes detected`
- `git diff --check`: grønn

## Deploy

Stagingrepoet var rent på `d928cf1` og ble fast-forwardet til eksakt grønn
merge. Bare API- og web-image ble bygget og rekreert. API-oppstarten
rapporterte `No migrations to apply`; ingen datamigrasjon eller backfill ble
kjørt.

Den dokumenterte Docker Compose 1.29.2-feilen `ContainerConfig` oppstod ved
begge recreates. Hver gang ble bare den identifiserte stoppede gamle
servicecontaineren fjernet før samme tjeneste ble opprettet fra ferdigbygd
image. Databasecontaineren ble ikke rekreert:

| Service | Image | Start | Restart |
| --- | --- | --- | ---: |
| API | `afc343cf6e20…` | 2026-08-29 21:34:16 UTC | 0 |
| web | `25fbf4eab4a5…` | 2026-08-29 21:34:40 UTC | 0 |
| database | `49767d69e574…` | 2026-08-24 18:57:51 UTC, uendret | 0 |

Root, sessionendepunkt og PUBLIC svarte `200` over ekstern HTTPS. Django
systemcheck var grønn, og stagingrepoet avsluttet rent på eksakt merge.

## Telefon-, API- og publiseringsgate

Den innebygde nettleseren hadde ingen tilgjengelig browserbinding. Det ble
ikke opprettet en ny stagingcredential eller brukt en annen kontrollflate som
omgåelse. Den synlige brukerreisen er dekket av den grønne lokale og CI-kjørte
Playwright-testen. Den deployede stagingruntimeen ble i tillegg verifisert med
en Django-transaksjon som alltid ble rollbacket, og med bytekontroll av den
faktisk leverte frontendbundlen.

Den transaksjonelle stagingreisen beviste:

- Organization beholdt rå `08-505 103 00`, canonical
  `tel:+46850510300`, hint `46` og `publish_phone=False`
- Person beholdt rå `070 123 45 67`, canonical `tel:+46701234567` og
  hint `46` fra autoritativ primær PHONE-kontakt
- PHONE-`PersonContact` fikk samme canonical dialmål og hint uten å endre
  `is_public=False`
- generisk backendmetadata ga `45` for `DK` i en `NO`-tenant, mens `NO` i
  `NO` og manglende region ga `null`
- public kontaktserializer beholdt eksakt `{"type":"PHONE","value":"070 123 45 67"}`
- ingen testdata ble stående: tenant-/Organization-/Person-/kontakt-tellinger
  var identiske før og etter (`3/128/157/223`)
- publiseringsfingerprint var identisk før og etter med 527 rader og SHA-256
  `1eeda1019cfe926e0b814551f71d4ddda17321a0967316e5cab1052527a1144e`

## Frontendbundle

Frontendbundlet `index-B3xblJLU.js` hadde samme SHA-256 lokalt, i kjørende
web-container og over offentlig staging-HTTPS:

`73611527ac09d837c00e0d28ee8cf717dfa92b131331d1d2f430caecf0165874`

Bundlet inneholdt `phone_country_calling_code_hint` og
`phone-country-code-hint`, men ikke den gamle teksten
`Rediger kontaktkanaler`. Sammen med 17/17 grønne Playwright-tester dekker
dette at hovedkortet er uten telefon, modal-/personvisningene viser korrekt
hint og canonical href, og `Rediger` navigerer til personredigering.

## PUBLIC, image og safety

Den skrivebeskyttede projectiongaten beholdt:

- publiserte aktører: `122`
- projection: `1 asset + 121 system_fallback`
- queries/authorize: `5/3`
- safety unavailable/scope mismatch: `0/0`

Safety-ledger-health var `READY` med event/read/anchor cursor `13`. Public API
fikk ikke det nye interne hintfeltet, og rollbackgaten bekreftet uendret
publiseringsstate.

## Stoppunkt og siste owner-smoke

Resultatet er fortsatt:

`PHASE 4 TECHNICALLY VERIFIED / READY_FOR_OWNER_SMOKE`

Fredriks siste korte owner-smoke:

1. Kontroller at telefon ikke vises på aktørens hovedkort, men fortsatt finnes
   i modal, redigering og søk.
2. Kontroller at et svensk nasjonalt nummer viser `(+46)` uten at råteksten
   endres, at et norsk nummer ikke får `(+47)`, og at klikk bruker canonical
   `+`-nummer.
3. Kontroller at knappen ved en koblet person heter `Rediger` og åpner riktig
   personredigering.
