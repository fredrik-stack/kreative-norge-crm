# Roadmap

**Status:** Strategisk arbeidsdokument

**Sist oppdatert:** 2026-07-23

## Fase 0 – Sikre utviklingsarbeidsflyten

Gjennomført:

- etablert GitHub som levende sannhetskilde
- etablert Fredrik Development System med `AGENTS.md`, dokumentert workflow og 12 repo-baserte Codex-skills
- sikret at ChatGPT og Codex har dokumenterte oppstarts- og sannhetskilder
- etablert ADR-gate for større implementeringer
- etablert dokumentasjonsplikt ved funksjonelle endringer

Gjenstår:

- planlegge automatisk staging-deploy ved push
- definere minimumstester før deploy

## Fase 1 – Stabilisering av PUBLIC og kontaktdata

Diagnosen er gjennomført, og målarkitekturen er godkjent i `ADR-005`. Implementering er ikke startet.

Arbeidet skal gjennomføres som små, sekvensielle leveranser:

1. **Beslutningsgater og databaseline**
   - godkjenne gjenværende produkt-, personvern-, rolle- og API-valg
   - kartlegge kontaktdata og offentlig før-bilde i staging og produksjon
   - godkjenne backup, migreringsmapping og rollback
2. **Kontrakts- og personverntester**
   - reprodusere dagens avvik mellom Editor, HTML og API
   - etablere publiseringsmatrise og negative personverntester
3. **Additiv kontaktmodell**
   - utvide `PersonContact`
   - legge til constraints og relasjonsspesifikk kontaktpublisering
   - beholde alle legacy-felter
4. **Backfill og migreringsreview**
   - migrere direkte personfelt til interne kontaktposter
   - bevare eksplisitte offentlige valg
   - gjennomgå konflikter og tidligere HTML-fallback
5. **Felles domenetjeneste og internt API**
   - samle kontaktregler og atomisk lagring
   - stoppe ny skriving til direkte personfelt
6. **Samlet kontaktopplevelse i Editor**
   - én kontaktseksjon
   - primærkontakt og offentlig kontaktvalg per aktørkobling
   - preview fra felles offentlig projeksjon
7. **Kontaktregler i IMPORT**
   - trygg merge, eksplisitte operasjoner og tri-state publisering
   - ingen implisitt sletting, primærbytte eller publisering
8. **Felles PUBLIC-projeksjon**
   - samme resultat i HTML, API og Editor-preview
   - fjerne direktefeltfallback
   - avklare API-versjonering og Musikkontoret.no-kontrakt
9. **Kontaktbevisst EKSPORT**
   - intern arbeidsliste, offentlig katalog og full relasjonell eksport
10. **Legacy-opprydding**
    - fjerne gamle API-felter og databasefelter først etter stabilisering

Detaljerte akseptansekriterier og rollbackkrav finnes i `docs/decisions/ADR-005-CONTACT_ARCHITECTURE.md`.

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
