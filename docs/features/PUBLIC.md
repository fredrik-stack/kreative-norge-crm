# Feature: Public

**Status:** grunnløsning implementert; kontakt- og lenkeregel rettet som mellomleveranse

Public skal vise et kontrollert utvalg av publiserte aktørdata i et symmetrisk og skalerbart grensesnitt.

Dagens public API fungerer, og HTML-visningen brukes i staging. Public API og public HTML bruker samme kontaktregel: personer vises bare når `OrganizationPerson.status=ACTIVE` og `OrganizationPerson.publish_person=True`, og e-post/telefon vises bare fra `PersonContact` med `is_public=True`.

`Person.email` og `Person.phone` brukes ikke som offentlig fallback. PUBLIC HTML-kort lenker til kanoniske ID-baserte aktørsider, slik at publiserte aktører uten organisasjonsnummer fortsatt får fungerende detaljside.

Staging-data ble rettet 2026-07-26 slik at eksisterende e-postkontakter er offentlige, unntatt at tre navngitte aktør-person-koblinger er interne via `publish_person=False`.

`ADR-005` har besluttet at personkontakt senere skal publiseres per aktør–person-kobling gjennom én felles offentlig projeksjon. Den langsiktige omleggingen er ikke implementert. Endelig visuelt design, filtrering, API-versjonering og integrasjon mot Musikkontoret.no er fortsatt uavklart.
