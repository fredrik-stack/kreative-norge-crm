# Import Architecture

**Status:** Teknisk motor implementert; større produkt- og UX-revisjon planlagt

**Sist verifisert:** 2026-07-23

**Verifisert mot:** importmodellene, importtjenestene, API-handlingene, React-siden for import/eksport og nyere commit-historikk.

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

- hvordan importerte bilder og lenker skal samspille med fremtidig bildelagring
- hvordan store jobber senere skal behandles asynkront
- hvor lenge importfiler og rapporter skal lagres

## Besluttet kontaktretning

`ADR-005` er godkjent, men ikke implementert.

Ved fremtidig kontaktomlegging skal import:

- skrive personers e-post og telefon til `PersonContact`
- tolke blank input som `KEEP`, ikke `CLEAR`
- bevare primærstatus og publisering når endring ikke er eksplisitt
- behandle publisering som tri-state og høyrisiko-review
- aldri la AI foreslå eller aktivere publisering
- støtte relasjonsspesifikk offentlig kontaktinformasjon

Detaljerte leveranser og akseptansekriterier finnes i ADR-et.
