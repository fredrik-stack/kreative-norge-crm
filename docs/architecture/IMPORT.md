# Import Architecture

**Status:** Teknisk motor implementert; fase 4F telefonkontrakt implementert og avventer staginggate; større produkt- og UX-revisjon planlagt

**Sist verifisert:** 2026-08-26

**Verifisert mot:** importmodellene, importtjenestene, API-handlingene, React-siden for import/eksport, kontaktregresjonstester og nyere commit-historikk.

## Implementert teknisk flyt

1. Opprette `ImportJob` innenfor én tenant.
2. Velge importmodus: kombinert, bare aktører eller bare personer.
3. Laste opp fil.
4. Parse filen og normalisere kolonner til CRM-strukturen.
5. Validere felt, tenant-regler og taksonomi.
6. Matche mot eksisterende aktører og personer.
7. Klassifisere rader som oppretting, oppdatering, kobling, review eller skip.
8. Forberede og generere heuristiske og OpenAI-baserte forslag.
9. Gjennomføre radvis review og lagre eksplisitte beslutninger.
10. Committe godkjente data til CRM-modellene.
11. Lagre commit-logg og produsere feilrapport.

## Sentrale modeller

- `ImportJob`: fil, konfigurasjon, status, sammendrag og rapporter
- `ImportRow`: rådata, normaliserte data, matching, forslag, feil, advarsler og handling
- `ImportDecision`: brukerens eksplisitte valg i review
- `ImportCommitLog`: spor av opprettede, oppdaterte, koblede, hoppede eller feilede enheter

## API-flyt

Importjobber støtter oppretting, opplasting, preview, radvis uthenting, AI-generering, lagring av beslutninger, commit og feilrapport.

## AI og fallback

AI-generering utføres kontrollert og kan suppleres av heuristiske forslag. Systemet registrerer om OpenAI ble brukt, om fallback ble brukt, om forslag manglet og om genereringen feilet. AI-forslag skal alltid behandles som forslag som kan kreve menneskelig kontroll.

## Faktisk og planlagt kildestøtte

CSV og XLSX er del av dagens filbaserte importarbeid. Følgende finnes bare som reserverte kildetyper og er planlagt senere:

- Google Sheets
- Checkin
- Mailmojo

De skal ikke dokumenteres som fungerende integrasjoner før kode, tester og brukerflyt finnes.

## Kvalitetsprinsipp

Import skal ikke være en ukontrollert masseoppretting. Review, eksplisitte beslutninger, validering og sporbarhet er grunnleggende arkitekturvalg.

## Telefonkontrakt i fase 4F

Hver importjobb fryser `phone_region` i `ImportJob.config_json`. Eksplisitt
jobbvalg har prioritet over tenantens nullable default, og eksplisitt `null`
slår av defaulten for den jobben. Senere tenantendringer påvirker ikke retry
eller preview av en eksisterende jobb. Norge brukes aldri skjult.

Ikke-tomme telefonverdier normaliseres gjennom den felles adapteren og lagres i
preview-payloaden med typed status `VALID`, `INVALID` eller `NEEDS_REGION`,
stabil årsakskode, eventuell E.164 og faktisk brukt region. Tom eller manglende
verdi er typed `KEEP` og kaller ikke adapteren. `INVALID` og `NEEDS_REGION`
krever review og committes ikke automatisk.

Ved commit beholdes rå presentasjonsverdi, mens gyldig E.164 og faktisk brukt
region lagres på Organization eller PHONE-`PersonContact`. Blank eller usikker
telefon overskriver ikke eksisterende telefonidentitet. Publiseringsvalg endres
bare når importkolonnen var eksplisitt; telefonnormalisering eller matching kan
aldri publisere data.

Personmatching bruker samme navn og canonical E.164 som et sterkt
`NAME_AND_PHONE`-signal når begge sider har canonical identitet. Samme telefon
alene er aldri personidentitet, tvetydige treff auto-merges ikke, og matching er
tenant-scopet. En kontrollert eksakt råverdi-fallback beholdes frem til fase 4G
har gjennomført legacybackfill.

## Kontaktfelt i dagens import

`person_email` lagres fortsatt i `Person.email` og synkroniseres til primær `PersonContact` av type `EMAIL`.

`person_phone` lagres fortsatt i `Person.phone` og synkroniseres til primær `PersonContact` av type `PHONE`.

Publisering av primær e-post og telefon er tri-state:

- manglende eller tom `person_email_public` / `person_phone_public`: bevar eksisterende `is_public`, eller bruk `False` for ny kontakt
- eksplisitt sann verdi: sett primærkontakten offentlig
- eksplisitt usann verdi: sett primærkontakten intern

Sekundærfeltene `person_secondary_emails_public` og `person_secondary_phones_public` gjelder fortsatt for sekundære kontaktkanaler.

## Planlagt større UX-revisjon

