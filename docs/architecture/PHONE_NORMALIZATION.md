# Phone normalization domain

Telefonnormalisering er implementert som én ren intern domenegrense i
`crm/services/phone_normalization.py`. Den presiserer fase 4C i
[ADR-010](../decisions/ADR-010-INTERNATIONAL_PHONE_IDENTITY_AND_NORMALIZATION.md).
Fase 4D–4G har koblet samme grense til additiv persistens, API/Editor, Import,
matching og kontrollert legacybackfill; fase 4H har teknisk verifisert hele
kjeden i staging.

## Dependency og kontrakt

- `phonenumbers==9.0.37` er eksakt pinnet i `requirements.txt`.
- `normalize_phone(value, region=None)` returnerer alltid et immutable
  `PhoneNormalizationResult`.
- Resultatet inneholder bare `status`, `e164`, `reason_code` og valgfri
  `region_used`; rå- eller presentasjonsverdi returneres ikke.
- Status er eksakt `VALID`, `INVALID` eller `NEEDS_REGION`.
- `e164` finnes bare ved `VALID`; vellykket normalisering har ingen
  feilårsakskode.

Stabile årsakskoder er:

- `EMPTY_INPUT`
- `REGION_REQUIRED`
- `INVALID_REGION`
- `PARSE_ERROR`
- `NOT_POSSIBLE`
- `NOT_VALID`
- `EXTENSION_NOT_SUPPORTED`

## Regler

- tom input er `INVALID / EMPTY_INPUT`
- et nummer med `+` parses uten region; eventuell caller-region endrer ikke
  identiteten eller resultatet
- nasjonale numre uten eksplisitt region er
  `NEEDS_REGION / REGION_REQUIRED`; Norge brukes aldri som skjult standard
- eksplisitte regioner trimmes, normaliseres til store bokstaver og må finnes
  i libphonenumbers støttede regioner
- `00` behandles ikke med egen omskriving: uten region krever verdien region,
  og med region brukes bibliotekets IDD-regler
- extension avvises fordi extensions er utenfor fase 4
- bibliotekets `is_possible_number` og `is_valid_number` skiller henholdsvis
  `NOT_POSSIBLE` og `NOT_VALID`
- kanonisk output formateres med bibliotekets E.164-format og er idempotent

## Renhets- og personverngrense

Adapteren har ingen Django-importer, modeller, settings, database-,
nettverks- eller fil-I/O, logging, tenant-/entity-kobling eller sideeffekter. Det er derfor
callerlagets ansvar å levere eksplisitt og sporbar regionkontekst, bevare
presentasjonsverdien og håndtere review, lagring og publisering. Disse
calleransvarene er implementert i 4E–4G uten å gjøre adapteren uren.

Fase 4C la ikke til schema eller callers. Fase 4D la bare til den additive
persistensen. Fase 4E kobler ordinære interne Organization-, Person- og
PHONE-`PersonContact`-writes til adapteren. Fase 4F kobler Import og matching.
Fase 4G har en separat, dry-run-first operatørvei for kontrollert legacybackfill.

## Additiv persistens i fase 4D

Migrasjon `0032_phone_identity_fields` legger til nullable felt uten backfill
eller database-default:

- `Tenant.default_phone_region`
- `Organization.phone_normalized`
- `Organization.phone_normalization_region`
- `PersonContact.normalized_value`
- `PersonContact.normalization_region`

`Person.phone` får bevisst ikke et normalisert felt. Det er fortsatt et
legacy-kompatibilitetsfelt, mens personens kanoniske telefonidentitet skal
ligge på en PHONE-`PersonContact`.

Databasen håndhever canonical E.164-form, uppercase regionkodeform, at region
ikke kan stå uten normalisert verdi, og at telefonidentitetsfeltene ikke brukes
på e-postkontakter. `PersonContact.normalized_value` er unik bare innen samme
tenant, person og kontakttype. Samme nummer kan derfor brukes av ulike personer
og organisasjoner. Indekser støtter tenant-scopet oppslag på normalisert verdi.

