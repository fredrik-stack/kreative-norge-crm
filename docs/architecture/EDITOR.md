# Editor

**Status:** implementert grunnløsning; fase 2-standarder for kontaktpublisering implementert; fase 4E synlig telefonregion/servernormalisering og fase 4F synlig importjobbregion er teknisk stagingverifisert gjennom fase 4H og `READY_FOR_OWNER_SMOKE`; tre owner-smoke-funn i telefonlenker, intern aktørtelefon og effektiv PUBLIC-status er rettet og teknisk stagingreverifisert 2026-08-29; siste UI-polish etter andre owner-smoke er lokalt verifisert og avventer staging; fase 3D.1 offisiell bildekandidatflyt teknisk aktivert og visuelt godkjent i staging; fase 3D.2 med precision/zoom er gjennomført og merget til `main` med PR #33, fullverifisert lokalt, CI-grønn, historisk live Brave-verifisert og visuelt eiergodkjent; Brave er operativt deaktivert for ordinære Editor-sluttbrukere frem til sluttbrukeravtalegaten er dokumentert oppfylt

React-editoren støtter tenantvalg, rollebasert tilgang, aktører, personer, relasjoner, kontaktkanaler, søk, taksonomifiltrering og import/eksport-side.

Editoren har håndtering av ulagrede endringer og egne URL-er for oversikter og detaljvisninger.

## Implementert Aktørbilde-flyt bak featureflag

Når `IMAGE_ASSET_FEATURE_ENABLED=True` for et miljø, viser Organization-editoren seksjonen `Aktørbilde`. Kildereisen presenteres i denne prioriterte rekkefølgen:

1. `Finn bilder` fra aktørens offisielle nettside og Open Graph
2. Brave Image Search
3. direkte, innlimt bilde-URL
4. manuell opplasting av JPEG, PNG eller WebP

Alternative kilder blir synlige etter at den offisielle discoveryen er forsøkt. Redaktøren velger fortsatt ett konkret bilde og må eksplisitt prosessere og godkjenne det; discovery, søk, kandidat-preview, opplasting og processing kan ikke opprette eller erstatte en aktiv selection alene.

### Deterministisk og synlig Brave-søk

Det foreslåtte søket starter alltid med lagret aktørnavn. Nøyaktig én lagret kommune legges automatisk til; ingen eller flere kommuner gir ikke automatisk stedstillegg, og ved flere kommuner må redaktøren velge én eksplisitt. Kategori og aktivt tilknyttet person kan legges til med egne valg. Tags brukes aldri. Det brukes ingen AI til å bygge, utvide eller rangere søket.

Den eksakte søketeksten og hvilke CRM-kilder den bygger på vises før søk og kan redigeres manuelt. UI-et viser også hvilke tilgjengelige kilder som ikke er brukt. Kommune-, kategori- og personchips gjelder bare så lenge det deterministiske forslaget er urørt; ved første manuelle tekstendring nullstilles alle chips og ID-er. Backend avviser `query_edited=true` kombinert med et nonempty refinement og signerer da provenance kun som `manual_edit`, slik at ingen skjulte refinement-signaler påvirker lokal rangering. Backend sender den eksakte teksten til Brave med de eiergodkjente parameterne `country=NO`, `search_lang=nb`, `safesearch=strict`, `spellcheck=false` og `count=30`, og rangerer resultatene deterministisk med offisielt domene som sterkeste lokale signal. `nb` er godkjent fordi Braves offisielle `search_lang`-enum ikke støtter `no`.

Full providerrespons lagres aldri. Bare eksakt query og normaliserte nødvendige kandidatfelt bæres i kortlivede, bruker-/tenant-/aktørbundne signerte referanser; appen oppretter ingen kandidatmodell eller søkehistorikk. Dette følger begrensningen for lagring/caching i Braves standardvilkår, og valgt bilde må fortsatt rettighetsgodkjennes av redaktøren. Den lokale signed-refen varer omtrent 30 minutter, mens Brave opplyser at providerens standard query-logger kan beholdes i opptil 90 dager; Zero Data Retention krever Enterprise/egen avtale.

