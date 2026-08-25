# Staging fase 4C – telefonnormaliseringsdomene 2026-08-25

**Status:** `READY_FOR_4D`

**Dato:** 2026-08-25

## Konklusjon

Fase 4C er implementert, reviewet, merget, deployet API-only og verifisert i
shared staging. `phonenumbers==9.0.37` kjører bak én ren intern adapter med
typed `VALID`, `INVALID` og `NEEDS_REGION`, stabile ikke-sensitive årsakskoder
og E.164 bare ved `VALID`.

To identiske real-data-kjøringer brukte `region=None` i separate
PostgreSQL-transaksjoner med `transaction_read_only=on`. De returnerte bare aggregerte
typed utfall. Fingerprints for Organization, Person, PHONE PersonContact og
OrganizationPerson var identiske før deploy, etter deploy og etter den andre
kjøringen. Ingen rå telefonverdier, navn eller e-post forlot prosessen.

Resultatet er `READY_FOR_4D`. Fase 4D er ikke startet.

## Implementasjon, review og CI

- implementeringsbranch: `feature/phase4c-phone-normalization-domain`
- implementerings-PR: #59
- frozen/reviewet head: `3fe7160a610295404943bad8e7695893afae8c1c`
- separat frozen-head-review: `0 BLOCKER`, `0 HIGH`, `0 MEDIUM`, `0 LOW`
- PR-CI: run `32891948790`, 6/6 grønn på eksakt head
- mergecommit: `b9cc84e598179cc90bf6587f986796036ad25a9c`
- main-CI: run `32892503493`, 6/6 grønn på eksakt merge
- dependency: `phonenumbers==9.0.37`

Lokal verifikasjon før PR:

- 22 målrettede syntetiske 4C-tester grønne
- full backend: 512 tester grønne
- `manage.py check` grønn
- `makemigrations --check --dry-run`: `No changes detected`
- produksjons-API-image bygget grønt
- dependency `9.0.37`, modulimport og kjøring verifisert i container
- `git diff --check` grønn
- ingen frontendfil var endret

## Deploy

Staging startet rent på applikasjonscommit
`438a4800ded325fdf1ba99acc3d03812fb9ef1e9`. Serverrepoet ble fast-forwardet
rent til eksakt merge `b9cc84e598179cc90bf6587f986796036ad25a9c`.

Bare API-imaget ble bygget. Før deploy:

| Tjeneste | Container-ID | Image | Restart |
| --- | --- | --- | ---: |
| API | `d1ab9356370fb4cb5ad435a6a9f55c72c5637045c0f24d2f64cbef43dd9f894f` | `1f7e4f95618331babed0f994051de33b3416c108dc39ddb1866cd8001a11cbfc` | 0 |
| database | `46606f0b5b9794bb7d4698026113d3d018c03dafb06da9a9332a6b44aefa68eb` | `49767d69e57428bc8229d8427521605e90b230c908d19542644d92b77dc1984d` | 0 |
| web | `73459717b736dd9f99ab2b6c5f8ed0faaebce32a5492d59ecd09b868e15703e1` | `29bebd1faddb0bab8af70c2b37165ffc0081460f4b0533612f7f6fed0fba4232` | 0 |

Compose 1.29.2 traff den kjente `ContainerConfig`-feilen ved første in-place
API-recreate. Bygget var ferdig og feilen var avgrenset til API. Den
dokumenterte sekvensen `stop → rm api → up --no-deps api` gjenopprettet bare
API-containeren. Database, web, volumer og data ble ikke rekreert.

Etter deploy:

| Tjeneste | Container-ID | Image | Restart |
| --- | --- | --- | ---: |
| API | `2a866b79a577f6d8b380606bc731edcc27f50e318c23ac077621fa7eef90fa0e` | `d50d3a3e1767740895bc1ff3a45ed6ef89dc81253c9405cdd2f81366ad927c2b` | 0 |
| database | `46606f0b5b9794bb7d4698026113d3d018c03dafb06da9a9332a6b44aefa68eb` | `49767d69e57428bc8229d8427521605e90b230c908d19542644d92b77dc1984d` | 0 |
| web | `73459717b736dd9f99ab2b6c5f8ed0faaebce32a5492d59ecd09b868e15703e1` | `29bebd1faddb0bab8af70c2b37165ffc0081460f4b0533612f7f6fed0fba4232` | 0 |

Repoet var rent på eksakt merge ved sluttkontrollen. Host- og containerfilen
`crm/services/phone_normalization.py` hadde samme SHA-256
`93febc0b7803e3a71cbc9c2d4db9ca850b9ae13bc4d5e8d15bd6b4b2230cec15`.
Containeren rapporterte dependency `9.0.37`.

Ingen ny migrasjon, schemaendring eller datamigrering inngikk. Compose-entrypointets
ordinære migrate-sjekk hadde ingen ny migrasjon å anvende;
`0031_import_image_decision_contract` forble nyeste anvendte CRM-migrasjon.
Det ble ikke tatt en rituell backup fordi leveransen ikke hadde schema- eller
datawrites.

## Syntetisk runtime-smoke

Den nye API-containeren kjørte adapteren direkte med syntetiske verdier:

