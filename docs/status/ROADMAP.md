# Roadmap

**Status:** Strategisk arbeidsdokument

**Sist oppdatert:** 2026-07-23

## Fase 0 – Sikre utviklingsarbeidsflyten

- etablere GitHub som levende sannhetskilde
- sikre at ChatGPT kan lese oppdatert repo ved planlegging og kvalitetssikring
- sikre at Codex alltid leser status og relevante dokumenter før implementering
- etablere dokumentasjonsplikt ved funksjonelle endringer
- planlegge automatisk staging-deploy ved push
- definere minimumstester før deploy

## Fase 1 – Stabilisering av PUBLIC og kontaktdata

1. Reprodusere og rette feilen der kontaktpersoners e-post ikke vises i Editor CRM og/eller PUBLIC.
2. Kartlegge hele publiseringskjeden: `Person.email`, `PersonContact`, `is_public`, `OrganizationPerson.publish_person`, serializers, API og frontend.
3. Legge inn regresjonstester som sikrer at offentlig og intern kontaktinformasjon vises etter riktige regler.
4. Avklare endelig public-kontrakt mot Musikkontoret.no.

## Fase 2 – Robust bilde- og thumbnail-løsning

1. Kartlegge dagens Open Graph-flyt og feilmodi.
2. Beslutte permanent lagring, bildeformat, dimensjoner og beskjæring.
3. Designe manuell godkjenning/overstyring og stabil fallback.
4. Ivareta kilde, opphavsrett og mulighet for senere utskifting.
5. Implementere og teste lik bruk i Editor CRM, PUBLIC og fremtidig Musikkontoret.no-visning.

## Fase 3 – Ny IMPORT-produktstrategi

IMPORT skal ikke bare finjusteres videre. Før implementering gjennomføres en egen planfase for store UX-grep.

Mål:

- gamification-inspirert fremdrift og mestring
- raskere review uten redusert datakvalitet
- tydelig prioritering av hvilke rader som krever menneskelig innsats
- gode kvalitetsmål, fremdriftsindikatorer og trygg lagring
- enkel og intuitiv arbeidsflyt også for uerfarne brukere
- gjenbruk av dagens importmotor der den er solid

Leveranser før koding:

- brukerreise og problemkart
- prioriterte brukerhistorier
- informasjonsarkitektur
- skisser/wireframes
- beslutning om kvalitets- og gamification-mekanismer
- testplan og akseptansekriterier
- implementeringsplan i etapper

## Fase 4 – EKSPORT

- ferdigstille eksportmotor
- CSV- og XLSX-generering
- valg av felter, filtre og målgrupper
- sikker nedlasting og jobbhistorikk
- eksport for e-postlister og senere integrasjoner

## Fase 5 – Plattformmodning

- automatisk staging-deploy ved push
- CI og obligatoriske testgates
- auditlogg og sterkere sporbarhet
- videreutvikling av roller og invitasjoner
- eksterne tenant-rom

## Senere

- Google Sheets-import
- Checkin-import
- Mailmojo-import
- skjemaer og automatisk opprettelse av kontakter
- geografisk visning
- eksterne integrasjoner
- nettdugnad og samtykkebasert redigering