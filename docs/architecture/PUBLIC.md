# Public Architecture

**Status:** Implementert grunnløsning; kontaktregel og fase 2-stabilisering implementert; standalone public image serving er `ACTIVE` i staging; 3E.2 projection/API-shadow er `CLOSED / SHADOW VERIFIED`; 3E.3 PUBLIC/head-kobling er implementert default-off og venter på staginggaten, der PUBLIC fortsatt bruker legacybilder

**Sist verifisert:** 2026-08-24

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
- `Person.title` vises i public API og PUBLIC HTML når feltet har en verdi, og utelates rent når det er tomt.

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
- eksisterende direkte e-post blir ikke automatisk offentlig av synkronisering eller reparasjonskommandoen `repair_person_contacts`

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

Kommandoen ble kjørt med `--apply` på staging 2026-07-26 etter backup og entydig dry-run. Sluttilstanden på staging var:

- `email_contacts_total=164`
- `email_contacts_public=164`
- `email_contacts_private=0`
- `active_links_total=170`
- `active_links_publish_true=167`
- `active_links_publish_false=3`

Dette beskriver en eksplisitt godkjent staging-datakjøring. Nye kontakter blir ikke automatisk offentlige uten bruker- eller importvalg.

Målarkitekturen er godkjent i `ADR-005`:

- `PersonContact` blir autoritativ kilde
- offentlige kontaktkanaler velges per aktør–person-kobling
- HTML, API og Editor-preview bruker én offentlig projeksjon
- direktefeltfallback fjernes

Full ADR-005-målmodell med relasjonsspesifikk kontaktpublisering er fortsatt planlagt og ikke implementert.

## Fase 2: trygg telefonstabilisering

Fase 2 utvider den eksisterende, bakoverkompatible `repair_person_contacts`-kommandoen med et eksplisitt `--contact-type PHONE`. Uten valget reparerer kommandoen fortsatt bare e-post.

Telefonkjøringen:

- er dry-run som standard
- kan avgrenses med `--tenant`
- oppretter bare en manglende privat primær `PHONE`-kontakt
- aktiverer aldri publisering
- endrer ikke eksisterende telefon- eller e-postkontakter
- rapporterer kandidater med interne ID-er og flere primærtelefoner, verdiavvik og matchende ikke-primær telefon uten rå kontaktverdier eller automatisk konfliktreparasjon

Direkte `Person.phone` brukes fortsatt aldri som PUBLIC-fallback. Offentlig telefon krever publisert aktør, aktiv kobling, `publish_person=True` og en `PHONE`-kontakt med `is_public=True`.

## Bilde og thumbnail

Dagens løsning velger mellom manuell thumbnail, automatisk thumbnail og Open Graph-bilde. Eksterne bilde-URL-er kan forsvinne, endres, blokkere hotlinking eller ha feil format.

[ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) er godkjent som målarkitektur, og fase 3B–3D har implementert intern bilde-/selection-/rendition-/release-domenegrunnmur. [ADR-009](../decisions/ADR-009-PUBLIC_IMAGE_RUNTIME_RELEASE_DELIVERY_AND_RESTORE_SAFE_DENY_STATE.md) har godkjent public runtimearkitekturen. 3E.1A-journalen/off-serverankeret, 3E.1B-materialisering og 3E.1C standalone controlled serving er `ACTIVE` i staging. 3E.1C-livegaten beviste canonical media-route, kontrollert Django-gate, intern Nginx-serving, eksplisitte origins, cache, fail-closed og restart/restore. 3E.2 projection-shadow er `CLOSED / SHADOW VERIFIED`. 3E.3-targetschema, PUBLIC/head-cutover og production fallback v1 er implementert bak default-off gater, men dagens eksterne URL-flyt gjelder fortsatt i staging til den separate aktiveringsgaten er bestått. Takedown er ikke implementert.

Godkjent retning:

- kandidater fra offisiell nettside, Open Graph, upload, limt URL og senere en kontrollert Brave-provider
- kontrollert fetch og teknisk validering før eksplisitt menneskelig godkjenning
- tenant-eid asset med privat original
- typed aktør-selection med fit, ett fokuspunkt, locking og append-only historikk
- square-, landscape- og 1200 × 630-share-renditions
- deterministisk Kreative Norge-fallback uten ekstern bildekilde
- én felles public image projection for Editor-preview, PUBLIC HTML, public API og delingsmetadata
- ingen endring av aktør-, person- eller kontaktpublisering som følge av bildehandlinger

