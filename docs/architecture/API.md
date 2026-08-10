# API

**Status:** implementert, detaljkartlegging gjenstår

API-et omfatter autentisering, tenants, taksonomi, aktører, personer, koblinger, kontaktkanaler, interne bildekandidathandlinger, public actors, importjobber og eksportjobber.

Tenant-scope Editor-API returnerer både interne og offentlige `PersonContact` for autoriserte brukere.

Det aktive public API-et under `/api/public/` bruker `crm.serializers_public.PublicActorSerializer`. Det returnerer bare kontaktpersoner fra aktive `OrganizationPerson`-koblinger med `publish_person=True`, og bare kontaktverdier fra `PersonContact` der `is_public=True`. Public API bruker ikke fallback fra `Person.email` eller `Person.phone`.

Personobjektet i public-kontrakten inneholder additivt `title` når `Person.title` har en verdi. Feltet utelates når tittelen er null eller tom. Tittelen er foreløpig global på `Person`; relasjonsspesifikk tittel er planlagt senere.

Import har egne handlinger for opplasting, preview, rader, AI-generering, beslutninger, commit og feilrapport.

Eksport har foreløpig grunnleggende oppretting, listing og visning av eksportjobber. Filgenerering og nedlasting er ikke bekreftet ferdig.

## Intern bildekandidatflyt og planlagt public bildekontrakt – ADR-007

[ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) er godkjent målarkitektur. Fase 3D.1s offisielle flyt er aktivert og visuelt godkjent i staging. Fase 3D.2 utvider den interne, feature-gated API-flyten med Brave-søk, limt URL, manuell upload, fokusforvalg og valgfri asset-alttekst på aktiv featurebranch. 3D.2 er ikke CI- eller stagingverifisert og er ikke eiergodkjent. Det aktive public API-et returnerer fortsatt bare legacy bilde-URL-er.

På én tenant-scopet Organization finnes følgende interne handlinger under `images/`:

- `POST discover/` finner maksimalt seks kandidater fra `website_url`, lagret Open Graph og én kontrollert sidefetch
- `GET search-context/` returnerer det deterministiske Brave-forslaget og eksplisitt valgbare kommuner, kategorier og aktive tilknyttede personer
- `POST brave-search/` tar eksakt synlig `query`, `query_edited` og eventuelle eksplisitte refinement-ID-er og returnerer transient signerte kandidater
- `POST url-candidate/` normaliserer én direkte bilde-URL og returnerer en transient signert kandidat uten å fetche eller velge bildet
- `POST candidate-preview/` tar en kortlivet signert `candidate_ref` og returnerer et begrenset, privat/no-store rasterpreview; `original=true` tvinger preview fra den signerte originale bilde-URL-en i stedet for eventuell provider-thumbnail
- `POST process/` verifiserer og fetcher den samme signerte originale bilde-URL-en for én official-, Brave- eller URL-kandidat og sender bare det valgte bildet gjennom processing profile v1
- `POST upload-process/` tar multipart-upload og prosesserer bare valgt JPEG, PNG eller WebP gjennom samme profil
- `POST rendition-preview/` tar en signert previewref og én av `square`, `landscape` eller `share`; privat original og storage key eksponeres aldri
- `POST approve/` tar signert `approval_ref`, `expected_revision`, valgfri asset-alttekst og eventuell offentlig kreditering og bruker eksisterende locking/replacement
- `GET state/` returnerer aktiv selection, expected revision og signert intern previewinformasjon

Kildeprioriteten i Editor er offisiell nettside/Open Graph → Brave → direkte URL → upload. Dette er en presentert brukerreise, ikke automatisk godkjenning: søk, discovery, preview, URL-oppretting, upload og processing kan ikke opprette selection eller event alene.

### Brave-kontrakt

Standardforslaget består av lagret aktørnavn og automatisk kommune bare når aktøren har nøyaktig én kommune. Ved flere kommuner må én velges eksplisitt. Kategori og aktivt tilknyttet person legges bare til ved eksplisitt valg; tags brukes aldri. Den eksakte teksten er synlig og redigerbar, og det brukes ingen AI. Strukturerte kommune-/kategori-/person-refinements gjelder bare det urørte deterministiske forslaget. Ved første manuelle tekstendring nullstiller klienten alle chips og ID-er. Backend avviser en crafted request med `query_edited=true` og nonempty refinement, signerer provenance kun som `manual_edit` og lar dermed ingen skjulte refinement-signaler påvirke lokal rangering. Manuell tekst sendes uendret innenfor lengde-/ordgrensene.

