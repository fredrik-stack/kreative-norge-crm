# API

**Status:** implementert grunn-API; 3E.2 public image projection/API shadow er `CLOSED / SHADOW VERIFIED`; 3E.3-targetschemaet er `CLOSED / ACTIVE` i staging; 3E.4-takedownaction er `CLOSED / ACTIVE` i staging med kode-/eksempelstandard fortsatt av; 3F legacy-/Import-kontrakten er `CLOSED / VERIFIED` med Import-gaten av i shared staging; fase 4 API-/Editor-/Import-telefonkontrakt, kontrollert backfill og siste additive read-only UI-polish er teknisk stagingverifisert og `READY_FOR_OWNER_SMOKE`

API-et omfatter autentisering, tenants, taksonomi, aktører, personer, koblinger, kontaktkanaler, interne bildekandidathandlinger, public actors, importjobber og eksportjobber.

Tenant-scope Editor-API returnerer både interne og offentlige `PersonContact` for autoriserte brukere.

Ordinære interne telefonwrites på Organization, Person og PHONE-
`PersonContact` tar et eksplisitt `phone_region`-kontekstfelt. Nasjonale numre
uten region avvises kontrollert; internasjonale `+`-numre er regionuavhengige.
Intern respons kan returnere `phone_region_used`, et read-only
`phone_dial_uri` og et read-only `phone_country_calling_code_hint` for
Organization, Person og PHONE-`PersonContact`. Dialfeltet bygges server-side
som `tel:<E.164>` når lagret canonical identitet finnes. Landkodehintet bygges
server-side fra libphonenumbers-regionmetadata og returneres bare når den
lagrede normaliseringsregionen er kjent og forskjellig fra tenantens
defaultregion. Manglende/ukjent region eller samme region gir `null`.
Råverdien er fortsatt visningsverdien, canonical databasefelt serialiseres
ikke, og klienten trenger ingen egen landkodetabell. Personens readfelt utledes
fra autoritativ primær PHONE-`PersonContact`. Manglende canonical identitet gir
`null` dialmål, ikke en gjetning fra råverdien. `Tenant.default_phone_region`
er read-only i intern tenantrespons og endres ikke gjennom denne
API-kontrakten. Public API er uendret og returnerer fortsatt bare
presentasjonsverdien etter eksisterende publiseringsregler.

Den ene kanoniske public API-ruten under `/api/public/` bruker `crm.urls_public`, `crm.views_public.PublicActorPublicViewSet` og `crm.serializers_public.PublicActorSerializer`. Detail-ruten slår opp på `org_number`. Den tidligere overlappende registreringen gjennom `crm.urls`, `PublicActorViewSet` og `PublicOrganizationSerializer` er fjernet i 3E.2. API-et returnerer bare kontaktpersoner fra aktive `OrganizationPerson`-koblinger med `publish_person=True`, og bare kontaktverdier fra `PersonContact` der `is_public=True`. Public API bruker ikke fallback fra `Person.email` eller `Person.phone`.

Personobjektet i public-kontrakten inneholder additivt `title` når `Person.title` har en verdi. Feltet utelates når tittelen er null eller tom. Tittelen er foreløpig global på `Person`; relasjonsspesifikk tittel er planlagt senere.

Import har egne handlinger for opplasting, preview, rader, AI-generering, beslutninger, commit og feilrapport.

Ved oppretting kan en importjobb ta nullable `phone_region`. Eksplisitt verdi,
også `null`, vinner over tenantdefaulten og fryses i `config_json`; manglende
felt snapshotter tenantens nullable default. Preview klassifiserer telefon som
`VALID`, `INVALID`, `NEEDS_REGION` eller blank `KEEP`. Usikre utfall krever
review, og bare gyldige numre kan skrive canonical identitet ved commit.

Eksport har foreløpig grunnleggende oppretting, listing og visning av eksportjobber. Filgenerering og nedlasting er ikke bekreftet ferdig.

## Intern bildekandidatflyt og public bildekontrakt – ADR-007

[ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) er godkjent målarkitektur. Fase 3D.1s offisielle flyt er aktivert og visuelt godkjent i staging. Fase 3D.2 utvider den interne, feature-gated API-flyten med Brave-søk, limt URL, manuell upload, fokusforvalg, presis X/Y, Foto-zoom og valgfri asset-alttekst. Precision/zoom-oppfølgingen er gjennomført og merget til `main` med PR #33, CI-grønn på mergecommiten, teknisk stagingverifisert, historisk live Brave-verifisert og visuelt eiergodkjent. Brave-credentialen er deretter deaktivert; providerkallet er operativt ikke aktivt for ordinære Editor-sluttbrukere før sluttbrukeravtalegaten er dokumentert oppfylt. Targetschemaet er aktivt i staging etter den separate 3E.3-gaten.

