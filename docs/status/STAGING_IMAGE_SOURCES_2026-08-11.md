# Fase 3D.2 – stagingverifisering 2026-08-11

**Status:** første tekniske stagingverifisering er gjennomført for direkte URL, multipart-upload, private previews, processing, valgfri alttekst, storage og PUBLIC-regresjon. Prosjekteiers påfølgende visuelle test godkjente grunnreisen og bestilte presis fokus/zoom. Oppfølgingen er nå fullverifisert lokalt, CI-grønn og teknisk stagingverifisert; visuell eierretest gjenstår. Brave-parametere/copy er godkjent, men live-søk venter på servercredential.

## Leveransegrunnlag

- branch: `feature/phase3d2-image-sources-ux`
- første 3D.2-runtimecommit: `971a9c0e13783ab57a49782d3e131cf988c917f1`
- deployet precision/zoom-runtimecommit: `3686f08006a1396fd1e2ce250603044c4b62e041`
- draft-PR: [#33](https://github.com/fredrik-stack/kreative-norge-crm/pull/33)
- første GitHub Actions-run: [31441538397](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/31441538397), alle fem jobber grønne
- precision/zoom GitHub Actions-run: [31471806873](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/31471806873), alle fem jobber grønne
- precision/zoom lokal verifikasjon: 372 backendtester på ren database migrert gjennom `0028`, 28 frontendtester, 11 Playwright-tester, 4 stagingkontrakttester, 68 backuptester, frontendproduksjonsbygg og begge produksjonscontainerbygg

## Pre-deploy-gater

Stagingrepoet var rent på tidligere fase 3D.1-commit `e60fe6f`. `IMAGE_ASSET_FEATURE_ENABLED=True`, mens `BRAVE_IMAGE_SEARCH_API_KEY` var tom. Før deploy ble Borg-arkivet `kreative-norge-staging-20260810T231815Z` fullført 2026-08-10 23:18 UTC / 2026-08-11 01:18 CEST med `Result=success` og `ExecMainStatus=0`.

Baseline før deploy var:

| Kontroll | Før |
| --- | ---: |
| Organisasjoner | 126 |
| Publiserte organisasjoner | 122 |
| Image assets | 4 |
| Renditions | 12 |
| Aktive selections | 4 |
| Review-events | 4 |
| Public releases | 0 |
| Private originalfiler | 4 |
| Interne renditionfiler | 12 |

## Deploy og Compose-avvik

Begge imagebyggene fullførte på serveren. Ordinær `docker-compose up -d --build` traff deretter serverens kjente Docker Compose 1.29.2-feil `KeyError: 'ContainerConfig'` mens Compose forsøkte å rekreere databasecontaineren. Den eksisterende databasecontaineren var stoppet med exit 0, men ikke slettet eller gjenskapt.

Kjøringen ble stoppet og avgrenset slik:

1. Den samme eksisterende databasecontaineren ble startet igjen; `pg_isready` bekreftet at PostgreSQL aksepterte forbindelser.
2. Lokal origin svarte `200` for session og PUBLIC, og eksisterende API-container bestod `manage.py check`.
3. Bare API-containeren ble stoppet, fjernet og opprettet fra nytt image. Database, web, volum og media ble ikke berørt.
4. Migrasjon `0027_optional_image_alt_text` ble anvendt, alle migrasjoner gjennom `0027` var markert anvendt, Gunicorn startet tre workers og Django-check var grønn.
5. Bare web-containeren ble deretter stoppet, fjernet og opprettet fra nytt image. Nginx lastet `client_max_body_size 16m`.

Etterpå var database, API og web `Up`. Ekstern HTTPS svarte `200` for `/`, `/api/auth/session/` og `/public/actors/`.

## Faktisk stagingreise

Verifikasjonen brukte en dedikert, upublisert aktør i tenant `musikkontoretnord`:

- navn: `Codex stagingtest 3D.2 2026-08-11`
- Organization-ID: `195`
- `is_published=False` og `publish_phone=False`
- aktiv selection etter testen: revisjon 2, upload-proveniens og eksakt tom alttekst

Den deterministiske standardqueryen var eksakt:

```text
Codex stagingtest 3D.2 2026-08-11 Bodø
```

Querykildene var eksakt `organization_name,municipality`. Dette bekrefter hovedregelen om lagret aktørnavn som basis og automatisk kommune bare når nøyaktig én kommune finnes. Automatiserte backend-/frontendtester dekker i tillegg flere kommuner uten default, eksplisitt kategori/person, aldri tags eller AI, og at første manuelle tekstendring nullstiller alle strukturerte refinements og gir bare `manual_edit`-proveniens.

Brave-kallet returnerte kontrollert `503` med `brave_not_configured`. Live providerrespons er derfor ikke verifisert. Prosjekteier har senere godkjent providerparametrene og privacy-/rettighetscopyen. En ny sikker kontroll fant fortsatt ingen credential lokalt eller i staging-runtime; en gyldig nøkkel må installeres server-side før live-test. Avtaleeier må samtidig sikre skriftlige sluttbrukerforpliktelser etter gjeldende standardvilkår punkt 3(b).

## Prosjekteiers visuelle oppfølging og bestilt retting

Prosjekteier bekreftet etter første deploy at official discovery, direkte URL, upload, private previews, fokusforvalg, blank alttekst og uendret PUBLIC fungerer visuelt. Testen avdekket at teknisk tomtilstandstekst måtte erstattes, og at de ni fokusforvalgene var for grove. Oppfølgingen på samme draft-PR implementerer derfor vanlig språk, tydelig Foto/Logo-forskjell, presis X/Y, 100–300 % Foto-zoom, reset og felles live/server-cropgeometri. Additiv migrasjon `0028` gir eksisterende rendition-sett zoom `1.0000`.

## Precision/zoom-deploy og teknisk gate

Før oppfølgingsdeployen var serverrepoet rent på `34f6f35`, database/API/web var `Up`, backup-/verify-timerne var aktive og siste backupstatus grønn. Før-migrasjonstilstanden var 127 aktører, 122 publiserte, 4 assets, 6 rendition-sett, 18 renditions, 5 aktive selections, 6 review-events, 0 public releases og 4/18 faktiske original-/renditionfiler.

Den obligatoriske ferske Borg-backupen fullførte med `Result=success`, dump- og repositoryverifikasjon `passed` og arkivnavn `kreative-norge-staging-20260811T081243Z`. Repoet ble fast-forwardet til eksakt `3686f08006a1396fd1e2ce250603044c4b62e041`, og API-/web-images ble bygget grønt. På grunn av den kjente Compose 1.29.2-risikoen ble bare API stoppet/fjernet/opprettet først; database, web, volum og media ble ikke berørt. API-loggen viste `Applying crm.0028_image_rendition_zoom... OK`, Django-check var grønn, alle migrasjoner gjennom `0028` var anvendt og Gunicorn startet tre workers. Deretter ble bare web stoppet/fjernet/opprettet.

Alle seks historiske rendition-sett hadde etter migrasjonen zoom `1.0000`, og de fem aktive asset-selectionene var lesbare. Featureflagget var fortsatt `True`; Brave runtime rapporterte bare `missing`, aldri credentialverdien.

Den tekniske produktreisen brukte den eksisterende upubliserte testaktøren og eksisterende rettighetsavklarte private kildebytes. Første testharnessforsøk ble avvist før behandling fordi Django-testklienten brukte den ikke-tillatte standardhosten `testserver`; ny kjøring med faktisk staginghost gikk gjennom den virkelige multipart-API-ruten:

```text
upload-process
→ Foto / cover
→ focus_x=0.3700
→ focus_y=0.6800
→ zoom=1.5000
→ square 200 image/webp private,no-store
→ landscape 200 image/webp private,no-store
→ share 200 image/jpeg private,no-store
```

Processingstatus var `created`. Testen godkjente eller publiserte ikke bildet. Delta var derfor nøyaktig +1 immutable rendition-sett, +3 interne renditions, 0 selections, 0 review-events og 0 public releases; aktørens `is_published=False` og `publish_phone=False` forble uendret. Sluttilstanden var 4 assets, 7 rendition-sett, 21 renditions, 5 aktive selections, 6 review-events, 0 public releases og fortsatt 122 publiserte aktører.

Alle 4 originaler og 21 renditions fantes og matchet lagret SHA-256. Orphan-dry-run rapporterte 4/4 og 21/21 refererte/faktiske filer, 0 eligible orphans, 0 unge urefererte filer og 0 slettinger. API/web/database var `Up` med 0 restarter; bare API hadde de to skrivbare mediamountene, mens web ikke hadde mediamount.

Lokal origin med korrekte proxyheadere svarte `200` for `/`, `/api/auth/session/` og `/public/actors/`. Det deployede JS-bundlet inneholdt `Finjuster utsnitt` og `Ingen aktivt valgt bilde ennå.`, men ingen `BRAVE_IMAGE_SEARCH_API_KEY`- eller `X-Subscription-Token`-markør. Ekstern server-side curl traff `HTTP 403` med `cf-mitigated: challenge`, altså en eksplisitt Cloudflare-browserchallenge. Ingen kontrollert in-app- eller ekstern nettleser var tilgjengelig i økten. Ekstern HTTPS/browser-smoke og all visuell vurdering er derfor en eksplisitt del av prosjekteiers retest, ikke feilaktig rapportert som automatisert grønn.

Direkte URL-flyten gjennomførte:

- signert URL-kandidat
- privat/no-store originalpreview som WebP
- sikker server-fetch og processing med `focus_x=0`, `focus_y=1`
- private/no-store previews av `square` og `landscape` som WebP og `share` som JPEG
- first lock med eksakt tom alttekst, revisjon 1 og `pasted_url`-proveniens

Multipart-upload brukte de samme allerede godkjente kildebytene og gjennomførte:

- faktisk multipart `upload-process`
- processing med `focus_x=1`, `focus_y=0`
- de samme tre private/no-store previewvariantene
- eksplisitt replacement med eksakt tom alttekst, revisjon 2 og `upload`-proveniens uten source-URL

Ingest gjenbrukte det eksisterende identiske assetet, slik at assetdelta var 0. De to ulike fokussettene opprettet 6 nye interne renditions og 2 nye review-events. Ingen handling opprettet en public release eller endret aktørens publiseringsflagg.

## Første 3D.2-sluttilstand

| Kontroll | Før | Etter |
| --- | ---: | ---: |
| Organisasjoner | 126 | 127 |
| Publiserte organisasjoner | 122 | 122 |
| Image assets | 4 | 4 |
| Renditions | 12 | 18 |
| Aktive selections | 4 | 5 |
| Review-events | 4 | 6 |
| Public releases | 0 | 0 |
| Private originalfiler | 4 | 4 |
| Interne renditionfiler | 12 | 18 |

Orphan-cleanup ble kjørt i dry-run. Begge storagealiasene hadde nøyaktig like mange DB-refererte filer som faktiske filer, 0 eligible orphans, 0 unge urefererte filer og 0 slettinger.

## Gjenstående eiergater

Prosjekteier skal teste [staging](https://staging.northernsound.no/) slik:

1. Åpne staging i en vanlig nettleser og fullfør eventuell Cloudflare-challenge. Kontroller at Editor, session og PUBLIC åpner normalt; automatisert server-side HTTPS-curl kunne ikke passere challengen, mens lokal origin var grønn.
2. Logg inn, velg tenant `musikkontoretnord`, åpne Aktører og finn `Codex stagingtest 3D.2 2026-08-11`. Kontroller at aktøren er upublisert, at aktivt bilde viser revisjon 2 og `Ingen alt-tekst`, og at tomtilstanden andre steder bruker `Ingen aktivt valgt bilde ennå.` – aldri «selection».
3. Trykk `Finn bilder`. Alternative kilder skal vises i rekkefølgen Brave, direkte URL og upload.
4. Åpne Brave-kilden. Kontroller privacyteksten ved queryen og rettighetsteksten ved resultatområdet. Standardqueryen skal være synlig som `Codex stagingtest 3D.2 2026-08-11 Bodø`. Prøv manuelt `Festspillene Helgeland logo`; fordi credential mangler skal kontrollert norsk ikke-konfigurert-feil vises. Dette er ikke en live-providerverifikasjon, og ingen nøkkel skal legges inn i UI.
5. Åpne direkte URL og lim inn en rettighetsavklart, direkte JPEG-/PNG-/WebP-URL. Kandidaten skal ikke bli valgbart galleriinnhold før privat originalpreview er hentet og validert. Gjenta senere med `Last opp bilde` og en statisk fil under 15 MiB; en større fil skal gi den norske 15 MB-meldingen.
6. Velg `Foto`. Kontroller forklaringsteksten, klikk Venstre/Midt/Høyre og Topp/Midt/Bunn og se at alle tre live-previewene endres. Åpne `Finjuster utsnitt`, flytt presis X og Y med mus og tastatur, zoom inn, zoom tilbake mot 100 %, og kontroller at Kvadrat, Landskap og Deling følger alle endringer uten nettverksventing.
7. Trykk `Tilbakestill utsnitt` og kontroller Midt/Midt/100 %. Sett deretter et tydelig presist utsnitt og trykk `Prosesser valgt bilde`. Sammenlign serverens faktiske tre previews med det siste live-utsnittet; de skal visuelt samsvare.
8. Velg `Logo`. Kontroller teksten `Logo viser hele motivet uten beskjæring.`, at hele logoen vises, og at presets, `Finjuster utsnitt` og zoom ikke vises.
9. La alttekst stå tom. `Godkjenn og erstatt bilde` skal være aktiv uten skjult navnefallback. Godkjenn bare en rettighetsavklart kilde og bare dersom en ny testrevisjon er ønsket; reload skal beholde aktivt bilde og tom alttekst.
10. Åpne [PUBLIC-oversikten](https://staging.northernsound.no/public/actors/) og kontroller at testaktøren ikke vises, at eksisterende legacybilder er uendret, og at ingen intern rendition er offentlig tilgjengelig. `search_lang=nb` er eiergodkjent; før en servernøkkel installeres skal avtaleeier sikre de skriftlige redaktørforpliktelsene i gjeldende standardvilkår punkt 3(b).

Ingen produksjonssetting eller merge er utført.
