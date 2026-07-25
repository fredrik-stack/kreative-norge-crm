# Editor

**Status:** implementert grunnløsning; kontaktkanalredigering rettet som mellomleveranse

React-editoren støtter tenantvalg, rollebasert tilgang, aktører, personer, relasjoner, kontaktkanaler, søk, taksonomifiltrering og import/eksport-side.

Editoren har håndtering av ulagrede endringer og egne URL-er for oversikter og detaljvisninger.

## Implementert kontaktopplevelse

Editor CRM er intern og viser kontaktinformasjon også når `PersonContact.is_public=False`.

På personens redigeringsside kan redaktøren:

- se primær e-post og telefon i kompatibilitetsfeltene `Person.email` og `Person.phone`
- se alle lagrede `PersonContact` for personen
- se hvilke kontakter som er primære
- endre kontaktverdi
- styre `is_primary`
- styre `is_public` med tekstene `Vis e-post offentlig` og `Vis telefon offentlig`

På aktørsiden skilles personpublisering fra kontaktpublisering:

- `Vis person offentlig` / `publish_person` styrer om personen vises offentlig for aktøren
- `PersonContact.is_public` styrer om e-post eller telefon vises i PUBLIC
- aktørkortet i Editor viser intern kontaktinformasjon og merker kontaktkanaler som `Offentlig` eller `Intern`

## Planlagt kontaktopplevelse

`ADR-005` er godkjent som langsiktig målarkitektur. Relasjonsspesifikk offentlig kontaktpublisering er ikke implementert.

Editor skal senere presentere kontaktinformasjon som én sammenhengende funksjon:

- flere e-poster og telefonnumre i én kontaktseksjon
- tydelig intern primærkontakt
- offentlig kontaktvalg per aktør–person-kobling
- alle publiseringsvalg slått av som standard
- atomisk lagring av person, kontakter, kobling og publisering
- preview fra samme offentlige projeksjon som HTML og API

Detaljert komponent- og dataflyt dokumenteres i neste fase.
