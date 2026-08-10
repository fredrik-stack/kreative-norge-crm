# Editor

**Status:** implementert grunnløsning; fase 2-standarder for kontaktpublisering implementert; fase 3D.1 offisiell bildekandidatflyt teknisk aktivert i staging bak miljøstyrt featuregate; manuell visuell kontroll gjenstår

React-editoren støtter tenantvalg, rollebasert tilgang, aktører, personer, relasjoner, kontaktkanaler, søk, taksonomifiltrering og import/eksport-side.

Editoren har håndtering av ulagrede endringer og egne URL-er for oversikter og detaljvisninger.

## Implementert Aktørbilde-flyt bak featureflag

Når `IMAGE_ASSET_FEATURE_ENABLED=True` for et miljø, viser Organization-editoren seksjonen `Aktørbilde`. Redaktøren kan eksplisitt finne kandidater fra aktørens `website_url`, se servergenererte kandidatpreviews uten hotlinking, velge én kandidat, velge `Foto`/cover eller `Logo`/contain, justere valgfritt fotofokus, prosessere bare det valgte bildet og kontrollere interne `square`-, `landscape`- og `share`-previews. Alt-tekst er påkrevd, offentlig kreditering er valgfri, og bare `Godkjenn og lås bilde` eller `Godkjenn og erstatt bilde` oppretter en aktiv `OrganizationImageSelection`.

Aktiv selection vises med revisjon og tre interne previews. Expected-revision-konflikter og nettverks-/processingfeil vises kontrollert. Vanlig Organization-save, discovery, kandidat-preview og processing kan ikke velge eller erstatte bilde. Den eksisterende `Public Preview (legacy)` er fortsatt en separat legacyvisning; de nye previewene er ikke offentlig publisert.

Seksjonen er skjult når flagget er av, som fortsatt er standard. Brave/generelt bildesøk, limt URL, brukerrettet upload, historikk-/restore-UI, takedown, public projection og PUBLIC-bildebruk er ikke implementert i denne leveransen.

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

Alle nye publiseringsvalg starter avslått:

- ny persons e-postadresse er intern
- nytt telefonnummer er internt
- ny person vises ikke offentlig som kontaktperson
- kobling av en eksisterende person publiserer ikke personen

Editor-tekstene skiller mellom å vise personen som kontaktperson på aktørsiden og å gjøre den konkrete e-postadressen eller telefonen offentlig. Eksisterende lagrede publiseringsvalg endres ikke av disse standardene.

## Planlagt kontaktopplevelse

`ADR-005` er godkjent som langsiktig målarkitektur. Relasjonsspesifikk offentlig kontaktpublisering er ikke implementert.

Editor skal senere presentere kontaktinformasjon som én sammenhengende funksjon:

- flere e-poster og telefonnumre i én kontaktseksjon
- tydelig intern primærkontakt
- offentlig kontaktvalg per aktør–person-kobling
- relasjonsspesifikke kontaktvalg slått av som standard
- atomisk lagring av person, kontakter, kobling og publisering
- preview fra samme offentlige projeksjon som HTML og API

Detaljert komponent- og dataflyt dokumenteres i neste fase.
