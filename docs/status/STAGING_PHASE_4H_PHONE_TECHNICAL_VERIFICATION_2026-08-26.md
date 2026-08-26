# Staging fase 4H – samlet teknisk telefonverifikasjon 2026-08-26

**Status:** `PHASE 4 TECHNICALLY VERIFIED / READY_FOR_OWNER_SMOKE`

**Dato:** 2026-08-26

## Konklusjon

Hele ADR-010 fase 4A–4H er implementert, reviewet, merget og teknisk
verifisert i shared staging. Fase 4 er klar for prosjekteiers korte manuelle
smoke, men markeres ikke eiergodkjent eller produksjonsklar av denne rapporten.
Fase 5 og produksjon er ikke startet.

Sluttgaten beviste additivt schema uten skjulte defaults eller global
telefonunikhet, synlig Editor-region, samme typed kontrakt i Import,
tenant-scopet matching uten automerge, kontrollert og reverserbar 4G-backfill,
uendret rå-/publiseringsstate, PUBLIC uten canonical lekkasje samt grønn
backup/restore-, image- og safety-state.

## Leveransekjede, review og CI

| Gate | PR | Frozen head | Merge | PR-/main-CI |
| --- | ---: | --- | --- | --- |
| 4D additiv datamodell | #61 | `076bb02cc9afd65e296092476c79a761b15edb7d` | `0198269892b7e59143393b4ed3f104098e81a24e` | `32899964521` / `32900414742`, 6/6 |
| 4E Editor/internal write | #62 | `4d6dc5f46a37b7700cc78707e34a73a579c3fcbe` | `8315c404f719f823f59eb1f104f7e5e921f9c02d` | `32903904895` / `32904398507`, 6/6 |
| 4F Import contract | #63 | `9607febd724857e61f3e12a4beb929e52bf07bbb` | `9119b03e263bc7c848b3b2e32db9b7a41d9e4964` | `32908487848` / `32908853104`, 6/6 |
| 4G controlled backfill | #64 | `f329a50dab82f99ec8657be2e25d3adde5431943` | `d9b0589acee433034acb2706f204383361049a41` | `32911465738` / `32911830730`, 6/6 |

Alle fire frozen-head-reviews endte med `0 BLOCKER`, `0 HIGH`, `0 MEDIUM` og
`0 LOW`. 4H ble kjørt mot eksakt 4G-merge `d9b0589` før denne separate
evidensleveransen.

## 4D–4F staginggrunnlag

- 4D anvendte additiv migrasjon `0032_phone_identity_fields` etter backup og
  isolert restore. Nye felt var `NULL`, rå- og publiseringsfingerprints var
  uendret, og isolert reverse/forward var grønn.
- 4E verifiserte norsk nasjonal skrivemåte, `+47`, `+46`, svensk nasjonal
  skrivemåte med eksplisitt `SE`, regionmangel, invalid og clearing gjennom API
  og synlig Editor. Syntetiske data ble slettet eksakt.
- 4F verifiserte jobbens immutable region-snapshot, eksplisitt `NO`, `null`,
  `VALID`, `INVALID`, `NEEDS_REGION`, blank `KEEP`, commit-skip, uendret
  publisering og full fil-/databaseopprydding.

## 4G apply og rollbackbevis

Før live apply ble staging verifisert med tre eksakte tenants, 128
organisasjoner, 157 personer, 56 PHONE-kontakter og null canonical
telefonidentitet. Fersk backup
`kreative-norge-staging-20260825T234721Z`, full repository-/arkivverifikasjon
og isolert restore var grønne.

To byteidentiske dry-runs fant 61 deterministiske endringer:

| Modell/felt | Endringer |
| --- | ---: |
| tenantregion `NO` | 3 |
| Organization canonical identitet | 2 |
| PHONE PersonContact canonical identitet | 56 |

En isolert kopi av den ekte stagingbackupen gjennomførte
`apply 61 → dry-run 0 → rollback dry-run 61 → rollback apply 61` og endte
byteidentisk med utgangspunktet. Live batch
`phase4g-staging-20260825T235228Z` skrev deretter 61 endringer. Det restriktive
root-eide `0600`-manifestet ligger utenfor Git, inneholder ingen råtelefon eller
ny canonical payload og ble validert uten at live rollback ble anvendt.

Etter apply ga både umiddelbar og repetert dry-run `changes_total=0` med
identisk output. Fem syntaktisk uvanlige legacypar ble klassifisert `VALID` av
den samme 4C-adapteren under eksplisitt `NO`; ingen verdi ble tvunget forbi
adapteren. Den historiske raden med primærkontakt uten direkte personfelt ble
bevart, mens mismatch, cross-tenant og flere primærkontakter fortsatt er null.

## 4H Editor-, API- og Import-gate

Den interaktive Codex-browseren var ikke tilgjengelig i økten. Den synlige
stagingreisen ble derfor kjørt i Chromium gjennom prosjektets Playwright-runner
mot den offentlige stagingorigin med en midlertidig tenant-1-redigerer.

Editor-/API-evidensen omfattet:

- tenantdefault `NO` synlig i regionvelgeren
- norsk nasjonal råverdi, `+47`, `+46` og svensk nasjonal råverdi med `SE`
- uendret rå presentasjonsverdi i Editor/API-respons
- canonical identitet og faktisk brukt region kontrollert separat i databasen
- invalid blokkert synlig i klienten og extension blokkert av backend med
  kontrollert norsk feltfeil
