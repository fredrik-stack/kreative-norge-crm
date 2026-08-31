# Feature: Import

**Status:** implementert og under kvalitetssikring; fase 4F-telefonkontrakten er teknisk stagingverifisert gjennom samlet fase 4H-gate

Brukeren skal kunne laste opp kontaktdata, få radvis preview, se konflikter og forslag, redigere beslutninger og eksplisitt commite godkjente rader.

Dagens løsning omfatter CSV/XLSX-basert flyt, matching, validering, AI-forslag, review, commit og feilrapport. Google Sheets, Checkin og Mailmojo er planlagt senere og er ikke implementerte kilder.

Import støtter `person_email_public` og `person_phone_public` for eksplisitt publisering av primær kontakt. Manglende eller tom publiseringskolonne bevarer eksisterende `is_public` ved oppdatering og bruker intern standard for ny kontakt.

Importjobbens synlige telefonregion fryses i jobbkonfigurasjonen. Eksplisitt
jobbvalg overstyrer tenantdefaulten, og «ingen region» kan velges eksplisitt.
Gyldige numre committes med bevart presentasjonsverdi og intern canonical
E.164-identitet. Ugyldige numre og nasjonale numre uten region sendes til
review; blank telefon betyr `KEEP`. Canonical telefon styrker matching sammen
med samme navn, men telefon alene gir aldri automatisk personmerge.

`ADR-005` har besluttet målretningen for kontaktimport. Den langsiktige relasjonsspesifikke kontaktmodellen er ikke implementert. Ved videre kontaktomlegging skal blank input fortsatt bevare eksisterende data, og primærstatus eller publisering skal bare endres etter eksplisitt valg og review.

Fase 3F har implementert en intern typed bildekontrakt for senere Import 2.0 med `KEEP_LOCKED_IMAGE`, `SET_APPROVED_IMAGE` og `USE_APPROVED_FALLBACK`. Kontrakten er additiv, relational og default-off med `IMPORT_IMAGE_DECISIONS_ENABLED=False`; dagens importskjemaer, kolonner og brukergrensesnitt er uendret. Uten en eksplisitt typed beslutning beholdes eksisterende selection, og import-commit utfører ingen Open Graph-refresh, søk, DNS/HTTP, nedlasting, decode, rendition-generering, release eller publiseringsendring. Full image review-UX hører fortsatt til den senere Import 2.0-fasen.

[ADR-011](../decisions/ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md)
beslutter den framtidige identity-/assignmentgrensen, ikke ny import-runtime.
Senere domain-wide matching skal være privacy-minimert og kreve aktiv
membership, agreement og capability. Canonical core, privat overlay, relation,
assignment og publication skal være separate reviewbeslutninger; assignment og
publication kan aldri skje skjult. Persistent import package og rapportstorage,
proveniens, backup/restore, retensjon og database–fil-konsistens er en hard gate
før Import 2.0-aktivering og er ikke implementert av ADR-011.
