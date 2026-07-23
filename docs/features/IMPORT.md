# Feature: Import

**Status:** implementert og under kvalitetssikring

Brukeren skal kunne laste opp kontaktdata, få radvis preview, se konflikter og forslag, redigere beslutninger og eksplisitt commite godkjente rader.

Dagens løsning omfatter CSV/XLSX-basert flyt, matching, validering, AI-forslag, review, commit og feilrapport. Google Sheets, Checkin og Mailmojo er planlagt senere og er ikke implementerte kilder.

`ADR-005` har besluttet målretningen for kontaktimport, men denne er ikke implementert. Ved kontaktomleggingen skal blank input bevare eksisterende data, og primærstatus eller publisering skal bare endres etter eksplisitt valg og review.