Før cutover skal public runtimeen bruke:

- lokal append-only SQLite-ledger med restore-sikkert off-server anker, der nyere deny/no-reuse-state alltid vinner over eldre DB/apprestore
- separat `/srv/kreative-norge/media/public-delivery/`; dagens `image_renditions_public` er intern artifact-storage og skal aldri eksponeres
- canonical release keys `releases/<release_uuid>/<variant>.<ext>`, permanent reservasjon før materialisering og create-only/no-clobber-verifikasjon
- Django release-gate og intern Nginx `X-Accel-Redirect` eller dokumentert likeverdig serving; ingen anonym filesystem-alias
- eksplisitte `PUBLIC_SITE_ORIGIN` og `PUBLIC_MEDIA_ORIGIN`, aldri vilkårlig `Host` eller `X-Forwarded-Host`
- én read-only `PublicImageProjection` som bruker samme ledger/read-model som serving-gaten og gjør ingen nettverks-, decode-, render- eller storage-writekall

Manglende eller korrupt journal, stale/ukjent cursor, denied/retired release, scope mismatch, upublisert aktør eller manglende/ufullstendige filer feiler lukket til statisk systemfallback eller ingen levering. Production fallback v1 finnes som uavhengige, versjonerte square-, landscape- og sharefiler på canonical static-stier. Den gjenbruker de visuelt kontrollerte 3B.1-bytene byte-for-byte og har blank alttekst fordi grafikken er dekorativ og aktørnavnet allerede er synlig.

PUBLIC skal etter cutover bare bruke CRM-kontrollerte renditions eller systemfallback. Rå kilde-URL, intern proveniens, audit og privat original skal ikke eksponeres.

Godkjente kortmål beholder 90 × 90 i PUBLIC-oversikten og bruker 160 × 160 på desktop-detaljen. Mobil detalj forblir rektangulær; eksakt felles høyde avgjøres i fase 3B. Logo bruker `contain`, foto bruker `cover` og fokuspunkt, PUBLIC-tags er grønne, og lange navn, kommuner, tags og knapper skal ikke gi overflow.

PUBLIC-detaljen skal få absolutt canonical, Open Graph og Twitter Card. Canonical app-origin og public media-origin skal være miljøkonfigurerte og allowlistede, ikke avledet fra vilkårlig request-host. `og:image` bruker CRM-kontrollert share-rendition eller fallback på 1200 × 630. Korrekt metadata kan leveres, men det kan ikke loves at alle meldingsklienter viser preview.

3E.3 implementerer dette med en liten read-only metadata-DTO. List og detail bruker `projection.square`; detail-head bruker `projection.share`; list-head bruker den generiske share-fallbacken. Canonical bygges fra `PUBLIC_SITE_ORIGIN` og `reverse()`, også for filtrerte listsider. Et asset som feiler i nettleseren byttes én gang til static square-fallback uten legacyoppslag eller state-write. `PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=False` er kode-/eksempelstandard og krever projection, API-schema og controlled serving når den slås på.

Fase 3E.1C velger foreløpig `private, max-age=60, must-revalidate`, checksum-`ETag`, `no-store` på 404/503 og ingen shared proxycache eller `immutable`. Dette begrenser klientens stale-vindu uten å påstå at formell purge/takedown er levert. Endelig purge-/verifikasjonskontrakt fastsettes i fase 3E.4. Formell takedown forblir deaktivert til release-deny, tenant-scopet checksum-deny, legacyguard, felles projection/gateway-state, originblokkering, cache expiry/purge/verifikasjon, gammel restore og republisering med ny UUID/key er bevist. Global checksum-deny er ikke del av godkjent MVP.

## Videre integrasjon

Løsningen er ikke ferdigstilt for ekstern integrasjon med Musikkontoret.no. Før dette må API-kontrakt, caching, bildeleveranse, personvern og publiseringsregler være eksplisitt spesifisert.
