# Public Architecture

**Status:** Implementert grunnløsning; kontaktregel for e-postflyt rettet som mellomleveranse

**Sist verifisert:** 2026-07-26

**Verifisert mot:** public-ruter, `PublicActorViewSet`, public serializer, modeller, public HTML-template, importtjenester, React-editor og regresjonstester.

## Omfang

Public består av:

- åpent API for publiserte aktører
- HTML-visning som foreløpig bare brukes i staging
- publiserte aktørdata, taksonomi, lenker, bilde og eventuelle kontaktpersoner

## Aktørdetaljer

PUBLIC HTML bruker en kanonisk ID-basert detaljrute:

- listekort lenker til `/public/actors/id/<actor_id>/`
- Django-template skal bruke `{% url 'public-actor-detail' actor.id %}`, ikke manuell sammensetting med `org_number`
- den gamle ruten `/public/actors/<org_number>/` beholdes som legacy-rute og redirecter bare når `org_number` identifiserer nøyaktig én publisert aktør

Denne regelen gjør at publiserte aktører uten organisasjonsnummer fortsatt får fungerende PUBLIC-lenke. Kommandoen `check_public_actor_links` kan kjøres skrivebeskyttet for å kontrollere at alle kortlenker fra PUBLIC-listen svarer uten 404.

## Publiseringsregler

Publisering styres blant annet av:

- `Organization.is_published`
- `Organization.publish_phone`
- `OrganizationPerson.status`
- `OrganizationPerson.publish_person`
- `PersonContact.is_public`

Personmodellen har også direkte `email` og `phone`. Dette gjør kontaktarkitekturen todelt og krever tydelig dokumentasjon og tester.

Implementert mellomregel fra 2026-07-25:

- `OrganizationPerson.publish_person` bestemmer om personen vises som kontaktperson offentlig.
- `PersonContact.is_public` bestemmer om den enkelte e-postadressen eller telefonen vises offentlig.
- `Person.email` og `Person.phone` er interne kompatibilitetsfelt og brukes ikke som PUBLIC-fallback.
- PUBLIC HTML og PUBLIC API bruker samme regel: bare aktive koblinger med `publish_person=True`, og bare kontaktkanaler med `is_public=True`.
- En offentlig person kan vises uten offentlig e-post eller telefon.

## Rettet feilområde: kontaktpersoners e-post

Diagnosen viser at problemet skyldes en todelt kontaktarkitektur og flere kontaktresolvere:

- `Person.email` og `Person.phone` finnes parallelt med `PersonContact`
- Editor viser og lagrer i hovedsak direktefeltene
- enkelte opprettingsflyter skriver begge steder
- public API brukte eksplisitte offentlige `PersonContact`
- public HTML kunne falle tilbake til direkte person-e-post
- import kunne oppdatere begge kilder og publiseringsflagg

Rettet mellomleveranse:

- public HTML bruker ikke lenger fallback til `Person.email`
- public API og HTML viser samme offentlige kontaktinformasjon
- direkte personfelt holdes synkronisert med primær intern `PersonContact` for e-post og telefon
- eksisterende direkte e-post blir ikke automatisk offentlig

## Engangspublisering av eksisterende e-post

For den godkjente staging-rettingen 2026-07-26 finnes management-kommandoen `publish_existing_email_contacts`.

Kommandoen er ikke en migrasjon og kjører som dry-run uten endringer som standard. Med `--apply` gjør den følgende i én transaksjon:

- setter alle eksisterende `PersonContact` med `type=EMAIL` til `is_public=True`
- setter aktive `OrganizationPerson`-koblinger til `publish_person=True`
- lar disse tre konkrete aktør-person-relasjonene være interne ved `publish_person=False`:
  - `Nordland fylkeskommune` / `Kathrine Schjem`
  - `Nordland fylkeskommune` / `Ole-Thomas Kolberg`
  - `Bådin` / `Jonas Jørgensen Moe`

Unntakene er relasjonsspesifikke. Personen gjøres ikke globalt privat, telefonpublisering endres ikke, og `Organization.is_published` endres ikke. Kommandoen avbryter uten endringer dersom unntakene ikke kan identifiseres entydig.

Målarkitekturen er godkjent i `ADR-005`:

- `PersonContact` blir autoritativ kilde
- offentlige kontaktkanaler velges per aktør–person-kobling
- HTML, API og Editor-preview bruker én offentlig projeksjon
- direktefeltfallback fjernes

Full ADR-005-målmodell med relasjonsspesifikk kontaktpublisering er fortsatt planlagt og ikke implementert.

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