Nær søkefeltet opplyser Editor at søket utføres via Brave, at teksten kan lagres hos provider i opptil 90 dager og at sensitiv eller intern informasjon ikke skal skrives inn. Nær resultatene står den separate rettighetspåminnelsen om å kontrollere at bildet kan brukes. Braves gjeldende Terms punkt 4(c) krever at hver End User er bundet av en skriftlig avtale med Customer med forpliktelser vesentlig tilsvarende 3(b), og Customer har ansvar for nødvendige privacy notices/samtykker. Dette er en manuell operativ avtaleplikt, ikke en egen samtykkemotor i Editor. Staging returnerte historisk 30 ekte kandidater gjennom `search_lang=nb` uten å eksponere credentialen; credentialen er nå deaktivert, og ordinære Editor-sluttbrukere får ikke Brave før avtalegaten er dokumentert oppfylt.

### Processing, fokus og godkjenning

Redaktøren kan se servergenererte kandidatpreviews uten hotlinking, velge `Foto`/cover eller `Logo`/contain og prosessere bare det valgte bildet. Brave-gridet kan bruke providerens thumbnail for rask kandidatvisning. Når en fjernkandidat velges, henter klienten eksplisitt et privat preview med `original=true` fra den signerte originale bilde-URL-en; den samme signerte originalen brukes senere av serverprocessing. Foto forklares som en fyllende modus som kan beskjære, mens Logo viser hele motivet uten beskjæring.

Foto har fokusforvalgene Venstre/Midt/Høyre og Topp/Midt/Bunn som snarveier til samme presise X/Y-state som sliderne under den kollapsede `Finjuster utsnitt`. Zoom går fra 100 til 300 prosent; 100 prosent er maksimalt cover-utsnitt uten tom flate. Zoom betyr derfor innzooming og retur til standard cover-nivå, ikke zoom ut til tomme flater. `Tilbakestill utsnitt` setter sentrum/sentrum/100 prosent. Alle tre live-previewene bruker samme kantklampede coverberegning som serverprocessing per variant og oppdateres uten nettverkskall per slidersteg. Etter `Prosesser valgt bilde` er serverens faktiske `square`-, `landscape`- og `share`-renditions fasit før godkjenning. Logo bruker contain, viser et helt-motiv-preview og skjuler/avviser fokus og zoom. Prosjekteier har visuelt bekreftet denne Foto-/Logo- og zoomkontrakten samt samsvaret mellom live previews og serverprocessing.

Alt-tekst for en asset-selection er valgfri. Tom streng bevares som tom streng og erstattes ikke skjult med aktørnavnet; whitespace-only avvises. Eksplisitt systemfallback-selection beholder sitt separate krav om ikke-tom tekst. Offentlig kreditering er valgfri. Bare `Godkjenn og lås bilde` eller `Godkjenn og erstatt bilde` oppretter en aktiv `OrganizationImageSelection` og tilhørende event.

Et aktivt valg vises som `Aktivt bilde`, med revisjon separat, eventuell `Ingen alt-tekst` og tre interne previews. Tom tilstand heter `Ingen aktivt valgt bilde ennå.`; tekniske domenebegreper vises ikke til redaktøren. Expected-revision-konflikter og nettverks-, provider-, fetch- og processingfeil vises kontrollert på norsk. Den eksisterende `Public Preview (legacy)` er fortsatt separat; kandidatpreviewene og de interne renditions er ikke public projection eller offentlig publisert.

### Leveransestatus og gjenstående gater

