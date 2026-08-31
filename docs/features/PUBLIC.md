# Feature: Public

**Status:** grunnløsning implementert; kontakt-, lenke- og tittelregel stabilisert i fase 2; 3E.3-bilde-/head-cutover er `CLOSED / ACTIVE` i staging

Public skal vise et kontrollert utvalg av publiserte aktørdata i et symmetrisk og skalerbart grensesnitt.

Dagens public API fungerer, og HTML-visningen brukes i staging. Public API og public HTML bruker samme kontaktregel: personer vises bare når `OrganizationPerson.status=ACTIVE` og `OrganizationPerson.publish_person=True`, og e-post/telefon vises bare fra `PersonContact` med `is_public=True`.

`Person.email` og `Person.phone` brukes ikke som offentlig fallback. PUBLIC HTML-kort lenker til kanoniske ID-baserte aktørsider, slik at publiserte aktører uten organisasjonsnummer fortsatt får fungerende detaljside.

På PUBLIC HTML beholdes telefonens rå skrivemåte som synlig tekst. Når kontakten
har lagret canonical E.164-identitet, bruker lenken dette som `tel:`-mål;
manglende canonical identitet gir ikke-klikkbar råtekst. Public API-shape og
publiseringsreglene er uendret.

Når en publisert kontaktperson har `Person.title`, vises tittelen både i public API og på PUBLIC HTML-kortet. Null eller tom tittel gir ikke en tom visningsrad eller et tomt API-felt.

Etter 3E.3-gaten bruker API, PUBLIC list/detail og delingsmetadata samme read-only bildeprojection i staging. Kort og hero bruker square, Open Graph/Twitter bruker share, og canonical kommer fra konfigurert site-origin. Manglende eller ikke-autorisert asset gir production fallback v1 med blank alttekst, aldri legacybilde. Kode-/eksempelstandarden `PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=False` bevarer sikker opt-in; den ignorerte stagingverdien er `True` etter dokumentert aktivering og rollbacktest.

Nye publiseringsvalg i Editor starter avslått. En telefon fra legacy-feltet kan repareres til en privat primær `PersonContact` gjennom en eksplisitt, dry-run-først-kommando, men blir aldri offentlig som bivirkning.

Editor viser nå den effektive kombinasjonen av `publish_person` og
`PersonContact.is_public` per aktørkobling. Dette er forklarende UX rundt dagens
mellommodell, ikke relasjonsspesifikk kontaktpublisering og ikke full ADR-005.

Staging-data ble rettet 2026-07-26 slik at eksisterende e-postkontakter er offentlige, unntatt at tre navngitte aktør-person-koblinger er interne via `publish_person=False`.

`ADR-005` har besluttet at personkontakt senere skal publiseres per aktør–person-kobling gjennom én felles offentlig projeksjon. Den langsiktige omleggingen er ikke implementert. Endelig visuelt design, filtrering, API-versjonering og integrasjon mot Musikkontoret.no er fortsatt uavklart.

[ADR-011](../decisions/ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md)
har i tillegg godkjent én framtidig PUBLIC-identitet og global publication state
per canonical Organization. Dette er ikke implementert: dagens aktører og tags
er fortsatt direkte tenant-eide. Målprojeksjonen skal returnere aktøren én gang,
bruke bare shared editorial tags og aldri eksponere assignments eller private
overlays. Offisiell `Organization.email` følger aktørens PUBLIC-state uten et
nytt `publish_email`-flagg; telefon beholder eget publiseringsvalg. Structured
places og actor-only maps avventer ADR-012, og personer får aldri kartpunkter.