| Gate | Resultat |
| --- | --- |
| dependency | `9.0.37` |
| nasjonalt nummer med eksplisitt `NO` | `VALID`, E.164 som forventet |
| nasjonalt nummer uten region | `NEEDS_REGION / REGION_REQUIRED`, ingen E.164 |
| uparsbar verdi med `NO` | `INVALID / PARSE_ERROR`, ingen E.164 |
| samme `+`-nummer uten region og med `SE` | identisk resultat |
| extension | `INVALID / EXTENSION_NOT_SUPPORTED` |
| E.164-idempotens | identisk kanonisk resultat |

Samlet smoke rapporterte `all_expected=true`.

## Faktiske 4B-data med `region=None`

Begge postdeploykjøringene åpnet en ny `transaction.atomic()`, satte
`SET TRANSACTION READ ONLY` som første databasesetning og bekreftet
`transaction_read_only=on` før ORM-lesing. Adapteren fikk aldri tenant- eller
landgjetning; alle faktiske verdier ble kalt med `region=None`.

| Kilde | Ikke-tomme rader | Typed utfall |
| --- | ---: | --- |
| `Organization.phone` | 2 | 2 `NEEDS_REGION / REGION_REQUIRED` |
| `Person.phone` | 55 | 54 `NEEDS_REGION / REGION_REQUIRED`, 1 `VALID` |
| PHONE `PersonContact.value` | 56 | 55 `NEEDS_REGION / REGION_REQUIRED`, 1 `VALID` |

De to `VALID`-radene er den samme internasjonalt skrevne verdien i direkte
personfelt og primærkontakt, slik 4B allerede dokumenterte. Resultatet viser at
nasjonalt skrevne verdier ikke skjules av en norsk default, og det gjør ingen
påstand om hvilket land de tilhører. Ingen `INVALID` oppstod ved `region=None`;
de nasjonale verdiene ble korrekt sendt til region-review.

## No-write- og fingerprintbevis

Fingerprintene er SHA-256 over stabile, ID-sorterte canonical JSON-rader.
4C-skriptet bruker sin egen eksplisitte canonical serializer; checksumverdiene er
derfor en før/etter-gate innen 4C og skal ikke sammenlignes byte-for-byte med
4B-rapportens separat produserte hashes.

| Datasett | Rader | Før = etter = repetert etter |
| --- | ---: | --- |
| `Organization(id, tenant_id, phone, is_published, publish_phone)` | 128 | `f5fe2a4b0f7d896c83cff1b4712729af50343753c02999554cf9c10546da487f` |
| `Person(id, tenant_id, phone)` | 157 | `ea31c1b6101b837956c7cc08a5c426dceae0397291cde196bfaeeaf77176c73e` |
| PHONE `PersonContact(id, tenant_id, person_id, type, value, is_primary, is_public)` | 56 | `ff068db3aa40c4efa2feb76848c36118715ba8c3d88a8a05758768cbff233daa` |
| `OrganizationPerson(id, tenant_id, organization_id, person_id, status, publish_person)` | 176 | `3c7a244e72135b5f9231f8d8651a0274b1701f2aff48ced57c97516050a55c2d` |

Database- og webcontainerens identitet, image, starttid og restartteller var
uendret gjennom hele deployen. Alle slutt-restarttellere var `0`. Adapteren
har ingen write-path, og ingen `save`, `update`, `create`, `delete`, repair,
backfill eller publiseringsendring ble kalt.

## Django, API/PUBLIC, image og safety

- Django systemcheck: grønn
- intern PUBLIC-katalog: `122` publiserte, `122` kortlenker, `0` brutte
- lokal staging-origin: public API `200`, PUBLIC HTML `200`
- full image projection: `122 = 1 asset + 121 system_fallback`
- projection: 5 queries, 3 safety-authorizations, 0 safety-unavailable og 0
  scope mismatch
- safety-ledger: `READY`, ledger-ID uendret, cursor/event/read/anchor `13`
- delivery: 9 filer, uendret manifest
  `ac91c567897bee1a79bf6146811c98ea550f3c2776c42cd52376aa7be2b475dc`

Ekstern server-side curl mot både API og PUBLIC traff Cloudflares eksisterende
browserchallenge og ga `403`. Dette er samme kjente edge-adferd som tidligere
stagingarbeid har dokumentert. Lokal origin, Django test client og hele
PUBLIC-lenkesettet var grønne, så det er ikke en 4C-applikasjonsregresjon.

## Avgrensning, rollback og stoppunkt

Fase 4C endret ikke modeller, schema, migrasjoner, telefondata,
publiseringsflagg, API-kontrakt, Editor, Import, matching, repair, backfill,
feature flags eller bildearkitektur. Normalisering er fortsatt en ubrukt intern
domenegrense frem til senere, separat godkjente callers.

Rollback før 4D er API-only rebuild/recreate av forrige applikasjonscommit
eller revert av adapter, tester og dependency. Ingen data- eller
migrasjonsrollback er nødvendig.

**Resultat: `READY_FOR_4D`.** Neste oppgave er å planlegge fase 4D som en egen
ADR-010-gate. Denne leveransen stopper før 4D.