Provideradapteren bruker `GET https://api.search.brave.com/res/v1/images/search`, server-side `X-Subscription-Token` og de faste parameterne `country=NO`, `search_lang=nb`, `safesearch=strict`, `spellcheck=false` og `count=30`, i tråd med Braves offisielle [API-referanse](https://api-dashboard.search.brave.com/api-reference/images/image_search) og [Image Search-dokumentasjon](https://api-dashboard.search.brave.com/documentation/services/image-search). `search_lang=nb` er et dokumentert avvik fra ønsket norskekode `no`, fordi den offisielle enumen ikke støtter `no`. Timeout, rate limit, providerfeil og malformed respons oversettes til kontrollerte API-feil uten å eksponere nøkkelen.

Full providerrespons lagres aldri. Bare eksakt query og det normaliserte, nødvendige delsettet for kandidaten — blant annet tittel, publisher/domene, dimensjoner, thumbnail, bilde-URL og kildeside når feltene finnes — bæres i kortlivede signerte referanser; appen oppretter ingen persistent kandidatmodell eller søkehistorikk. Ved valgt Brave-bilde lagres `brave_image_search` og provider på review-eventet, mens source-URL og side-URL er tomme. Dette følger Braves [standardvilkårs](https://api-dashboard.search.brave.com/documentation/resources/terms-of-service) begrensning på lagring/caching uten særskilte storage-rettigheter; redaktørens godkjenning må fortsatt dekke rettighetene til selve bildet.

Appens omtrent 30 minutter gamle signed-ref må ikke forveksles med providerens egen logging. Braves [privacy policy](https://api-dashboard.search.brave.com/privacy-policy) opplyser at standard query-logger kan beholdes i opptil 90 dager; Zero Data Retention krever Enterprise/egen avtale.

`BRAVE_IMAGE_SEARCH_API_KEY` skal ikke aktiveres i staging eller et senere miljø før prosjekteier eller annen avtaleeier har dokumentert hvordan redaktørene omfattes av standardvilkårenes punkt 4(c), og hvilke personvernvarsler eller samtykker som kreves for querydata. Manglende nøkkel er derfor en gyldig fail-closed tilstand frem til denne ikke-tekniske gaten er godkjent.

### Signering, tilgang og approval

Referansene er tidsstemplet, omtrent 30 minutter gamle maksimalt, og bundet til tenant, Organization og autentisert bruker. Caller kan ikke levere fri proveniens, asset-ID eller rendition-sett ved approval. Lesere kan lese image state og interne rendition-previews, men kan ikke starte discovery, søk, URL-oppretting, fetch, upload, processing eller approval. Når featureflagget er av, feiler rutene før nettverk, storage eller bildedomene-write.

Asset-alttekst kan være eksakt tom streng; den fylles ikke skjult med aktørnavn. En ikke-tom whitespace-only verdi avvises. Den separate systemfallback-selectiontjenesten krever fortsatt ikke-tom fallbacktekst. Brave og upload kan ha tom `source_url` i eventet; øvrige ikke-tomme source types krever URL.

Schema-migrasjon `0027` omskriver ingen data og kan reverseres mens alle selection- og event-altverdier fortsatt er ikke-tomme. Etter første blanke asset-/event-alt er den forward-only fordi de gamle databaseconstraintene avviser raden. Operativ rollback er da feature-off og en fremoverrettet retting; en pre-deploy-backup må tas og verifiseres før aktivering. Data skal aldri omskrives til en skjult aktørnavn-fallback for å tvinge schemaet bakover.

Uploadtjenestens filgrense er 15 MiB. Staging-nginxmalen har 16 MiB request-body-grense for å gi plass til multipart-overhead, men 3D.2-konfigurasjonen er ennå ikke deployet eller stagingverifisert.

Den planlagte overgangen er additiv:

- et strukturert bildeobjekt får `kind`, alt-tekst, eventuell offentlig kreditering og `square`-, `landscape`- og `share`-renditions med URL, bredde og høyde
- bare CRM-kontrollerte renditions eller systemfallback blir aktive bildekilder etter cutover
- offentlige rendition-URL-er blir absolutte HTTPS-URL-er
- intern kilde, proveniens, review, audit og privat original eksponeres ikke
- `thumbnail_image_url` og `preview_image_url` beholdes midlertidig som deprecated aliaser til dokumenterte rendition-URL-er
- aliasene fjernes bare i en senere eksplisitt API-versjon eller integrasjonsfase
- API-lesing gjør ingen ekstern bildefetch

Canonical app-URL-er og public rendition-URL-er skal bygges fra miljøkonfigurerte, allowlistede site- og media-origins, ikke fra vilkårlig request-host.

Eksakt public toppnivåfeltnavn, enum og alias-til-variant-mapping fastsettes før public API-implementering. De interne refsene og previewene er ikke public projection eller public serving.

Endelig endepunktliste skal genereres fra aktive ruter og kontrolleres mot Swagger/OpenAPI.
