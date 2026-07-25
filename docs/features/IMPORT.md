# Feature: Import

**Status:** implementert og under kvalitetssikring

Brukeren skal kunne laste opp kontaktdata, få radvis preview, se konflikter og forslag, redigere beslutninger og eksplisitt commite godkjente rader.

Dagens løsning omfatter CSV/XLSX-basert flyt, matching, validering, AI-forslag, review, commit og feilrapport. Google Sheets, Checkin og Mailmojo er planlagt senere og er ikke implementerte kilder.

Import støtter `person_email_public` og `person_phone_public` for eksplisitt publisering av primær kontakt. Manglende eller tom publiseringskolonne bevarer eksisterende `is_public` ved oppdatering og bruker intern standard for ny kontakt.

`ADR-005` har besluttet målretningen for kontaktimport. Den langsiktige relasjonsspesifikke kontaktmodellen er ikke implementert. Ved videre kontaktomlegging skal blank input fortsatt bevare eksisterende data, og primærstatus eller publisering skal bare endres etter eksplisitt valg og review.
