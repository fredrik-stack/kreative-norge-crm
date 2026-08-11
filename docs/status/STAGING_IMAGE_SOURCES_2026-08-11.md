# Fase 3D.2 – stagingverifisering 2026-08-11

**Status:** første tekniske stagingverifisering er gjennomført for direkte URL, multipart-upload, private previews, processing, valgfri alttekst, storage og PUBLIC-regresjon. Prosjekteiers påfølgende visuelle test godkjente grunnreisen og bestilte presis fokus/zoom; oppfølgingen venter på ny stagingdeploy og visuell retest. Brave-parametere/copy er godkjent, men live-søk venter på servercredential.

## Leveransegrunnlag

- branch: `feature/phase3d2-image-sources-ux`
- deployet commit: `971a9c0e13783ab57a49782d3e131cf988c917f1`
- draft-PR: [#33](https://github.com/fredrik-stack/kreative-norge-crm/pull/33)
- GitHub Actions: [run 31441538397](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/31441538397), alle fem jobber grønne
- lokal verifikasjon før push: 365 backendtester, 22 frontendtester, 10 Playwright-tester, 4 stagingkontrakttester, 68 backuptester, produksjonsbygg og begge produksjonscontainerbygg

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

Prosjekteier bekreftet etter første deploy at official discovery, direkte URL, upload, private previews, fokusforvalg, blank alttekst og uendret PUBLIC fungerer visuelt. Testen avdekket at teknisk tomtilstandstekst måtte erstattes, og at de ni fokusforvalgene var for grove. Oppfølgingen på samme draft-PR implementerer derfor vanlig språk, tydelig Foto/Logo-forskjell, presis X/Y, 100–300 % Foto-zoom, reset og felles live/server-cropgeometri. Additiv migrasjon `0028` gir eksisterende rendition-sett zoom `1.0000`. Ny backup, deploy, teknisk staginggate og visuell eierretest dokumenteres i dette dokumentet når de faktisk er utført.

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

## Sluttilstand

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

1. Logg inn, velg tenant `musikkontoretnord`, åpne Aktører og finn `Codex stagingtest 3D.2 2026-08-11`.
2. Kontroller at aktøren er upublisert og at aktivt bilde viser revisjon 2 og `Ingen alt-tekst`.
3. Trykk `Finn bilder`. Etter forsøket skal alternative kilder vises i rekkefølgen Brave, direkte URL og upload.
4. Åpne Brave-kilden. Kontroller den synlige queryen `Codex stagingtest 3D.2 2026-08-11 Bodø`, at kildene vises, og at søk gir den norske meldingen om at bildesøk ikke er konfigurert. Ikke legg inn provider-nøkkel.
5. Åpne direkte URL og lim inn en rettighetsavklart, direkte JPEG-/PNG-/WebP-URL. Kandidaten skal ikke bli valgbart galleriinnhold før privat originalpreview er hentet og validert.
6. Velg kandidaten som `Foto`. Klikk Venstre/Midt/Høyre og Topp/Midt/Bunn og kontroller at alle tre live crop-previewene endres umiddelbart. Dette er den visuelle gaten som ikke kunne kjøres automatisk i stagingøkten fordi nettleserkontroll ikke var tilgjengelig.
7. Trykk `Prosesser valgt bilde` og kontroller serverens faktiske Kvadrat-, Landskap- og Deling-preview. La alttekst stå tom. `Godkjenn og erstatt bilde` skal være aktiv uten skjult navnefallback. Godkjenn bare dersom du ønsker en ny testrevisjon.
8. Gjenta med `Last opp bilde` og en statisk JPEG, PNG eller WebP under 15 MiB. Kontroller samme fokus- og previewreise. En fil over grensen skal gi den norske meldingen om maks 15 MB.
9. Åpne [PUBLIC-oversikten](https://staging.northernsound.no/public/actors/) og kontroller at den nye testaktøren ikke vises, at eksisterende legacybilder er uendret, og at ingen ny intern rendition er offentlig tilgjengelig.
10. `search_lang=nb` er eiergodkjent fordi Braves offisielle enum støtter `nb`, men ikke `no`. Før en nøkkel installeres skal avtaleeier sikre de skriftlige redaktørforpliktelsene som følger av gjeldende standardvilkår punkt 3(b).

Ingen produksjonssetting eller merge er utført.
