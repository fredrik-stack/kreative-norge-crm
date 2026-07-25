# Feature: Public

**Status:** grunnløsning implementert; kontaktregel rettet som mellomleveranse

Public skal vise et kontrollert utvalg av publiserte aktørdata i et symmetrisk og skalerbart grensesnitt.

Dagens public API fungerer, og HTML-visningen brukes i staging. Public API og public HTML bruker samme kontaktregel: personer vises bare når `OrganizationPerson.publish_person=True`, og e-post/telefon vises bare fra `PersonContact` med `is_public=True`.

`Person.email` og `Person.phone` brukes ikke som offentlig fallback. `ADR-005` har besluttet at personkontakt senere skal publiseres per aktør–person-kobling gjennom én felles offentlig projeksjon. Den langsiktige omleggingen er ikke implementert. Endelig visuelt design, filtrering, detaljsider, API-versjonering og integrasjon mot Musikkontoret.no er fortsatt uavklart.
