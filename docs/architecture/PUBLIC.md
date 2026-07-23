# Public Architecture

**Status:** Implementert grunnløsning, videreutvikling og feilretting planlagt

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

## Kjent feilområde: kontaktpersoners e-post

Det er rapportert at mange eller alle e-postadresser for kontaktpersoner kan mangle både i Editor CRM og PUBLIC. Ingen rotårsak er konkludert.

Undersøkelsen skal følge datakjeden:

1. Er e-post lagret på `Person.email`, i `PersonContact`, eller begge steder?
2. Finnes korrekt `OrganizationPerson`-kobling og er personen aktiv?
3. Bevares `publish_person` ved redigering?
4. Bevares `PersonContact.is_public` ved redigering og import?
5. Returnerer serializer riktig kontaktdata?
6. Viser frontend dataene den mottar?
7. Finnes eldre data som aldri har fått de nye publiseringsflaggene?

Feilen skal først reproduseres med konkrete testdata. Deretter skal backend- og frontendtester legges til før eller sammen med rettingen.

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