Fase 3D.2-koden og den automatiserte testdekningen er merget til `main` med PR #33 som mergecommit `48f23f183dacb8331a64b86f1d7574250cbfbe02`; alle fem jobber i main-CI-run `31535260891` er grønne. Første versjon har teknisk stagingevidens for direkte URL, multipart-upload, private previews, blank alttekst og uendret PUBLIC. Precision/zoom-oppfølgingen er teknisk stagingverifisert med faktisk API-processing av presis X/Y og 150 % zoom samt tre private serverpreviews. Prosjekteiers visuelle retest er gjennomført og aksepterer vanlig/teknisk bildespråk, Foto/Logo-skillet, Logo uten cropkontroller, finjustering, zoomkontrakten, live/server-samsvar og blank alttekst. Brave live-søk, privat originalpreview, secure fetch og processing er historisk verifisert uten PUBLIC- eller public-releaseendring. Credentialen er deretter deaktivert som operativ avtalegate. Featureflaggets kode-default er fortsatt avslått. Se [datert stagingevidens](../status/STAGING_IMAGE_SOURCES_2026-08-11.md).

Historikk-/restore-UI, takedown, permanent kandidatlagring, public release/materialisering, public projection og PUBLIC-bildebruk er ikke implementert av 3D.2.

## Implementert kontaktopplevelse

Editor CRM er intern og viser kontaktinformasjon også når `PersonContact.is_public=False`.

På personens redigeringsside kan redaktøren:

- se primær e-post og telefon i kompatibilitetsfeltene `Person.email` og `Person.phone`
- se alle lagrede `PersonContact` for personen
- se hvilke kontakter som er primære
- endre kontaktverdi
- styre `is_primary`
- styre `is_public` med teksten `Kan vises offentlig` og en presisering om at
  kontaktkanalen bare vises på aktører der `Vis person offentlig` også er valgt

Organization-, Person- og PHONE-kontaktskjemaene har et synlig
land-/regionvalg. Tenantens nullable default forhåndsvelges når den finnes,
men kan overstyres per telefon. `+`-numre trenger ikke region og tømmer valget
i Editor. Nasjonale numre uten region og ugyldige numre blokkeres av backend
med norsk feltfeil. Original skrivemåte beholdes i Editor/PUBLIC. Klikkbare
telefoner bruker et servergenerert `tel:`-mål fra canonical identitet; mangler
denne, vises råverdien uten telefonlenke. Lagring av et annet felt normaliserer
ikke en uendret legacytelefon.

Import-/eksportsiden har et eget synlig regionvalg når importjobben opprettes.
Tenantdefaulten forhåndsvelges, «ingen region» kan velges eksplisitt, og den
frosne jobbregionen vises i reviewflaten. Valget er kontekst for
normalisering, ikke del av telefonidentiteten.

På aktørsiden skilles personpublisering fra kontaktpublisering:

- `Vis person offentlig` / `publish_person` styrer om personen vises offentlig for aktøren
- `PersonContact.is_public` styrer om e-post eller telefon vises i PUBLIC
- aktøroversikten holder hovedkortene kompakte og viser ikke Organization-
  telefon; telefonen finnes fortsatt i oversiktsmodal, redigering og søk
- Organization-telefonen vises i oversiktsmodal også når
  `publish_phone=False`; statusen merkes separat som `Offentlig` eller
  `Kun intern`
- utenlandske telefoner skrevet i nasjonalt format kan vise et dempet,
  backend-avledet landkodehint etter råverdien, for eksempel
  `070 123 45 67 (+46)`; eksplisitte `+`-verdier får ikke dobbelt hint, og
  dialmålet er fortsatt canonical E.164
- knappen fra en aktør–person-kobling til personredigeringen heter `Rediger`
- hver aktør–person-kobling viser effektiv PUBLIC-status for alle fire
  kombinasjoner av `publish_person` og offentlige/ikke-offentlige
  kontaktkanaler, uten å koble eller omskrive de to flaggene

Alle nye publiseringsvalg starter avslått:

- ny persons e-postadresse er intern
- nytt telefonnummer er internt
- ny person vises ikke offentlig som kontaktperson
- kobling av en eksisterende person publiserer ikke personen

Editor-tekstene skiller mellom å vise personen som kontaktperson på aktørsiden og å gjøre den konkrete e-postadressen eller telefonen offentlig. Personen kan være offentlig uten kontaktkanaler, og en offentligmarkert kontaktkanal forblir skjult på aktører der personen er skjult. Eksisterende lagrede publiseringsvalg endres ikke av disse standardene.

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