På én tenant-scopet Organization finnes følgende interne handlinger under `images/`:

- `GET legacy-candidates/` returnerer maksimalt tre dedupliserte, transient signerte kandidater fra de eksisterende `thumbnail_image_url`-, `og_image_url`- og `auto_thumbnail_url`-feltene uten DNS/HTTP, automatisk preview, approval eller write; safetyfeil og blokkert legacykilde feiler lukket
- `POST discover/` gjør én kontrollert sidefetch fra `website_url` og finner maksimalt seks Open Graph-/nettsidekandidater fra den hentede siden; lagrede legacy-URL-er inngår bare i `legacy-candidates/`
- `GET search-context/` returnerer det deterministiske Brave-forslaget og eksplisitt valgbare kommuner, kategorier og aktive tilknyttede personer
- `POST brave-search/` tar eksakt synlig `query`, `query_edited` og eventuelle eksplisitte refinement-ID-er og returnerer transient signerte kandidater
- `POST url-candidate/` normaliserer én direkte bilde-URL og returnerer en transient signert kandidat uten å fetche eller velge bildet
- `POST candidate-preview/` tar en kortlivet signert `candidate_ref` og returnerer et begrenset, privat/no-store rasterpreview; `original=true` tvinger preview fra den signerte originale bilde-URL-en i stedet for eventuell provider-thumbnail
- `POST process/` verifiserer og fetcher den samme signerte originale bilde-URL-en for én official-, Brave- eller URL-kandidat og sender bare det valgte bildet gjennom processing profile v1; Foto kan sende komplett `focus_x`, `focus_y` og `zoom`
- `POST upload-process/` tar multipart-upload og prosesserer bare valgt JPEG, PNG eller WebP gjennom samme profil og samme Foto-oppskrift
- `POST rendition-preview/` tar en signert previewref og én av `square`, `landscape` eller `share`; privat original og storage key eksponeres aldri
- `POST approve/` tar signert `approval_ref`, `expected_revision`, valgfri asset-alttekst og eventuell offentlig kreditering og bruker eksisterende locking/replacement
- `GET state/` returnerer aktiv selection, expected revision og signert intern previewinformasjon
- `POST takedown/` mottar eksakt `{"reason_code": "rights_request|privacy_safety|legal_compliance|editorial_policy"}` og utfører en formell deny-first takedown når `PUBLIC_IMAGE_TAKEDOWN_ENABLED=True`; serveren utleder eksakt aktiv release og avviser ekstra callerfelt

Kildeprioriteten i Editor er offisiell nettside/Open Graph → Brave → direkte URL → upload. Dette er en presentert brukerreise, ikke automatisk godkjenning: søk, discovery, preview, URL-oppretting, upload og processing kan ikke opprette selection eller event alene.

Legacykandidatene vises i en separat read-only gruppe og inngår ikke i automatisk discovery. Først et eksplisitt klikk bruker den eksisterende kontrollerte kandidat-previewen; listing alene starter ingen DNS-, HTTP- eller previewrequest. Vanlig `POST`/`PATCH` av Organization kjører ikke Open Graph-refresh, og `og_*`, `auto_thumbnail_url` og `thumbnail_image_url` er read-only i serializer. Eksplisitt `POST refresh-preview/` er fortsatt den eneste vanlige API-ruten som oppdaterer legacy Open Graph-state.

Fase 3F eksponerer ingen ny Import 2.0-image-UX eller fri beslutningspayload. Den interne typed domenekontrakten er default-off med `IMPORT_IMAGE_DECISIONS_ENABLED=False`, krever både den eksisterende image asset-gaten og safety-materialiseringsruntimeen og kan bare anvende en forhåndsgodkjent beslutning som allerede er bundet til importrow og review-snapshot. Dermed kan gaten ikke konfigureres på uten tenant-checksum-guard. Import-commit uten slik beslutning bevarer eksisterende bilde; commit utfører aldri providerkall, fetch, Open Graph-refresh, processing, release eller publiseringswrite.

Takedownhandlingen er en intern sikkerhetsaction, ikke en offentlig lifecycle-API. Plattform-superadmin kan bruke den på tvers av tenants; aktiv tenant-`SUPERADMIN` og `GRUPPEADMIN` kan bruke den i egen tenant; redigerer/leser og cross-tenant object-ID-angrep avvises. Successresponsen inneholder bare ny selection/revisjon, review-event-ID, idempotens/dispositions, anchorcursor og aggregerte delete-tall. Source-checksum, reasonaudit, ledgerhistorikk, private paths og release-ID eksponeres ikke i public API, PUBLIC eller image response.

### Brave-kontrakt

