# Staging fase 4B – skrivebeskyttet telefonbaseline 2026-08-25

**Status:** `READY_FOR_4C`

**Dato:** 2026-08-25

## Konklusjon

Fase 4B kartla eksisterende telefon- og publiseringsdata i shared staging uten å endre database, runtime eller konfigurasjon. To separate inventorykjøringer i eksplisitte PostgreSQL-transaksjoner med `transaction_read_only=on` ga byteidentiske aggregater og identiske SHA-256-fingerprints. API-, database- og webcontainerne beholdt samme container-ID, image, starttid og restartteller `0` før og etter.

Stagingdataene bekrefter [ADR-010](../decisions/ADR-010-INTERNATIONAL_PHONE_IDENTITY_AND_NORMALIZATION.md): de fleste lagrede telefonverdiene mangler eksplisitt internasjonalt prefiks og kan ikke tolkes med en skjult Norge-default. De observerte format- og legacyavvikene kan håndteres gjennom planlagt typed normalisering, eksplisitt regionkontekst og konservativ review/backfill i 4C–4G. Ingen ny arkitekturbeslutning er nødvendig før 4C.

## Baseline og scope

- lokal og GitHub-`main` etter ADR-010-statussynk: `e2bddc9b2cade3baeeb2017d9dd3ce32eab1207a`
- PR #57 post-merge-CI: run `32887838281`, `success`
- stagingrepo og deployet applikasjonsbaseline: `438a4800ded325fdf1ba99acc3d03812fb9ef1e9`
- forskjellen fra stagingcommit til dagens `main` består bare av Markdown-dokumentasjon; ingen modell-, import- eller annen runtimekode er forskjellig
- PostgreSQL: `16.13`
- omfang: `Organization.phone`, `Person.phone`, `PersonContact(type=PHONE)` og `OrganizationPerson`-publiseringsstate for alle tre tenants
- deploy: `NOT APPLICABLE – NO RUNTIME CHANGE`

Staging kjørte fra fase 3F-mergen fordi fase 4A og status-PR #57 bare endret dokumentasjon. Inventoryen brukte dermed samme aktive telefonmodeller og importmellomregel som dagens `main`.

## Absolutt no-write-kontrakt og metode

Et midlertidig, ikke-committet Django-shellskript ble strømmet til den eksisterende API-containeren. Hver kjøring åpnet en ny `transaction.atomic()` og kjørte `SET TRANSACTION READ ONLY` som første databasesetning. `SHOW transaction_read_only` returnerte `on` i begge kjøringer før ORM-lesingene startet.

Skriptet:

- leste bare stabilt ID-sorterte feltsett
- kalte ingen `save`, `update`, `create`, `delete`, migrasjon, repair, backfill eller ekstern tjeneste
- installerte ingen dependency og brukte ikke `phonenumbers`
- produserte bare aggregerte tellinger og SHA-256-digests
- returnerte aldri rå telefonverdier, navn, e-post eller fullstendige rader

Tom telefon betyr i denne rapporten `NULL`, tom streng eller whitespace-only. Eksakt rå duplikat betyr byte-for-byte lik, ikke-tom lagret verdi innen angitt scope. Formatprofilene er syntaktisk inventory, ikke E.164-validering eller påstand om hvilket land en verdi tilhører.

## Aggregert inventory

### Organization

| Måling | Antall |
| --- | ---: |
| Organisasjoner totalt | 128 |
| Med ikke-tom `Organization.phone` | 2 |
| Uten telefon | 126 |
| Eksakte rå duplikatgrupper på tvers av organisasjoner | 0 |
| Rader berørt av slike duplikater | 0 |

Publiseringsbaseline:

| `is_published` | `publish_phone` | Organisasjoner | Med telefon |
| --- | --- | ---: | ---: |
| false | false | 6 | 0 |
| false | true | 0 | 0 |
| true | false | 119 | 0 |
| true | true | 3 | 2 |

Én publisert organisasjon har dermed `publish_phone=true` uten lagret telefon. Dette er en senere reviewgruppe, ikke en dataendring i 4B.

### Person legacyfelt

| Måling | Antall personer |
| --- | ---: |
| Personer totalt | 157 |
| Med ikke-tom `Person.phone` | 55 |
| Uten direkte telefon | 102 |
| Direkte telefon med primær PHONE-kontakt | 55 |
| Direkte telefon uten primær PHONE-kontakt | 0 |
| Direkte telefon med eksakt lik rå primærverdi | 55 |
| Direkte telefon med avvikende rå primærverdi | 0 |
| Uten direkte telefon, men med primær PHONE-kontakt | 1 |

