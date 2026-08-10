# Editor

**Status:** implementert grunnløsning; fase 2-standarder for kontaktpublisering implementert; fase 3D.1 offisiell bildekandidatflyt teknisk aktivert og visuelt godkjent i staging; fase 3D.2 er implementert og lokalt backendtestet på aktiv featurebranch, men er ikke CI-, staging- eller eiergodkjent

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

Den eksakte søketeksten og hvilke CRM-kilder den bygger på vises før søk og kan redigeres manuelt. UI-et viser også hvilke tilgjengelige kilder som ikke er brukt. Kommune-, kategori- og personchips gjelder bare så lenge det deterministiske forslaget er urørt; ved første manuelle tekstendring nullstilles alle chips og ID-er. Backend avviser `query_edited=true` kombinert med et nonempty refinement og signerer da provenance kun som `manual_edit`, slik at ingen skjulte refinement-signaler påvirker lokal rangering. Backend sender den eksakte teksten til Brave med `country=NO`, `search_lang=nb`, `safesearch=strict`, `spellcheck=false` og `count=30`, og rangerer resultatene deterministisk med offisielt domene som sterkeste lokale signal. `nb` er bevisst valgt fordi Braves offisielle `search_lang`-enum ikke støtter `no`.

Full providerrespons lagres aldri. Bare eksakt query og normaliserte nødvendige kandidatfelt bæres i kortlivede, bruker-/tenant-/aktørbundne signerte referanser; appen oppretter ingen kandidatmodell eller søkehistorikk. Dette følger begrensningen for lagring/caching i Braves standardvilkår, og valgt bilde må fortsatt rettighetsgodkjennes av redaktøren. Den lokale signed-refen varer omtrent 30 minutter, mens Brave opplyser at providerens standard query-logger kan beholdes i opptil 90 dager; Zero Data Retention krever Enterprise/egen avtale.

Brave-kontrollen skal forbli uten servernøkkel frem til prosjekteier eller annen avtaleeier har dokumentert hvordan redaktørene omfattes av standardvilkårenes punkt 4(c), samt hvilke personvernvarsler eller samtykker som kreves når søket kan inneholde personnavn eller manuelt skrevet tekst. Dette er en aktiveringsgate, ikke en ny automatisk godkjenningsmekanisme i Editor.

### Processing, fokus og godkjenning

Redaktøren kan se servergenererte kandidatpreviews uten hotlinking, velge `Foto`/cover eller `Logo`/contain og prosessere bare det valgte bildet. Brave-gridet kan bruke providerens thumbnail for rask kandidatvisning. Når en fjernkandidat velges, henter klienten eksplisitt et privat preview med `original=true` fra den signerte originale bilde-URL-en; den samme signerte originalen brukes senere av serverprocessing. Foto har fokusforvalgene Venstre/Midt/Høyre og Topp/Midt/Bunn med sentrum som standard. Den umiddelbare crop-previewen av originalen i klienten er veiledende. Etter `Prosesser valgt bilde` er serverens faktiske `square`-, `landscape`- og `share`-renditions fasit før godkjenning. Logo bruker contain og har ikke fokuskontroller.

Alt-tekst for en asset-selection er valgfri. Tom streng bevares som tom streng og erstattes ikke skjult med aktørnavnet; whitespace-only avvises. Eksplisitt systemfallback-selection beholder sitt separate krav om ikke-tom tekst. Offentlig kreditering er valgfri. Bare `Godkjenn og lås bilde` eller `Godkjenn og erstatt bilde` oppretter en aktiv `OrganizationImageSelection` og tilhørende event.

Aktiv selection vises med revisjon, eventuell `Ingen alt-tekst` og tre interne previews. Expected-revision-konflikter og nettverks-, provider-, fetch- og processingfeil vises kontrollert på norsk. Den eksisterende `Public Preview (legacy)` er fortsatt separat; kandidatpreviewene og de interne renditions er ikke public projection eller offentlig publisert.

### Leveransestatus og gjenstående gater

Fase 3D.2-koden og automatisert testdekning finnes på aktiv featurebranch. Fase 3D.1 er tidligere teknisk og visuelt verifisert i staging, men fase 3D.2 er ennå ikke verifisert i CI eller staging og er ikke visuelt godkjent av prosjekteier. Featureflaggets kode-default er fortsatt avslått.

Historikk-/restore-UI, takedown, permanent kandidatlagring, public release/materialisering, public projection og PUBLIC-bildebruk er ikke implementert av 3D.2.

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