Regionfeltene bruker også en modellvalidator mot libphonenumbers støttede
regioner. Tom region lagres som `NULL`; nye tenants får ingen skjult region.
Schema-reverse er testet så lenge alle nye felt er `NULL`, og blokkeres før
feltdropp dersom region eller kanonisk identitet senere er lagret.

## Intern write-kontrakt i fase 4E

Editor-API-et tar et eksplisitt `phone_region`-kontekstfelt sammen med en ny
eller endret rå telefon. `phone_region` returneres ikke som identitet; intern
respons kan lese `phone_region_used`, mens canonical E.164-feltet ikke
serialiseres. Tenantens nullable default returneres read-only slik at Editor
kan forhåndsvelge den synlig. Backend bruker aldri tenantdefaulten implisitt.

`crm.services.phone_writes.prepare_phone_write` er den felles write-grensen.
Den bevarer trimmet presentasjonsverdi, lagrer E.164 og bare regionen adapteren
faktisk brukte. Internasjonale `+`-numre ignorerer valgt region og lagrer
region som `NULL`. `NEEDS_REGION`, ugyldige numre og extensions blir
kontrollerte norske feltfeil; rå dependencyexceptions eksponeres ikke.

Den interne read-kontrakten bruker `phone_dial_uri` som avgrenset
presentasjonsfelt. `crm.services.phone_writes.phone_dial_uri` aksepterer bare
allerede lagret E.164-form og returnerer `tel:<E.164>`; den parser eller
normaliserer aldri råverdien. Organization leser fra `phone_normalized`, PHONE-
`PersonContact` fra `normalized_value`, og Person utleder målet fra primær
PHONE-kontakt. Manglende canonical identitet gir `null`, slik at Editor kan
vise råverdien uten klikkbar lenke. Dette endrer ingen write-, matching- eller
publiseringssemantikk.

Det separate read-only feltet `phone_country_calling_code_hint` er kun et
presentasjonshjelpemiddel for nasjonalt skrevne utenlandske numre. Backend
utleder landkoden fra lagret normaliseringsregion og libphonenumbers-metadata
når regionen er kjent og forskjellig fra tenantens defaultregion. Samme,
manglende eller ukjent region gir `null`; frontend har ingen hardkodet
region-/landkodetabell og undertrykker hintet når råverdien allerede starter
med `+`. Råverdi, canonical identitet, matching, writes og publisering endres
ikke, og public API får ikke feltet.

Personens direkte kompatibilitetsfelt synkroniseres fortsatt med primær
PHONE-`PersonContact`, og identiteten ligger bare på kontakten. Eksplisitt
tømming fjerner den primære telefonkontakten; sekundære kontakter og alle
publiseringsvalg berøres ikke. Serializerlaget normaliserer bare når selve
råtelefonen opprettes eller faktisk endres. Et fullstendig Editor-payload med
uendret legacytelefon kan derfor ikke gi incidental backfill.

## Importkontrakt i fase 4F

`ImportJob.config_json.phone_region` er et immutable snapshot: eksplisitt
jobbvalg, deretter tenantens nullable default, ellers `null`. Jobben viser dette
valget i Editor, og retry leser bare snapshotet. `+`-numre er fortsatt
regionuavhengige.

Importpayloaden skiller `VALID`, `INVALID`, `NEEDS_REGION` og den
importspesifikke blanksemantikken `KEEP`. Bare `VALID` kan skrive råverdi,
canonical E.164 og faktisk brukt region. `INVALID` og `NEEDS_REGION` sendes til
review og kan ikke automatisk overskrive eksisterende identitet. Blank input
kaller ikke adapteren og bevarer eksisterende telefon.

Canonical E.164 brukes som et sterkt, tenant-scopet `NAME_AND_PHONE`-signal,
men telefon alene identifiserer aldri en person. Flere treff blir tvetydig
review, aldri merge. Eksakt råverdi beholdes som kontrollert fallback frem til
fase 4G. Import-commit endrer ingen publiseringsflagg uten eksplisitte
publiseringskolonner, og AI kan ikke utlede region eller aktivere publisering.