Standardforslaget består av lagret aktørnavn og automatisk kommune bare når aktøren har nøyaktig én kommune. Ved flere kommuner må én velges eksplisitt. Kategori og aktivt tilknyttet person legges bare til ved eksplisitt valg; tags brukes aldri. Den eksakte teksten er synlig og redigerbar, og det brukes ingen AI. Strukturerte kommune-/kategori-/person-refinements gjelder bare det urørte deterministiske forslaget. Ved første manuelle tekstendring nullstiller klienten alle chips og ID-er. Backend avviser en crafted request med `query_edited=true` og nonempty refinement, signerer provenance kun som `manual_edit` og lar dermed ingen skjulte refinement-signaler påvirke lokal rangering. Manuell tekst sendes uendret innenfor lengde-/ordgrensene.

Provideradapteren bruker `GET https://api.search.brave.com/res/v1/images/search`, server-side `X-Subscription-Token` og de eiergodkjente faste parameterne `country=NO`, `search_lang=nb`, `safesearch=strict`, `spellcheck=false` og `count=30`, i tråd med Braves offisielle [API-referanse](https://api-dashboard.search.brave.com/api-reference/images/image_search) og [Image Search-dokumentasjon](https://api-dashboard.search.brave.com/documentation/services/image-search). `search_lang=nb` er godkjent fordi den offisielle enumen ikke støtter `no`. Timeout, rate limit, providerfeil og malformed respons oversettes til kontrollerte API-feil uten å eksponere nøkkelen.

Full providerrespons lagres aldri. Bare eksakt query og det normaliserte, nødvendige delsettet for kandidaten — blant annet tittel, publisher/domene, dimensjoner, thumbnail, bilde-URL og kildeside når feltene finnes — bæres i kortlivede signerte referanser; appen oppretter ingen persistent kandidatmodell eller søkehistorikk. Ved valgt Brave-bilde lagres `brave_image_search` og provider på review-eventet, mens source-URL og side-URL er tomme. Dette følger Braves [standardvilkårs](https://api-dashboard.search.brave.com/documentation/resources/terms-of-service) begrensning på lagring/caching uten særskilte storage-rettigheter; redaktørens godkjenning må fortsatt dekke rettighetene til selve bildet.

Appens omtrent 30 minutter gamle signed-ref må ikke forveksles med providerens egen logging. Braves [privacy policy](https://api-dashboard.search.brave.com/privacy-policy) opplyser at standard query-logger kan beholdes i opptil 90 dager; Zero Data Retention krever Enterprise/egen avtale.

Editor viser før søk at queryen sendes til Brave, kan lagres der i opptil 90 dager og ikke skal inneholde sensitiv eller intern informasjon. Ved resultater vises rettighetspåminnelsen om at redaktøren må kontrollere bruken før godkjenning. Prosjekteier har godkjent parametrene og denne copyen. Braves gjeldende Terms punkt 4(c) krever at hver End User er bundet av en skriftlig avtale med Customer med forpliktelser vesentlig tilsvarende 3(b), og legger ansvaret for nødvendige privacy notices/samtykker på Customer. Dette er en manuell operativ avtaleplikt, ikke en egen samtykkemotor i API-et. Staginggaten 2026-08-11 bekreftet 30 live-kandidater, privat originalpreview, secure fetch og processing med `search_lang=nb`; ingen credentialverdi ble eksponert. Credentialen ble deretter deaktivert, og staging gir igjen kontrollert `brave_not_configured`.

Foto krever enten ingen fokusverdier eller begge verdiene; manglende zoom betyr `1.0000`. Fokus må være endelig tall i intervallet 0–1 og zoom et endelig tall i intervallet 1–3. Logo/contain avviser enhver fokus- eller zoomverdi. Zoom krymper det gyldige cover-vinduet rundt fokuspunktet og klamper det til kildekanten, slik at tom flate aldri oppstår. No-upscale, source byte-/pixelgrenser, tenant-scope og secure fetch er uendret.

### Signering, tilgang og approval

Referansene er tidsstemplet, omtrent 30 minutter gamle maksimalt, og bundet til tenant, Organization og autentisert bruker. Caller kan ikke levere fri proveniens, asset-ID eller rendition-sett ved approval. Lesere kan lese image state og interne rendition-previews, men kan ikke starte discovery, søk, URL-oppretting, fetch, upload, processing eller approval. Når featureflagget er av, feiler rutene før nettverk, storage eller bildedomene-write.

Asset-alttekst kan være eksakt tom streng; den fylles ikke skjult med aktørnavn. En ikke-tom whitespace-only verdi avvises. Den separate systemfallback-selectiontjenesten krever fortsatt ikke-tom fallbacktekst. Brave og upload kan ha tom `source_url` i eventet; øvrige ikke-tomme source types krever URL.

Schema-migrasjon `0027` omskriver ingen data og kan reverseres mens alle selection- og event-altverdier fortsatt er ikke-tomme. Etter første blanke asset-/event-alt er den forward-only fordi de gamle databaseconstraintene avviser raden. Operativ rollback er da feature-off og en fremoverrettet retting; en pre-deploy-backup må tas og verifiseres før aktivering. Data skal aldri omskrives til en skjult aktørnavn-fallback for å tvinge schemaet bakover.

Schema-migrasjon `0028` legger additivt til `ImageRenditionSet.zoom` med default `1.0000` og constraint 1–3. Eksisterende rows beholder dermed dagens cropsemantikk. Reverse er tillatt så lenge alle rows fortsatt har default; den blokkeres før feltet droppes dersom en non-default zoomoppskrift finnes, fordi tap av zoom da ville gjøre historisk rendermetadata uriktig.

Uploadtjenestens filgrense er 15 MiB. Staging-nginx har 16 MiB request-body-grense for å gi plass til multipart-overhead. 3D.2-konfigurasjonen og faktisk multipartflyt er deployet og stagingverifisert.

Den godkjente overgangen i [ADR-009](../decisions/ADR-009-PUBLIC_IMAGE_RUNTIME_RELEASE_DELIVERY_AND_RESTORE_SAFE_DENY_STATE.md) er implementert med default-off kode-/eksempelgater og er aktiv i staging gjennom ignorert miljøkonfigurasjon:

- et strukturert `image`-objekt får `kind` med enum `asset|system_fallback`, `alt_text`, nullable `credit` og `square`-, `landscape`- og `share`-renditions med `url`, `width` og `height`
- bare CRM-kontrollerte renditions eller systemfallback blir aktive bildekilder etter cutover
- offentlige rendition-URL-er blir absolutte HTTPS-URL-er
- intern kilde, proveniens, review, audit og privat original eksponeres ikke
- `thumbnail_image_url` og `preview_image_url` beholdes midlertidig som deprecated aliaser; etter cutover kommer begge fra samme `PublicImageProjection` og peker til `image.square.url`
- aliasene fjernes bare i en senere eksplisitt API-versjon eller integrasjonsfase
- aliasene og `image.square.url` kan ikke divergere
- API-lesing gjør ingen ekstern bildefetch

Canonical app-URL-er og public rendition-URL-er skal bygges fra miljøkonfigurerte, allowlistede site- og media-origins, ikke fra vilkårlig request-host.

`PublicImageProjection` er read-only og blir eneste resolver for public API, PUBLIC HTML og head. Den gjør ingen HTTP-/DNS-oppslag, decode, render eller storage-write og leser samme journal/read-model som serving-gaten. De interne refsene og previewene er ikke public projection eller public serving.

`PUBLIC_IMAGE_PROJECTION_ENABLED=False` er kode-/eksempelstandard og styrer projection/shadow; den ignorerte stagingverdien er `True` etter den separate [shadowgaten](../status/STAGING_PHASE_3E2_SHADOW_2026-08-24.md). Projection krever gyldige site-/media-origins slik at både static fallback og release-URL-er er absolutte. Den reproducerbare, skrivebeskyttede fullkataloggaten er `python manage.py audit_public_image_projection`; request-shadow kjøres bare for detail, ikke for hele listen. `PUBLIC_IMAGE_API_SCHEMA_ENABLED=False` styrer target-response og OpenAPI; den ignorerte stagingverdien er `True` etter [3E.3-cutovergaten](../status/STAGING_PHASE_3E3_CUTOVER_2026-08-24.md). Schemaflagget krever projection og controlled serving. Med schemaflagget av er responsefeltene og legacyverdiene uendret. Med flagget på kommer `image` og begge deprecated aliasene fra samme projection. `PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=False` er en separat global PUBLIC/head-gate og krever projection, targetschema, serving og gyldige origins; den ignorerte stagingverdien er `True`. Ingen tenant-enrollment er innført uten en konkret blocker.

Projection og byte-serving deler samme fail-closed validering av publication, tenant/Organization/selection/revision/rendition-sett, eksakt tre mappinger, canonical keys og immutable snapshots. Projection autoriserer alle tre varianter gjennom 3E.1Cs read-only bridge, men leser ikke bildefiler. Serving beholder den separate byte-/filverifikasjonen. Ved ukjent eller utilgjengelig safety-state returnerer projection production fallback v1, aldri legacybilde. Fallback v1 gjenbruker de visuelt kontrollerte 3B.1-bytene på canonical `fallback-{square,landscape,share}.png`-stier og bruker blank alttekst.

Endelig endepunktliste skal genereres fra aktive ruter og kontrolleres mot Swagger/OpenAPI.