Alle 55 ikke-tomme direktefeltene matchet både rått og etter bare boundary-trim mot en primær PHONE-kontakt. Den ene personen som bare har primær kontakt er en kontrollert legacyreviewgruppe; PUBLIC bruker fortsatt `PersonContact`, ikke direktefeltet, som autoritet.

### PersonContact PHONE

| Måling | Antall |
| --- | ---: |
| PHONE-kontakter totalt / ikke-tomme | 56 / 56 |
| Primære / ikke-primære | 56 / 0 |
| Offentlige / private | 8 / 48 |
| Primære offentlige / primære private | 8 / 48 |
| Personer med 0 / 1 / flere enn 1 PHONE-kontakter | 101 / 56 / 0 |
| Personer med flere enn én primær PHONE | 0 |
| Eksakte duplikatgrupper innen samme person | 0 |
| Eksakte rå verdier delt av flere personer | 0 grupper / 0 rader |
| `PersonContact.tenant` ↔ `Person.tenant`-avvik | 0 |

### Tenant-avgrenset oversikt

Tenantene identifiseres bare med interne numeriske ID-er; ingen navn eller kontaktdata er tatt inn i evidensen.

| Tenant-ID | Organisasjoner, med telefon | Personer, med direkte telefon | PHONE-kontakter, offentlige | OrganizationPerson-lenker |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 121, 2 | 147, 49 | 50, 4 | 163 |
| 2 | 3, 0 | 4, 0 | 0, 0 | 7 |
| 3 | 4, 0 | 6, 6 | 6, 4 | 6 |

Alle tenants hadde null kontakt-/person-tenantavvik og null OrganizationPerson-avvik mot både organisasjonens og personens tenant.

### OrganizationPerson og publiseringsstate

Det finnes 176 koblinger: 171 `ACTIVE/publish_person=true`, 3 `ACTIVE/publish_person=false` og 2 `INACTIVE/publish_person=false`. Ingen kobling hadde tenantavvik. Inventoryen endret ingen status eller publiseringsflagg.

## Syntaktiske formatprofiler

Kategoriene overlapper bevisst. `Andre tegn` betyr tegn utenfor sifre, whitespace, `+`, bindestrek og parentes. `Syntaktisk uvanlig` betyr andre tegn, feilplassert/flere plusstegn, `+00` eller antall sifre utenfor 7–15; dette er kun en reviewindikator.

| Kategori | Organization | Person legacy | PersonContact PHONE |
| --- | ---: | ---: | ---: |
| Ikke-tomme lagringsrader | 2 | 55 | 56 |
| Starter med `+` | 0 | 1 | 1 |
| Starter med `00` | 0 | 0 | 0 |
| Uten eksplisitt internasjonalt prefiks | 2 | 54 | 55 |
| Bare sifre | 2 | 13 | 13 |
| Inneholder whitespace | 0 | 42 | 43 |
| Inneholder bindestrek | 0 | 0 | 0 |
| Inneholder parentes | 0 | 0 | 0 |
| Inneholder andre tegn | 0 | 5 | 5 |
| Bokstav-/extension-lignende | 0 | 0 | 0 |
| Syntaktisk uvanlig | 0 | 5 | 5 |

Sifferlengde:

| Antall sifre | Organization | Person legacy | PersonContact PHONE |
| --- | ---: | ---: | ---: |
| 8 | 2 | 54 | 55 |
| 9–11 | 0 | 1 | 1 |
| Alle andre buckets | 0 | 0 | 0 |

På tvers av de tre lagringsstedene finnes 113 ikke-tomme og 228 tomme lagringsrader. De 113 radene er ikke 113 unike telefonidentiteter: direkte personfelt og primærkontakt lagrer samme råverdi for 55 personer. Kombinert profil har 111 rader uten internasjonalt prefiks, 2 med `+`, 0 med `00`, 28 med bare sifre, 85 med whitespace og 10 syntaktisk uvanlige rader.

## Aggregerte review- og konfliktgrupper