## Verifikasjon og rollback

Syntetiske tester dekker norske, svenske og britiske numre, internasjonale
`+`-numre, regionuavhengighet, `00`, manglende/ugyldig region, parsefeil,
mulighet kontra gyldighet, extension, E.164-idempotens, personvern og
deterministiske resultater.

Fase 4C er verifisert API-only i shared staging med dependency `9.0.37`,
syntetisk smoke, to identiske real-data-kjøringer i read-only transaksjoner og
uendrede fingerprints for Organization, Person, PHONE PersonContact og
OrganizationPerson. Se [stagingevidensen](../status/STAGING_PHASE_4C_PHONE_NORMALIZATION_2026-08-25.md).

Fase 4D er verifisert i shared staging med fullverifisert backup/restore,
additiv migrasjon `0032`, alle nye felt fortsatt `NULL`, uendrede fingerprints
og isolert reverse/forward. Fase 4E er verifisert med API- og synlig
Editor-smoke for norsk, svensk, internasjonal, ugyldig og regionløs input,
etterfulgt av full opprydding og identiske katalogfingerprints.

Fase 4F har ingen migrasjon. Import-callers og UI kan rulles tilbake uten å
reversere gyldige canonical felt fra ordinære 4E-writes eller 4G-backfill.

## Kontrollert legacybackfill i fase 4G

`backfill_phone_identity` krever komplett eksplisitt tenantscope og forventet
eksakt tenantantall. Den setter ikke region gjennom modell- eller
databasedefault; bare en eksplisitt `--apply` kan sette de valgte tenantene og
normalisere gyldige Organization- og PHONE-`PersonContact`-rader. Ugyldige
eller regionløse verdier bevares raw med canonical felt som `NULL`.

Kommandoen verifiserer eksisterende canonical data uten å overskrive dem,
blokkerer Person/primær PHONE-integritetsavvik og endrer aldri `Person.phone`,
rå kontaktverdier, primærstatus, publiseringsflagg eller OrganizationPerson.
To aggregert redakterte fingerprints beskytter råtelefon og publisering før og
etter apply; et tredje sporer de additive feltene.

Apply krever unik batch-ID og skriver et no-clobber rollbackmanifest med bare
nødvendige ID-er og additive feltverdier til en operatøreid path utenfor Git.
Rollback gjenoppretter bare feltene batchen faktisk endret og stopper ved
post-batch drift. Se [operatørprosedyren](../operations/PHONE_BACKFILL.md).

## Samlet stagingstate etter fase 4H

Fase 4G satte eksplisitt `NO` på alle tre stagingtenantene og skrev 61
additive endringer: 3 tenantregioner, 2 Organization-identiteter og 56 PHONE-
`PersonContact`-identiteter. Råverdier og publiseringsstate beholdt eksakt
samme fingerprints som før apply, og repetert dry-run er `0`.

[Fase 4H-sluttevidensen](../status/STAGING_PHASE_4H_PHONE_TECHNICAL_VERIFICATION_2026-08-26.md)
verifiserer schema/defaults, Editor, API, Import, cross-tenant, PUBLIC,
backfillmanifest/isolert rollback, full testmatrise og post-change
backup/restore. Restorekopien hadde samme migrasjon, regioner, tellinger,
canonical state og fingerprints som live.

[Siste owner-smoke UI-polish](../status/STAGING_PHASE_4_OWNER_SMOKE_UI_POLISH_2026-08-29.md)
stagingverifiserer i tillegg det backend-avledede landkodehintet, uendret
public shape og rå/canonical kontrakt uten persistente testdata.

[Endelig owner-smoke](../status/PHASE_4_OWNER_APPROVAL_2026-08-29.md)
godkjente de tre siste UI-punktene 2026-08-29. Status er
`PHASE 4 = CLOSED / VERIFIED`.