Dagens tekniske motor er et fundament, men dagens brukeropplevelse skal ikke låse neste løsning. Før videre implementering skal en egen planfase definere en gamification-inspirert arbeidsflyt.

Den nye opplevelsen skal:

- vise tydelig fremdrift, gjenstående arbeid og oppnådd datakvalitet
- prioritere rader etter risiko og behov for menneskelig vurdering
- gjøre enkle avgjørelser raske uten å skjule konsekvenser
- gi mestringsfølelse gjennom delmål, grupper og ferdigmarkering
- bevare arbeid fortløpende og tåle avbrudd
- redusere kognitiv belastning og repetisjon
- aldri premiere hastighet på bekostning av korrekt data

## Før ny implementering

Det skal utarbeides:

- brukerreise og problemkart
- oversikt over dagens friksjon og tidsbruk
- prinsipper for gamification og kvalitetsmåling
- informasjonsarkitektur og wireframes
- beslutning om hvilke steg som kan automatiseres
- akseptansekriterier og brukertestopplegg
- etappevis implementeringsplan

## Åpne arkitekturspørsmål

- hvordan store jobber senere skal behandles asynkront
- hvor lenge importfiler og rapporter skal lagres

## Godkjent fremtidig bildekontrakt

[ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) avgjør prinsippene for hvordan Import 2.0 senere skal samspille med bildearkitekturen. Fase 3F har implementert den typed backendkontrakten bak `IMPORT_IMAGE_DECISIONS_ENABLED=False`; produkt- og review-UX for Import 2.0 er fortsatt ikke implementert.

Fremtidige typed bildeutfall er:

- `KEEP_LOCKED_IMAGE`
- `SET_APPROVED_IMAGE`
- `USE_APPROVED_FALLBACK`

Manglende bildevalg for en eksisterende aktør betyr `KEEP_LOCKED_IMAGE`. Et tenant-eid asset kan være teknisk validert og godkjent før en ny `Organization` opprettes. En typed importbeslutning skal da referere med referanseintegritet til asset, fit, fokus, processing-version, ferdig rendition-sett og et immutable proposed-actor-/ImportRow-snapshot.

`SET_APPROVED_IMAGE` eller `USE_APPROVED_FALLBACK` mot en eksisterende låst selection er en eksplisitt replacement og skal stoppe dersom selection-revisjonen har endret seg etter review.

Import-commit skal bare koble et allerede godkjent og ferdig asset eller fallbackvalg. Den skal ikke utføre Brave-søk, Open Graph-henting, ekstern nedlasting, dekoding, rendition-generering, automatisk replacement eller noen publiseringsendring.

Approvalhistorikken skal ligge i append-only bildehistorikk, ikke bare i `decision_json` eller en commitlogg som kan regenereres. Full produkt- og review-UX for bilder implementeres fortsatt først som del av senere Import 2.0.

Migrasjon `0031` legger additivt til én `ImportImageDecision` per `ImportRow` og en nullable, beskyttet én-til-én-binding fra det anvendte `ImageReviewEvent`. Beslutningen fryser type, besluttende principal, target eller canonical proposed-actor-snapshot, forventet selection/revisjon og — for `SET_APPROVED_IMAGE` — tenant-eid asset/rendition-sett og approval-/proveniens-/checksum-/versjonssnapshots. `KEEP_LOCKED_IMAGE` uten eksplisitt beslutningsrad er fortsatt standard og gjør ingen image-write.

Ved commit låses beslutningsraden, proposed actor og target revalideres, og eksisterende selection må fortsatt ha eksakt reviewet ID og revisjon. `SET_APPROVED_IMAGE` bruker de vanlige selection-/approvalinvariantene; `USE_APPROVED_FALLBACK` bruker den vanlige fallbackkommandoen. Det produserte review-eventet peker tilbake på beslutningen, slik at retry returnerer samme resultat i stedet for å opprette en ny selection. Commit gjør ingen søk, DNS/HTTP, Open Graph-refresh, nedlasting, decode, rendition-generering, release/materialisering eller publiseringsendring. Feil tenant, stale selection, endret actor-snapshot, ufullstendig asset eller manglende approval feiler lukket.

## Besluttet kontaktretning

`ADR-005` er godkjent som langsiktig målarkitektur. Mellomleveransen fra 2026-07-25 implementerer tri-state publisering for dagens `PersonContact.is_public`, men ikke relasjonsspesifikk publisering.

Ved fremtidig kontaktomlegging skal import:

- skrive personers e-post og telefon til `PersonContact`
- tolke blank input som `KEEP`, ikke `CLEAR`
- bevare primærstatus og publisering når endring ikke er eksplisitt
- behandle publisering som tri-state og høyrisiko-review
- aldri la AI foreslå eller aktivere publisering
- støtte relasjonsspesifikk offentlig kontaktinformasjon

Detaljerte leveranser og akseptansekriterier finnes i ADR-et.
