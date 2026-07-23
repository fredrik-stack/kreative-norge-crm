# Public Architecture

**Status:** Implementert grunnløsning; kontaktfeil diagnostisert og målarkitektur besluttet, ikke implementert

**Sist verifisert:** 2026-07-23

**Verifisert mot:** public-ruter, `PublicActorViewSet`, public serializer, modeller og Editor/Public-adferd som er rapportert av prosjekteier.

## Omfang

Public består av:

- åpent API for publiserte aktører
- HTML-visning som foreløpig bare brukes i staging
- publiserte aktørdata, taksonomi, lenker, bilde og eventuelle kontaktpersoner

## Publiseringsregler

Publisering styres blant annet av:

- `Organization.is_published`
- `Organization.publish_phone`
- `OrganizationPerson.status`
- `OrganizationPerson.publish_person`
- `PersonContact.is_public`

Personmodellen har også direkte `email` og `phone`. Dette gjør kontaktarkitekturen todelt og krever tydelig dokumentasjon og tester.

## Diagnostisert feilområde: kontaktpersoners e-post

Diagnosen viser at problemet skyldes en todelt kontaktarkitektur og flere kontaktresolvere:

- `Person.email` og `Person.phone` finnes parallelt med `PersonContact`
- Editor viser og lagrer i hovedsak direktefeltene
- enkelte opprettingsflyter skriver begge steder
- public API bruker eksplisitte offentlige `PersonContact`
- public HTML kan falle tilbake til direkte person-e-post
- import kan oppdatere begge kilder og publiseringsflagg

Målarkitekturen er godkjent i `ADR-005`:

- `PersonContact` blir autoritativ kilde
- offentlige kontaktkanaler velges per aktør–person-kobling
- HTML, API og Editor-preview bruker én offentlig projeksjon
- direktefeltfallback fjernes

Dette er planlagt og ikke implementert. Dagens publiseringsregler og fallback gjelder fortsatt i kodebasen.

## Bilde og thumbnail

Dagens løsning velger mellom manuell thumbnail, automatisk thumbnail og Open Graph-bilde. Eksterne bilde-URL-er kan forsvinne, endres, blokkere hotlinking eller ha feil format.

Målarkitekturen skal vurderes før implementering og bør støtte:

- innhenting av kandidater fra Open Graph eller nettside
- menneskelig valg/godkjenning
- permanent lagring av valgt bilde
- standardisert beskjæring og skalering
- definert original, visningsformat og thumbnail-format
- manuell overstyring og trygg fallback
- registrering av kilde og tidspunkt
- lik presentasjon i Editor, PUBLIC og senere Musikkontoret.no

## Videre integrasjon

Løsningen er ikke ferdigstilt for ekstern integrasjon med Musikkontoret.no. Før dette må API-kontrakt, caching, bildeleveranse, personvern og publiseringsregler være eksplisitt spesifisert.
