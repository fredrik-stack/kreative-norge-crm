# Feature: Import

**Status:** implementert og under kvalitetssikring; fase 4F-telefonkontrakten er teknisk stagingverifisert gjennom samlet fase 4H-gate

Brukeren skal kunne laste opp kontaktdata, få radvis preview, se konflikter og forslag, redigere beslutninger og eksplisitt commite godkjente rader.

Dagens løsning omfatter CSV/XLSX-basert flyt, matching, validering, AI-forslag, review, commit og feilrapport. Google Sheets, Checkin og Mailmojo er planlagt senere og er ikke implementerte kilder.

## Godkjent Import 2.0-opplevelse – ennå ikke implementert

[UX-spesifikasjon v6, revisjon 4](IMPORT_2_0_UX_SPEC_V6.md) er den godkjente
produktkontrakten. [Fase 5D-rapporten](../status/PHASE_5D_USER_TEST_REPORT_2026-10-11.md)
dokumenterer owner-approved intern validering med to formelle kollegadeltakere
og prosjekteiers egen gjennomgang. R12/O-24 avslutter UX-godkjenningen
2026-10-12: Kategorier og tags, Telefon, Berikelsesnivå og Stedsavklaring er
tilgjengelige ved Filtrerte kandidater; de tre feltfiltrene beholdes, med
virkning bare innen det låste utvalget og ærlig null effekt.

Ingen ny manuell prototypetest eller formell brukertest gjenstår som gate.
Dokumentene leveres på dokumentasjonsbranchen for separat draft-PR-review;
merge er ikke utført. Etter leveransen og fersk main følger ustartet read-only
5E før godkjent nødvendig grunnmur og senere Import 2.0-implementering.
Den aktive importmotoren og telefon-/bildekontraktene nedenfor er uendret.

## Aktive og planlagte importkontrakter

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

[ADR-012](../decisions/ADR-012-PLACE_IDENTITY_GEOGRAPHIC_CLASSIFICATION_AND_ACTOR_ONLY_MAPS.md)
beslutter i tillegg den framtidige `STEDER`-kontrakten og additiv overgang fra
dagens fritekststeder. Unike Place-/relasjonskandidater, duplicate-/similarity-
kontroll, betinget tvetydighetsreview og rådgivende tenantforslag skal
ferdigstilles før eksplisitt commit. Importrevieweren kan velge eksisterende og
opprette source-backed eller manuelt brukerbekreftet canonical Place i
normalflyten uten plattform-superadmin; bare globale registerkonflikter
eskaleres. Stedscommit kjører aldri Google/geokoding/providerkall og oppretter
aldri public status eller assignment automatisk. PersonPlace er strukturert data
uten kart eller Google-persondatascope. Dette er ikke implementert i dagens
importflyt.
