# Phone normalization domain

Telefonnormalisering er implementert som én ren intern domenegrense i
`crm/services/phone_normalization.py`. Den presiserer fase 4C i
[ADR-010](../decisions/ADR-010-INTERNATIONAL_PHONE_IDENTITY_AND_NORMALIZATION.md)
uten å koble normaliseringen til modeller, API, Editor eller import.

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
callers ansvar i senere faser å levere eksplisitt og sporbar regionkontekst,
bevare presentasjonsverdien og håndtere review, lagring og publisering.

Fase 4C la ikke til schema eller callers. Fase 4D la bare til den additive
persistensen. Fase 4E kobler ordinære interne Organization-, Person- og
PHONE-`PersonContact`-writes til adapteren; Import, matching, repair og
legacybackfill er fortsatt egne senere gater.

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

Personens direkte kompatibilitetsfelt synkroniseres fortsatt med primær
PHONE-`PersonContact`, og identiteten ligger bare på kontakten. Eksplisitt
tømming fjerner den primære telefonkontakten; sekundære kontakter og alle
publiseringsvalg berøres ikke. Serializerlaget normaliserer bare når selve
råtelefonen opprettes eller faktisk endres. Et fullstendig Editor-payload med
uendret legacytelefon kan derfor ikke gi incidental backfill.

## Verifikasjon og rollback

Syntetiske tester dekker norske, svenske og britiske numre, internasjonale
`+`-numre, regionuavhengighet, `00`, manglende/ugyldig region, parsefeil,
mulighet kontra gyldighet, extension, E.164-idempotens, personvern og
deterministiske resultater.

Fase 4C er verifisert API-only i shared staging med dependency `9.0.37`,
syntetisk smoke, to identiske real-data-kjøringer i read-only transaksjoner og
uendrede fingerprints for Organization, Person, PHONE PersonContact og
OrganizationPerson. Se [stagingevidensen](../status/STAGING_PHASE_4C_PHONE_NORMALIZATION_2026-08-25.md).

Før fase 4D kan rollback gjøres ved å reversere adapteren, testene og den
pinnede dependencyen. Ingen data- eller migrasjonsrollback er nødvendig.