- manglende regionkontekst: 2 organisasjonsrader, 54 direkte personrader og 55 PersonContact-rader
- klart internasjonalt skrevet med `+`: 0 organisasjonsrader, 1 direkte personrad og 1 tilsvarende PersonContact-rad
- `00`-prefiks: 0 i alle tre kilder
- extension-lignende innhold: 0 i alle tre kilder
- syntaktisk uvanlig: 0 organisasjonsrader, 5 direkte personrader og deres 5 eksakt samsvarende primærkontakter
- delte eksakte rå telefonverdier mellom personer: 0 grupper
- direktefelt ↔ primærkontakt-avvik: 0 personer
- direktefelt med manglende primærkontakt: 0 personer
- primærkontakt uten direkte legacyverdi: 1 person
- publisert organisasjon med `publish_phone=true`, men uten telefon: 1 organisasjon

Disse gruppene overlapper og skal ikke summeres til et antall unike telefonnumre. Spesielt krever de nasjonalt skrevne verdiene eksplisitt regionkontekst i 4C/4G; inventoryen antar ikke Norge.

## Dagens mellomregel og skjult normalisering

Kodekontroll mot `main` og den runtimeekvivalente stagingkoden fant ingen E.164-parser, `phonenumbers`-/libphonenumber-dependency eller annen skjult telefonkanonisering:

- importens `normalize_phone()` komprimerer bare whitespace
- primary-contact-synkronisering trimmer ytterkantene og sammenligner ellers lagret tekst eksakt
- `repair_person_contacts` trimmer PHONE, men normaliserer ikke formatet
- importmatcheren bruker navn sammen med eksakt `Person.phone` eller eksakt `PersonContact.value`
- AI-suggestion-sanitizeren er et minimumslengdefilter for forslag, ikke lagret kanonisk identitet eller matcher

Dette samsvarer med mellomtilstanden i ADR-010. Ingen av disse mekanismene ble kjørt skrivende i 4B.

## Deterministisk no-write-bevis

Fingerprints er SHA-256 over stabile, ID-sorterte JSON-representasjoner. Rå telefontekst inngikk bare i hash-input inne på staging og forlot aldri inventoryprosessen.

| Datasett og felt | Rader | Kjøring 1 = kjøring 2 |
| --- | ---: | --- |
| `Organization(id, tenant_id, phone, is_published, publish_phone)` | 128 | `c2972b1b9aa3d359b85cce53c9311c47d0a841b25fd2e4b25b462be50c46553a` |
| `Person(id, tenant_id, phone)` | 157 | `6038f9cf8b2e66cd6042d0cedb40e4af958b4610ef0d20c355b01b0d47288740` |
| PHONE `PersonContact(id, tenant_id, person_id, type, value, is_primary, is_public)` | 56 | `54ece03a07020f0e9b37e282d5b0e4c7491dc9c28e52c36dfa92b3d8827d4404` |
| `OrganizationPerson(id, tenant_id, organization_id, person_id, status, publish_person)` | 176 | `377f25b527c35f4d2e3894943d36c9fa4e78458e19ef0095aa0ba75b5f7ca53a` |

Hele aggregerte JSON-resultatet var byteidentisk mellom kjøringene. Stagingrepoet forble rent på samme commit. Container-ID-er, image-ID-er, starttider og restarttellere var identiske før og etter; alle tre restarttellere var `0`. Det ble ikke kjørt deploy, restart, recreate, migrasjon, featureflagendring eller runtimeinstallasjon.

## Hva fase 4B ikke gjorde

4B installerte ikke `phonenumbers`, implementerte ikke adapter eller validering, la ikke til felt/modeller/migrasjoner, endret ikke Editor, import, PUBLIC eller API, utførte ikke backfill eller repair og skrev ingen telefon- eller publiseringsdata. Ingen rå telefonnumre, navn, e-post, eksport, dump eller screenshot er lagret i Git, PR eller rapport.

## Risiko og eksplisitt neste gate

De nasjonalt skrevne verdiene dominerer datasettet, og fem samsvarende person-/kontaktrader har uvanlig syntaks. Dette gjør eksplisitt og sporbar regionkontekst samt typed `NEEDS_REGION`/`INVALID`-håndtering nødvendig; det begrunner ikke en skjult Norge-default. Delt telefon mellom personer og duplikater innen samme person forekommer ikke i dagens stagingbaseline, men ADR-010s forbud mot global telefonunikhet består.

**Resultat: `READY_FOR_4C`.** Neste oppgave er å planlegge fase 4C fra denne faktiske evidensen. 4C skal fortsatt være en separat leveranse og inngår ikke i 4B.