- clearing av råverdi, canonical og region uten publiseringsendring
- fem gyldige testaktører og én midlertidig bruker slettet eksakt; avviste
  forsøk opprettet ingen rader

Den transaksjonelle API-/Import-gaten brukte åtte små syntetiske rader og
tre opplastede CSV-filer. Den verifiserte internasjonal `+`, nasjonal verdi via
jobbens tenant-snapshot, eksplisitt annen region, `NEEDS_REGION` med `null`,
`INVALID`, blank `KEEP`, identisk preview-retry og tenant-scopet
`NAME_AND_PHONE`. Telefon alene og tvetydighet ga aldri automerge.

Alle tre filer ble slettet eksakt, og databasearbeidet ble rullet tilbake i
samme transaksjon. Seks negative cross-tenant-kontroller dekket Organization,
PersonContact og ImportJob både gjennom feil tenant-path og manglende
membership.

## Schema-, data- og personverngate

Modell- og PostgreSQL-inspeksjon bekreftet at alle fem additive felt er
nullable uten modell- eller database-default. Ingen canonical telefonconstraint
gir global unikhet mellom personer eller organisasjoner.

Sluttstate og samme state på post-4H-restorekopien:

| Fingerprint | Rader | SHA-256 |
| --- | ---: | --- |
| rå telefonstate | 341 | `ff7c51a79d5177e0dc480b5aa0cec0264ac4a5cf6eef78aa31a8e2a6d54a51f9` |
| publiseringsstate | 526 | `fc26758aa9e46683383e4f49ed0a7ca583c752adee691196f4650ac9686649a7` |
| additiv telefonidentitet | 187 | `97c6ae05b4a1c5d74ddfc7fa45a44cf7c6882e2882bb515cb8337fdc597a25a9` |

Tre tenants har eksplisitt `NO`. Staging har 128 organisasjoner, 157
personer og 56 PHONE-kontakter; canonical identitet finnes på 2 Organization-
og 56 PHONE-kontaktrader. Backfill-dry-run er `0`, eksisterende canonical
identitet er konsistent, og rå- og publiseringsfingerprints er identiske med
pre-apply-state. Ingen rå telefonverdi er lagret i denne rapporten.

## PUBLIC, image og safety

PUBLIC følger fortsatt bare eksisterende publiseringsflagg og returnerer rå
presentasjonsverdi. 4H testet både skjult og publisert Organization-telefon,
publisert personkontakt i API og HTML/`tel:` samt fravær av canonical felt i
responsene.

- publiserte aktører: 122
- projection: `1 asset + 121 system_fallback`
- SQL-spørringer: 5
- safety-authorize: 3
- safety unavailable/scope mismatch: 0/0
- safety-ledger: `READY`, cursor/event/read/anchor 13
- deliveryfiler: 9
- deliverymanifest:
  `ac91c567897bee1a79bf6146811c98ea550f3c2776c42cd52376aa7be2b475dc`

## Lokal sluttmatrise

- backend: 560/560 tester grønne
- frontend: 31/31 tester grønne
- produksjonsfrontend-build: grønn
- Django systemcheck: grønn
- migrasjonsdrift: `No changes detected`
- fase 4H Playwright mot staging: grønn

## Post-4H backup og restore

Post-4H-backup `kreative-norge-staging-20260826T061135Z` ble opprettet med
service-resultat `success`. Repository-ID ble verifisert, 16 relevante arkiver
var synlige, full repository- og archive-data-verifikasjon var grønn, og
standard isolert restore-smoke fullførte.

En separat isolert restorekopi av samme arkiv verifiserte:

- anvendt migrasjon `0032`
- aggregat `3 tenants | 3 NO | 128 Organization | 157 Person | 56 PHONE |
  2 Organization canonical | 56 Contact canonical | 0032 applied`
- backfill-dry-run `0` og eksakt samme tre fingerprints som live
- PUBLIC projection `122 = 1 + 121`, fem queries og null safety-/scopefeil
- nyere host-eid safety-ledger fortsatt `READY` på cursor 13

Restorecontainer, Docker-nettverk og midlertidig arbeidsområde ble fjernet
automatisk. Standard backupverifikasjon kontrollerte også archive-data og
representativt mediabyte; den separate restorekopien brukte media read-only.

## Runtime og ekstern tilgjengelighet

Stagingrepoet avsluttet rent på `d9b0589`. API-, database- og webcontainerne
var `running` med restartteller `0`. API-imaget var `48101084…`, database
`49767d69…` og web `1c285363…`; database og web ble ikke rekreert av 4G.

Korrekt lokal origin med `X-Forwarded-Proto: https` ga `200` for root,
session og PUBLIC. Offentlig Cloudflare-rute ga også `200` for alle tre,
`cf-cache-status: DYNAMIC` og ingen browserchallenge. Playwright-reisen brukte
samme offentlige origin og var grønn.

## Stoppunkt og eier-smoke

**Resultat: `PHASE 4 TECHNICALLY VERIFIED / READY_FOR_OWNER_SMOKE`.**

Prosjekteiers gjenstående smoke er en kort manuell bekreftelse av forståelig
regionvalg, rå telefonvisning og kontrollerte feiltekster i Editor. Teknisk
state skal ikke omtales som eiergodkjent før dette er gjort. Fase 5,
produksjonssetting, extensions, automatisk personmerge, `OrganizationContact`
og fysisk fjerning av `Person.phone` er fortsatt utenfor denne leveransen.
