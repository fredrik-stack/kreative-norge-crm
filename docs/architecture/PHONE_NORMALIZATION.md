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

Fase 4C legger ikke til schema, migrasjon, API, Editor-, Import-, matching-,
repair- eller backfilladferd. Disse koblingene får egne gater fra fase 4D.

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
