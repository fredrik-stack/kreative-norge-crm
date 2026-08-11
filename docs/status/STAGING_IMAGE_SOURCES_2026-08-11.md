# Fase 3D.2 – stagingverifisering 2026-08-11

**Status:** fase 3D.2 med precision/zoom er fullverifisert lokalt, CI-grønn, teknisk stagingverifisert, live Brave-verifisert og visuelt eiergodkjent. Direkte URL, multipart-upload, private previews, processing, valgfri alttekst, storage og PUBLIC-regresjon er grønne. Etter live-verifikasjonen ble Brave-credentialen med hensikt deaktivert; historisk live-status er **PASS**, mens dagens operative stagingstatus er **NOT ACTIVE** frem til sluttbrukeravtalegaten er dokumentert oppfylt. Draft-PR #33 venter på ny uavhengig sluttreview; ingen merge eller produksjonssetting er utført.

## Leveransegrunnlag

- branch: `feature/phase3d2-image-sources-ux`
- første 3D.2-runtimecommit: `971a9c0e13783ab57a49782d3e131cf988c917f1`
- deployet precision/zoom-runtimecommit: `3686f08006a1396fd1e2ce250603044c4b62e041`
- draft-PR: [#33](https://github.com/fredrik-stack/kreative-norge-crm/pull/33)
- første GitHub Actions-run: [31441538397](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/31441538397), alle fem jobber grønne
- precision/zoom GitHub Actions-run: [31471806873](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/31471806873), alle fem jobber grønne
- sluttreview-baseline GitHub Actions-run: [31520955798](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/31520955798), alle fem jobber grønne på PR-head `964a97d89f5489aeaff26cb822b2753c76b40d6e`
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

Brave-kallet i den første stagingreisen returnerte kontrollert `503` med `brave_not_configured`. Det dokumenterer pre-credential-baselinen. Prosjekteier godkjente senere providerparametrene og privacy-/rettighetscopyen, og credentialen ble deretter installert bare server-side før den endelige live-gaten. Gaten nedenfor dokumenterer historisk live-verifikasjon, ikke dagens operative aktivering.

## Prosjekteiers visuelle oppfølging og bestilt retting

Prosjekteier bekreftet etter første deploy at official discovery, direkte URL, upload, private previews, fokusforvalg, blank alttekst og uendret PUBLIC fungerer visuelt. Testen avdekket at teknisk tomtilstandstekst måtte erstattes, og at de ni fokusforvalgene var for grove. Oppfølgingen på samme draft-PR implementerer derfor vanlig språk, tydelig Foto/Logo-forskjell, presis X/Y, 100–300 % Foto-zoom, reset og felles live/server-cropgeometri. Additiv migrasjon `0028` gir eksisterende rendition-sett zoom `1.0000`.

## Precision/zoom-deploy og teknisk gate

Før oppfølgingsdeployen var serverrepoet rent på `34f6f35`, database/API/web var `Up`, backup-/verify-timerne var aktive og siste backupstatus grønn. Før-migrasjonstilstanden var 127 aktører, 122 publiserte, 4 assets, 6 rendition-sett, 18 renditions, 5 aktive selections, 6 review-events, 0 public releases og 4/18 faktiske original-/renditionfiler.

Den obligatoriske ferske Borg-backupen fullførte med `Result=success`, dump- og repositoryverifikasjon `passed` og arkivnavn `kreative-norge-staging-20260811T081243Z`. Repoet ble fast-forwardet til eksakt `3686f08006a1396fd1e2ce250603044c4b62e041`, og API-/web-images ble bygget grønt. På grunn av den kjente Compose 1.29.2-risikoen ble bare API stoppet/fjernet/opprettet først; database, web, volum og media ble ikke berørt. API-loggen viste `Applying crm.0028_image_rendition_zoom... OK`, Django-check var grønn, alle migrasjoner gjennom `0028` var anvendt og Gunicorn startet tre workers. Deretter ble bare web stoppet/fjernet/opprettet.

Alle seks historiske rendition-sett hadde etter migrasjonen zoom `1.0000`, og de fem aktive asset-selectionene var lesbare. Featureflagget var fortsatt `True`; Brave runtime rapporterte på dette tidspunktet bare `missing`, aldri credentialverdien. Den senere sluttgaten nedenfor bekreftet `configured` på samme boolske måte.

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

Lokal origin med korrekte proxyheadere svarte `200` for `/`, `/api/auth/session/` og `/public/actors/`. Det deployede JS-bundlet inneholdt `Finjuster utsnitt` og `Ingen aktivt valgt bilde ennå.`, men ingen `BRAVE_IMAGE_SEARCH_API_KEY`- eller `X-Subscription-Token`-markør. Ekstern server-side curl traff `HTTP 403` med `cf-mitigated: challenge`, altså en eksplisitt Cloudflare-browserchallenge. Ingen kontrollert in-app- eller ekstern nettleser var tilgjengelig i den tekniske deployøkten. Prosjekteier har senere gjennomført den vanlige browser-smoken og den visuelle retesten; denne eierverifiseringen holdes eksplisitt adskilt fra Codex-harnessen.

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

## Endelig Brave live-gate

Sluttkontrollen kjørte på rent stagingrepo med eksakt PR-head `209b44b060db759d356e334cc288ee4e3e5cfde1`; database, API og web var `Up`. Credentialen ble aldri lest eller skrevet ut. Django rapporterte bare:

```text
brave_configured=True
image_feature_enabled=True
```

Den eksisterende aktøren `Festspillene Helgeland` ga det deterministiske forslaget `Festspillene Helgeland VEFSN` med querykildene `organization_name,municipality`. Det deployede providerkallet brukte den eiergodkjente faste `search_lang=nb`-parameteren og returnerte `200` med 30 ekte kandidater. Første kandidat gjennomførte:

```text
privat originalpreview image/webp, private/no-store
secure fetch og Foto-processing 200
square image/webp private/no-store
landscape image/webp private/no-store
share image/jpeg private/no-store
```

Den dedikerte Codex-testaktørens mer kunstige forslag returnerte også ekte resultater og flere grønne originalpreviews, men kildene var for små for alle obligatoriske Foto-renditions og ble kontrollert avvist med `upscale_required`. Det bekrefter at no-upscale-kvalitetsvernet fortsatt gjelder; den egnede Festspillene-aktøren fullførte processing på første kandidat.

Kontrollen stoppet før approval. Deltaet var derfor +1 privat asset, +1 immutable rendition-sett og +3 interne renditions, men 0 selections, 0 review-events, 0 publiserte aktører og 0 public releases. `Festspillene Helgeland` beholdt sin eksisterende publiseringsstatus, det globale publiserte antallet var fortsatt 122 og public releases var fortsatt 0. Etterpå rapporterte orphan-dry-run 8/8 refererte private originaler, 33/33 refererte interne renditions, 0 eligible orphans, 0 unge urefererte filer og 0 slettinger.

## Operativ deaktivering etter live-verifikasjon

Etter at live-evidensen var kontrollert og lagret, ble `BRAVE_IMAGE_SEARCH_API_KEY` satt tilbake til tom verdi i serverens ignorerte `.env.staging`. Credentialverdien ble aldri lest eller skrevet ut. Bare API-containeren ble stoppet, fjernet og opprettet med `--no-deps`; database, web, volum og media ble ikke rekreert. Etterpå var database, API og web fortsatt `Up`, Django system check var grønn, serverrepoet var rent, og de boolske/kontrollerte probene rapporterte:

```text
brave_configured=False
brave_probe_code=brave_not_configured
```

Dermed er statusen eksplisitt todelt:

- **LIVE VERIFIED: PASS** – 30 ekte kandidater, privat originalpreview, secure fetch, processing og private renditions er historisk verifisert.
- **CURRENTLY ACTIVE: NOT ACTIVE** – ordinære Editor-sluttbrukere skal ikke få Brave aktivert før den manuelle sluttbrukeravtalegaten er dokumentert oppfylt.

Braves gjeldende [Search API Terms of Use](https://api-dashboard.search.brave.com/documentation/resources/terms-of-service) punkt 4(c) krever at hver End User er bundet av en skriftlig avtale med Customer med forpliktelser vesentlig tilsvarende punkt 3(b), og legger ansvaret for nødvendige privacy notices/samtykker på Customer. Se også Braves [Privacy Policy](https://api-dashboard.search.brave.com/privacy-policy). Prosjektet påstår ikke at denne gaten er oppfylt. Det skal ikke bygges en consent-, terms- eller brukeravtalemotor i PR #33; senere valg mellom eksisterende arbeids-/oppdragsvilkår, egne Editor-vilkår eller eksplisitt digital aksept er en separat beslutning.

## Gjennomført visuell eiergate

Prosjekteier har gjennom vanlig browser-smoke bekreftet:

- vanlig og teknisk bildespråk oppleves riktig, og Foto/Logo-skillet er logisk
- Logo viser hele motivet og har med vilje ingen crop-, fokus- eller zoomkontroller
- finjustering og zoom fungerer i praksis; Foto-zoom betyr innzooming og retur til standard cover-nivå, aldri zoom ut til tomme flater
- live previews og serverprocessing oppleves som samsvarende
- blank alttekst er akseptert uten skjult navnefallback
- under den historiske live-testen ble `Brave konfigurert: True` vist, `Søk etter flere bilder` returnerte ekte resultater, og den tidligere ikke-konfigurert-feilen var borte
- privacy- og rettighetscopyen samt aktiv bruk av `search_lang=nb` er godkjent
- PUBLIC og legacybildene er uendret, og ingen public release er opprettet

Den kontrollerte nettleserflaten var ikke tilgjengelig i evidensøkten som oppdaterte denne rapporten. De synlige observasjonene ovenfor er derfor prosjekteiers evidens; den separate tekniske harnessen bekreftet live provider, privat preview, secure fetch, processing og null PUBLIC-/release-delta uavhengig.

Ingen produksjonssetting eller merge er utført.
