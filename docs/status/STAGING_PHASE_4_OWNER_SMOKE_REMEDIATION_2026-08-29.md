# Staging – fase 4 owner-smoke-remediation 2026-08-29

**Status:** `PHASE 4 TECHNICALLY VERIFIED / READY_FOR_OWNER_SMOKE`

**Deployet merge:** `589b86fc1e1a41f01ef1444bb679b49c9d0bc13d`

## Konklusjon

De tre konkrete funnene fra prosjekteiers første owner-smoke er rettet,
reviewet, merget og teknisk reverifisert i shared staging uten schemaendring,
datamigrasjon, backfill eller endret publiseringssemantikk. Fase 4 markeres
ikke `CLOSED / VERIFIED`: prosjekteiers korte andre owner-smoke gjenstår.

Rettelsen bevarer rå telefon som synlig verdi og bruker lagret canonical E.164
som ringemål, viser Organization-telefon i intern Editor uavhengig av
`publish_phone` og forklarer den effektive kombinasjonen av
`OrganizationPerson.publish_person` og `PersonContact.is_public` uten å koble
eller omskrive flaggene.

## Rotårsak og retting

1. React brukte rå presentasjonsverdi direkte i `tel:`. Backend leverer nå et
   avgrenset read-only `phone_dial_uri` fra allerede lagret canonical identitet
   for Organization, primær PHONE-kontakt på Person og PHONE-PersonContact.
   Manglende canonical identitet gir rå, ikke-klikkbar tekst.
2. Interne aktørkort/modaler viste ikke `Organization.phone`. De viser nå rå
   telefon og canonical ringemål både når `publish_phone=True` og `False`, med
   separat `Offentlig`/`Kun intern`-merking.
3. Editor viste de to eksisterende publiseringsflaggene hver for seg uten å
   forklare samspillet. Person-editoren bruker «Kan vises offentlig» med
   aktørgateforklaring, og aktør-editoren forklarer alle fire aktive
   kombinasjoner. Ingen ny relasjonsspesifikk modell er introdusert.

## PR, review og CI

- implementerings-PR: [#66](https://github.com/fredrik-stack/kreative-norge-crm/pull/66)
- frozen head: `c24ddfe1afcdca3a3b32a16cfb7b1aa5176056a5`
- frozen-head-review: `0 BLOCKER`, `0 HIGH`, `0 MEDIUM`, `0 LOW`
- PR-CI: run `33272622781`, 6/6 grønn
- merge: `589b86fc1e1a41f01ef1444bb679b49c9d0bc13d`
- main-CI: run `33272843804`, 6/6 grønn

Lokal sluttmatrise før PR:

- backend: 568/568
- frontend: 38/38
- Playwright: 17/17
- frontend-produksjonsbuild og API-/web-Dockerbuild: grønne
- Django systemcheck: grønn
- migrasjonsdrift: `No changes detected`
- `git diff --check`: grønn

## Deploy

Stagingrepoet var rent på `d9b0589` og ble fast-forwardet til eksakt grønn
merge. Bare API- og web-image ble bygget og rekreert. API-oppstarten
rapporterte `No migrations to apply`; ingen datamigrasjon eller backfill ble
kjørt.

Den dokumenterte Docker Compose 1.29.2-feilen `ContainerConfig` oppstod ved
begge recreates. Hver gang ble bare den identifiserte stoppede gamle
containeren fjernet før samme service ble opprettet fra ferdigbygd image.
Databasecontaineren ble ikke rekreert:

| Service | Image | Start | Restart |
| --- | --- | --- | ---: |
| API | `5ccb4e476a5a…` | 2026-08-29 20:18:11 UTC | 0 |
| web | `0c7ea45d8b5d…` | 2026-08-29 20:18:59 UTC | 0 |
| database | `49767d69e574…` | 2026-08-24 18:57:51 UTC, uendret | 0 |

Root, sessionendepunkt og PUBLIC svarte `200` over ekstern HTTPS. Stagingrepoet
avsluttet rent på eksakt merge.

## Telefon-, API- og publiseringsgate

Den innebygde interaktive nettleseren var ikke tilgjengelig. Det ble ikke
opprettet en ny stagingcredential som omgåelse. Den synlige Editor-reisen er
dekket av den grønne lokale og CI-kjørte Playwright-testen; stagingruntimeen ble
i tillegg verifisert med en isolert Django-transaksjon som alltid ble
rollbacket, samt bytekontroll av det faktisk leverte frontendbundlet.

Den transaksjonelle stagingreisen beviste:

- svensk rå `070 123 45 67` forble synlig, med `tel:+46701234567`
- norsk rå `22 12 34 56` forble synlig, med `tel:+4722123456`
- Organization-responsen inneholdt telefon/dialmål med `publish_phone=False`
- Person utledet dialmålet fra primær PHONE-PersonContact
- PHONE-PersonContact og nested kontaktchip fikk samme canonical dialmål
- endring av bare `publish_person` lot `PersonContact.is_public` være identisk
- PUBLIC HTML brukte rå tekst og canonical href
- public API-shape forble uendret uten `phone_dial_uri`

Publiseringsfingerprint før og etter var byteidentisk:

- rader: `526`
- SHA-256 før/etter:
  `da3953a7c420dc06a51d5a6a1d85cf3061ffd5313ee2f0616f2304ff78ee19bc`
- midlertidige tenants, brukere og øvrige testdata etter gaten: `0`

Frontendbundlet `index--wncUrUV.js` hadde samme SHA-256 lokalt, i kjørende
web-container og over offentlig staging-HTTPS:
`c78681fbdc7e98b28f835a6c5ac61d293a07b3fa9792940ac8acd71f2312770e`.
Bundlet inneholdt `phone_dial_uri`, `Kun intern`, «Kan vises offentlig» og den
eksakte forklaringen for offentlig person uten offentlige kontaktkanaler.

## PUBLIC, image og safety

Den skrivebeskyttede projectiongaten beholdt:

- publiserte aktører: `122`
- projection: `1 asset + 121 system_fallback`
- queries/authorize: `5/3`
- safety unavailable/scope mismatch: `0/0`

Safety-ledger-health var `READY` med event/read/anchor cursor `13`. PUBLIC API-
og HTML-testen endret ikke hvilke kontakter som er publisert; den verifiserte
bare rå visning og canonical ringemål for en allerede offentlig kontakt inne i
rollbacktransaksjonen.

## Stoppunkt og andre owner-smoke

Resultatet er fortsatt:

`PHASE 4 TECHNICALLY VERIFIED / READY_FOR_OWNER_SMOKE`

Fredriks andre owner-smoke:

1. Lagre et svensk nasjonalt nummer med region `SE`, kontroller rå visning og
   trykk på nummeret for å se at telefonen ringer `+46`.
2. Slå av offentlig aktørtelefon og kontroller at telefonen fortsatt vises på
   det interne aktørkortet og i modal som `Kun intern`.
3. Bruk én kontaktkanal med «Kan vises offentlig», og slå «Vis person
   offentlig» av og på på én aktørkobling.
4. Kontroller at forklaringen i både Person- og Aktør-editoren følger den
   effektive PUBLIC-statusen uten å endre kontaktkanalens flagg.
