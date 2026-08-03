# Project Status Current

**Status:** Fase 1 og 2 gjennomført; fase 3A, fase 3B.1 og fase 3B.2 teknisk gjennomført; lokal Hetzner storage-/backup-MVP ACTIVE; fase 3C er startet med en avslått konfigurasjonsgrunnmur for lokale image-storagealiaser

**Teknisk sist verifisert:** 2026-08-03

**Teknisk verifisert mot:** fase 2-applikasjonsversjonen i merge-commit `6768af8a3b48314aec028ec5972939c6ef0e38e8`, fortsatt kjørende API-/web-images, PostgreSQL, Django, migrasjoner, HTTPS, PUBLIC API/HTML, Editor-API og kontrollert tenant-avgrenset telefonreparasjon etter verifisert backup; fase 3B.1 og fase 3B.2 er i tillegg verifisert som isolerte lokale/Linux-prototyper uten CRM-runtimekobling. Første fase 3C-konfigurasjonsgrunnmur er lokalt verifisert med 18 avgrensede settings-tester, inkludert krav om eksplisitte roots ved aktivert feature utenfor debug, Django system check, uendret migrasjonsstatus og hele backendpakken på 152 tester. Staging-repoet er separat fast-forwardet og rent på backupmodulens godkjente `main`-commit uten deploy eller containerrestart. [Backupaktiveringen 2026-08-02](STAGING_BACKUP_ACTIVATION_2026-08-02.md) verifiserte hele Storage Box-/Borg-kjeden, recovery-custody, første backup, full repository-check, isolert restore og aktive timere.

**Produkt-roadmap sist oppdatert:** 2026-08-02

**Arbeidsflyt sist kontrollert:** 2026-07-28

**Ansvar:** Prosjekteier + ChatGPT for prioritering og produktretning. Codex for oppdatering etter implementering.

## Aktiv utviklingsfase

Fase 1 i [ROADMAP.md](ROADMAP.md) ble gjennomført 2026-07-29. Den skrivebeskyttede baselinen verifiserte server-, container-, bygg-, proxy-, cache-, PUBLIC- og Editor-tilstanden. Hoveddesignet på forsidene i Editor CRM og PUBLIC er godkjent designreferanse. Øvrige sider, kort og komponenter skal videreutvikles innenfor denne visuelle retningen.

Fase 2 ble gjennomført 2026-07-30 etter teknisk stagingverifisering, kontrollert reparasjon av fire private primære legacytelefonkontakter og prosjekteiers visuelle sluttkontroll.

Fase 3A kartla deretter dagens thumbnail-, bilde-, storage-, import- og kortflyt uten endringer. [ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) er godkjent som arkitekturgrunnlag.

[Fase 3B.1](PHASE_3B1_IMAGE_RENDITION_SPIKE.md) har gjennomført en isolert bildebehandlings- og renditionprototype med syntetiske fixtures. Pillow og pyvips/libvips, sikker dekoding, contain/cover, fokus, formater, determinisme, fallback og ressursbruk er målt. Prosjekteier har godkjent Pillow bak intern adapter, statisk JPEG/PNG/WebP-input, processing profile v1, no-upscale, immutable key-invarianten og 15 MiB som konfigurerbar standard. Endelig pixelgrense, dimensjons- og blur-/komprimeringsregler er fortsatt åpne.

[Fase 3B.2](PHASE_3B2_STORAGE_RESTORE_SPIKE.md) er teknisk gjennomført som isolert prototype. Den målte separate Django-storagealiaser, gjenbrukt processing artifact key, separat public release key, private/public Moto-buckets, versioning, purge/cache, deny-journal, T0–T5 restore-reconciliation, backupstrategier og statisk fallback. Prosjekteier godkjente 2026-08-01 de leverandøruavhengige prinsippene om to-key-kontrakt, en aktiv public rendition-store uten tilgjengelige historiske public versjoner, kontrollert public delivery, private originaler, hybridbackup, fail-closed restore, varig deny-journal/read-model og idempotent purge. ADR-008 har senere valgt lokal host-persistent storage for første MVP; providerkravene fra prototypen er derfor betingede dersom objektlagring senere tas opp igjen.

[ADR-008](../decisions/ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md) velger en enklere operasjonell MVP: app, database og aktiv media på dagens Hetzner Cloud-server, lokale navngitte Django-storagealiaser og kryptert Borg-backup til separat Hetzner Storage Box. S3/AWS/Backblaze/CDN utsettes. Backupgrunnmuren er **ACTIVE** etter verifisert Storage Box, kryptert repository, separat recovery-custody for minst to ansvarlige, første backup, full repository-check, isolert restore av samme arkiv, Storage Box-snapshot, nyere synlig Cloud Backup og aktiverte timere. Første backup tok 8 sekunder og restore-smoke 8,7 sekunder. Foreløpig RPO er inntil omtrent 24 timer pluss timerforsinkelse; restore-smoke-målingen er evidens, ikke et løfte om full katastrofe-RTO.

Baselinen fant ingen eksisterende `/app/imports`-, `/app/exports`- eller host-mediafiler. API-containeren mangler fortsatt persistent import-/eksport-/media-mount, og Django default storage peker til `/app`; nye FileField-filer kan derfor gå tapt ved recreate. Host-persistent storage og runtimekobling er en separat senere leveranse. Aktiv Storage Box er BX11 med 1 TB i FSN1, med kapasitetsreview ved 60–70 prosent faktisk bruk og 20–30 prosent ledig margin.

Det separate infrastrukturløpet for ADR-008 er fullført. Første fase 3C-leveranse innfører nå `IMAGE_ASSET_FEATURE_ENABLED=False` som standard og separate lokale `FileSystemStorage`-aliaser for private originaler og offentlige renditions. Aliasene er bare konfigurasjonsgrunnmur: ingen runtime henter dem, ingen bildefiler skrives eller serveres, og legacybildeflyten er uendret. Fase 3B.1R med representative bilder og fargeprofiler forblir en kvalitetsgate før reell bildebehandling kan godkjennes, men blokkerer ikke dette additive grunnarbeidet.

Bildearkitekturens modeller og runtime er ikke implementert. Det er ikke opprettet modeller eller migrasjoner, host-mediaområder, filskriving, serving, API- eller frontendendringer eller gjennomført deploy. Eksisterende default-storage for import-/eksportfiler og dagens eksterne `thumbnail_image_url`-, `auto_thumbnail_url`-, `og_image_url`- og faviconflyt gjelder fortsatt. Neste fase 3C-leveranse krever separat godkjenning.

Den langsiktige relasjonsspesifikke kontaktmodellen fra [ADR-005](../decisions/ADR-005-CONTACT_ARCHITECTURE.md) kommer fortsatt senere. Internasjonal telefonmodell skal spesifiseres i et eget ADR ved overgangen fra fase 3 til fase 4 og implementeres tidlig i fase 5; dette blokkerer ikke fase 3.

## Godkjent bildearkitektur – første konfigurasjonsgrunnmur implementert

ADR-007 beslutter følgende konseptuelle flyt:

```text
ImageCandidate
    → kontrollert fetch og teknisk validering
    → tenant-eid ImageAsset med privat original
    → OrganizationImageSelection
    → ImageRendition
    → én felles public image projection
```

Godkjente hovedprinsipper:

- assetet eies av tenant, kan finnes før en aktør og kobles gjennom en typed aktør-selection
- bare ett bildevalg er aktivt per aktør; et låst bilde erstattes bare gjennom eksplisitt approval og replacement
- fit og ett fokuspunkt lagres på selection i første MVP
- viktige overganger registreres i append-only bildehistorikk
- én rask og versjonert godkjenning brukes uten obligatoriske juridiske detaljfelt
- kreditering er valgfri uten konkret krav
- formell takedown fjerner offentlig bruk, går til fallback og beholder privat karantene og historikk
- deterministic Kreative Norge-fallback finnes som square, landscape og 1200 × 630 share
- public API utvides additivt med strukturert bildeobjekt og midlertidige deprecated URL-aliaser
- lokal utvikling, staging og første produksjons-MVP bruker navngitte filesystemaliaser gjennom Djangos `STORAGES`; aktiv media forblir på dagens server og objektlagring vurderes bare på nytt ved dokumentert behov
- Import 2.0 skal senere bruke `KEEP_LOCKED_IMAGE`, `SET_APPROVED_IMAGE` og `USE_APPROVED_FALLBACK` uten nettverk eller bildebehandling i commit
- ingen bildehandling endrer aktør-, person- eller kontaktpublisering

Godkjent processing profile v1 bruker `square` 512 × 512 og `landscape` 800 × 450 som WebP quality 82 for foto, `share` 1200 × 630 som ikke-progressiv JPEG quality 85, PNG for logo med alpha og WebP/JPEG for fallback. Format, encoderinnstillinger, source checksum, fit, fokus, variant og processing-version inngår i immutable key.

Fase 3C skal implementeres additivt og bak avslått feature. Før reell bildebehandling eller public serving kan godkjennes gjenstår fase 3B.1R med representative, rettighetsavklarte ekte bilder; eksplisitt sRGB-normalisering og fargeprofiltesting; endelige pixel-, dimensjons- og kvalitetsgrenser; lokal private/public-storage og same-origin/media-origin-serving; lokal cache-, purge- og verifikasjonskontrakt; permanent deny-journal og materialisert read-model med journalcursor og fail-closed reconciliation; SVG-policy og eventuell sikker rasterisering; eventuell skadevarekontroll og bakgrunnskø; endelig public API-schema og alias-til-variant-mapping; public release key-struktur innenfor godkjente invarianter; concurrency og databaseconstraints; retensjonsmekanisme; sync/async-grense og observability. S3, CDN, ekstern IAM, bucket-policy, KMS, Object Lock og provider-spesifikk `versionId`-/purgeverifikasjon er bare en betinget senere gate dersom objektlagring tas opp igjen på grunn av dokumentert behov.

Godkjent fase 3B.2-kontrakt skiller intern artifact identity fra public release identity. Aktiv public rendition-store er unversioned eller likeverdig uten tilgjengelige historiske public versjoner; første MVP leverer senere gjennom en kontrollert same-origin/media-origin fra lokal host-persistent storage. Private originaler skal forbli private. Hybridbackup inkluderer aktive rendition-bytes, mens deny-journalen har separat failure-domain og alltid avstemmes fail-closed før public serving etter restore. Lokal serving/purge og permanent journal er fortsatt åpne; backup-RPO og restore-smoke er foreløpig målt, mens full katastrofe-RTO fortsatt er åpen. Ekstern S3/CDN er utsatt.

## Verifisert fase 1-baseline

- lokal og GitHub `main` var synkronisert på `f6f03d67ba0c5d3afbe258fb356248e7075c4b49`
- staging-repoet var rent på `ea8b8762aecdff760728139b1659f7d3a43445c7`; de åtte nyere commitene på `main` endret ikke kjørende applikasjonskode
- API-koden i imaget kunne knyttes til serverrepo-SHA gjennom innebygd Git-metadata og filhashes
- web-imagets eksakte commit var ikke merket, men JS- og CSS-bundles matchet ren build fra dagens `main`
- HTTPS leverte de samme bundlehashene som web-containeren, også med cache-busting
- nginx og Caddy leverte forventet kjede; proxy og Cloudflare-cache viste ikke gamle frontendfiler
- Django system check og PostgreSQL readiness var grønne, og de kjørende containerne hadde ingen restarter
- PUBLIC desktop/mobil og autentisert Editor ble kontrollert; Editor-forsiden er godkjent designreferanse
- observerte kort-, bilde-, tag- og layoutavvik er lagt til fase 3 eller fase 5 og ble ikke rettet i baselinen
- ingen kode, data, publiseringsflagg, containere, tjenester eller deploy ble endret i fase 1

Detaljert, datert evidens finnes i [FRONTEND_BASELINE_2026-07-29.md](FRONTEND_BASELINE_2026-07-29.md). Dette dokumentet er fortsatt autoritativ nåstatus.

## Fase 2-baseline

Det konkrete undersøkelseseksemplet viste en person med verdi i direkte `Person.phone`, men uten noen `PersonContact` av type `PHONE`. Personen hadde bare en lagret e-postkontakt. Direkte telefon kan derfor ikke få egen offentlig kontroll og skal heller aldri brukes som PUBLIC-fallback.

Kodekartleggingen viser samtidig at dagens person-API synkroniserer direkte `Person.email` og `Person.phone` til private primære kontakter ved ny lagring. Avviket gjelder derfor eksisterende legacy-data som ikke har gått gjennom denne synkroniseringen. `repair_person_contacts` reparerer før fase 2 bare e-post.

Editor-baselinen viste fire utrygge forhåndsvalg i opprettingsflytene:

- offentlig e-post på ny kontaktperson
- offentlig telefon på ny kontaktperson
- publisering av ny kontaktperson
- publisering ved kobling av eksisterende person

Alle fire skal være avslått som standard i fase 2. Dette endrer ikke eksisterende lagrede publiseringsflagg.

Fase 2-leveransen fra PR #12, merget i `6768af8a3b48314aec028ec5972939c6ef0e38e8`, implementerer:

- eksplisitt `--contact-type PHONE` i den bakoverkompatible, dry-run-først `repair_person_contacts`-kommandoen
- tenant-filter, idempotens og kandidat-/konfliktrapport med interne ID-er uten kontaktverdier
- privat primær telefonkontakt ved entydig lokal/test-apply
- alle fire nye publiseringsvalg avslått som standard og nullstilt ved faktisk aktør- eller tenantbytte
- tydeligere Editor-tekst for personpublisering kontra offentlig e-post/telefon
- additiv offentlig `Person.title` i aktivt API og PUBLIC HTML

Ingen schema-migrasjon inngår. Kodeleveransen endret ikke eksisterende publiseringsflagg og kjørte ingen data-apply ved merge eller deploy. Den separate, senere stagingreparasjonen ble gjennomført etter uttrykkelig godkjenning og backup som beskrevet nedenfor; produksjon ble ikke endret.

## Verifisert fase 2-stagingstatus

PR #12 ble merget med ordinær merge-commit og deployet kontrollert til staging 2026-07-29. Staging-repoet var rent på merge-commiten da API- og web-imagene ble bygget og startet.

- PostgreSQL readiness, Django system check og migrasjonsstatus var grønne
- API-, web- og databasecontainer kjørte; API og web hadde ingen restarter etter ny oppstart
- HTTPS, auth-session, PUBLIC HTML og aktivt public API svarte `200`
- `check_public_actor_links` kontrollerte `122` publiserte aktører og `122` kortlenker uten brutte lenker
- JavaScript-bundlen `index-DvXY3g5v.js` ble levert fra staging, og SHA-256 var identisk over HTTPS og i web-containeren
- stagingbyggets Editor nullstilte ny-personskjema, feiltilstand, koblingsstatuser og alle fire nye publiseringsvalg ved faktisk aktørbytte; kontrollen sendte ingen tenantmutasjoner
- eksisterende `Person.title` ble verifisert i både aktivt public API og PUBLIC HTML
- person uten tittel fikk ingen tom tittelrad, og direkte `Person.phone` ble ikke brukt som PUBLIC-fallback
- tenant-avgrenset `PHONE`-dry-run for `musikkontoretnord` undersøkte `49` personer, fant `4` kandidater og ingen konflikter; kandidat-ID-ene var `1`, `2`, `132` og `150`
- etter streng kandidatkontroll og verifisert PostgreSQL-backup opprettet den godkjente `--apply`-kjøringen nøyaktig fire private primære `PHONE`-kontakter, kontakt-ID `233`–`236`, for de fire kandidatene og rapporterte `changes_applied=4`
- umiddelbar etterfølgende dry-run rapporterte null kandidater, null konflikter og `changes_applied=0`
- felt- og fingeravtrykkskontroll bekreftet at eksisterende `PHONE`, samtlige `EMAIL`, direkte persontelefoner og relevante Organization-/OrganizationPerson-publiseringsflagg var uendret
- Editor-API viste de fire nye radene som primære og private; aktivt PUBLIC API og PUBLIC HTML eksponerte ingen av dem
- PostgreSQL readiness, Django system check, migrasjoner, HTTPS og `122` av `122` PUBLIC-kortlenker var fortsatt grønne etter kjøringen

Prosjekteier kontrollerte deretter undersøkelseseksemplet visuelt i staging og bekreftet at telefonen finnes under Kontaktkanaler, at Primær er valgt og at «Gjør dette telefonnummeret offentlig» er avslått. De øvrige tre kandidatene var allerede verifisert gjennom preflight, felt- og fingeravtrykkskontroll, Editor-API og PUBLIC-smoke. Denne uttrykkelige produktgodkjenningen lukket fase 2 den 2026-07-30.

## Implementert

- tenant-basert CRM for aktører og personer
- koblinger mellom aktører og personer
- flere kontaktkanaler per person
- kategorier, underkategorier og tenant-spesifikke tags
- roller via `TenantMembership`
- intern React-editor med rollebasert tilgang
- public API for publiserte aktører
- public HTML-visning, foreløpig kun brukt i staging
- PUBLIC HTML-detaljsider med kanonisk ID-rute og legacy orgnummer-redirect
- felles PUBLIC-regel for personkontakt i HTML og API: aktiv kobling med `publish_person=True` og kontaktkanal med `PersonContact.is_public=True`
- synkronisering mellom `Person.email`/`Person.phone` og primær intern `PersonContact`
- importjobber med opplasting, parsing, normalisering, preview, validering, matching, AI-forslag, review, beslutninger, commit, commit-logg og feilrapport
- grunnmodell og grunn-API for eksportjobber
- Docker-basert lokal kjøring og stagingoppsett

## Delvis implementert

### EXPORT

`ExportJob`, eksporttyper, CSV/XLSX-formatvalg, filtre, feltvalg og grunnleggende API finnes. Faktisk filgenerering, nedlasting og komplett brukerflyt er ikke bekreftet ferdig.

### PUBLIC

Public API og HTML-visning fungerer. HTML-visningen brukes foreløpig bare i staging. Endelig API-kontrakt og integrasjon mot Musikkontoret.no er ikke ferdigstilt.

### Roller og tilgang

Kjerne-rollene og tenant-scope håndheves i backend. Invitasjonsflyt, full administrasjon av medlemmer og den langsiktige modellen for eksterne tenant-rom må videreutvikles.

## Prioritert produktrekkefølge

### 1. Staging- og frontend-baseline – gjennomført 2026-07-29

Før det endres kode eller deployes, skal en skrivebeskyttet diagnose fastslå:

- repo-commit på serveren
- faktisk commit og bygg i kjørende containere
- om frontend-bundles, statiske filer, bilder eller cache er utdaterte
- påvirkning fra nginx, Caddy og nettlesercache
- forskjeller mellom lokal `main` og staging
- hvilke observerte avvik som er reelle regresjoner på `main`

### 2. Liten kontaktstabilisering – gjennomført 2026-07-30

Den avgrensede mellomleveransen sporer offentlig telefon gjennom Editor, API og PUBLIC, viser `Person.title` offentlig når den finnes og har regresjonstester for e-post, telefon, personlenke og tittel. Den generelle årsaken ble rettet, fire legacytelefoner ble reparert privat etter backup, og teknisk og visuell stagingkontroll ble godkjent. Dette er ikke full implementering av [ADR-005](../decisions/ADR-005-CONTACT_ARCHITECTURE.md).

### 3. Thumbnail-, bilde- og kortarkitektur – fase 3B.2 gjennomført og besluttet

Fase 3A-kartleggingen, ADR-007 og de isolerte prototypene i fase 3B.1 og fase 3B.2 er gjennomført. Prosjekteier har godkjent tilhørende processing-, storage-, delivery-, takedown- og restoreprinsipper, og ADR-008s lokale Hetzner-MVP er ACTIVE. Fase 3C er startet med en avslått featureflag og separate, ubrukte lokale image-storagealiaser. Modeller, filskriving, serving og offentlig bildebruk er fortsatt ikke implementert; fase 3B.1R og øvrige kvalitetsgater må være grønne før reell bildebruk kan aktiveres.

Deretter skal Import 2.0 gjennom en egen produkt- og UX-designfase før større kodeendringer. Dagens importmotor skal gjenbrukes der den er solid, men skal ikke låse den nye brukeropplevelsen.

Detaljert faseinndeling, AI-prinsipp og senere produktområder finnes i [ROADMAP.md](ROADMAP.md).

## Verifisert kontaktstatus

### Implementert mellomregel

Første mellomleveranse er implementert og deployet til staging. Problemet skyldte en todelt kontaktarkitektur og forskjellige regler i Editor, import og PUBLIC:

- `Person.email` og `Person.phone` er parallelle med `PersonContact`
- Editor viste og lagret i hovedsak direktefeltene
- enkelte opprettingsflyter skriver både direktefelt og `PersonContact`
- public API brukte eksplisitte `PersonContact`
- public HTML kunne falle tilbake til direkte person-e-post
- import kunne oppdatere begge kilder og endre publiseringsflagg

Implementert mellomregel:

- `OrganizationPerson.publish_person` bestemmer om personen vises som kontaktperson offentlig
- `PersonContact.is_public` bestemmer om hver e-post eller telefon vises offentlig
- `Person.email` og `Person.phone` brukes ikke som PUBLIC-fallback
- Editor CRM er intern og viser kontaktkanaler også når de ikke er offentlige
- import støtter `person_email_public` og `person_phone_public` som tri-state publiseringsfelt
- `repair_person_contacts` kan opprette manglende private primære e-postkontakter fra `Person.email`
- `repair_person_contacts --contact-type PHONE --tenant musikkontoretnord --apply` ble kjørt kontrollert på staging 2026-07-30 etter backup og opprettet fire private primære telefonkontakter uten å endre publiseringsflagg
- `publish_existing_email_contacts` ble kjørt på staging 2026-07-26 etter backup og gjorde eksisterende e-postkontakter offentlige, med tre relasjonsspesifikke unntak på `publish_person=False`

Staging etter datakjøringen:

- `email_contacts_total=164`
- `email_contacts_public=164`
- `email_contacts_private=0`
- `active_links_total=170`
- `active_links_publish_true=167`
- `active_links_publish_false=3`

De tre unntakene er:

- `Nordland fylkeskommune` / `Kathrine Schjem`
- `Nordland fylkeskommune` / `Ole-Thomas Kolberg`
- `Bådin` / `Jonas Jørgensen Moe`

Målarkitekturen er godkjent i `docs/decisions/ADR-005-CONTACT_ARCHITECTURE.md`:

- `PersonContact` blir eneste autoritative kilde
- primærkontakt og offentlig kontakt holdes adskilt
- offentlige kontaktkanaler velges per aktør–person-kobling
- HTML, API og Editor-preview bruker én offentlig projeksjon
- migreringen gjennomføres additivt og reverserbart

Den langsiktige ADR-005-modellen er ikke implementert. Direktefelt finnes fortsatt av kompatibilitetshensyn, og dagens `PersonContact.is_public` er fortsatt globalt for kontaktkanalen, ikke relasjonsspesifikt.

## Godkjent fremtidig retning for internasjonal telefon

Den konservative PHONE-reparasjonskommandoen fra fase 2 beholdes uendret som en avgrenset legacy-reparasjon. Internasjonal telefonarkitektur blokkerer ikke fase 3.

Godkjent beslutningsgate og tidsplan:

- et eget ADR for internasjonal telefonmodell, landkontekst og normalisering skal utarbeides ved overgangen fra fase 3 til fase 4
- fase 4, produkt- og UX-design for Import 2.0, kan ikke godkjennes som ferdig før dette ADR-et er godkjent
- den nye telefonarkitekturen skal implementeres tidlig i fase 5
- en stabil internasjonal telefonmodell er en forutsetning for full telefonmatching i fase 6

Det senere ADR-et skal bygge på disse godkjente prinsippene:

- original/raw telefonverdi bevares
- normalisert sammenligningsverdi lagres separat
- nasjonale numre får uttrykkelig land-/regionkontekst
- fullstendige internasjonale numre støttes
- internnummer kan håndteres separat
- én sentral backendtjeneste brukes av Editor, API, import, eksport og reparasjonsverktøy
- tvetydige verdier går til review og slås ikke sammen automatisk
- normalisering og matching aktiverer aldri publisering

Denne retningen er besluttet, men telefonarkitekturen er ikke implementert og et nytt ADR er ikke opprettet eller godkjent.

## Planlagt senere

- Google Sheets som importkilde
- Checkin som importkilde
- Mailmojo som importkilde
- komplett eksportmotor
- auditlogg og sterkere sporbarhet

Google Sheets, Checkin og Mailmojo finnes foreløpig bare som reserverte kildetyper.

## Separat infrastrukturløp

Sikker automatisk staging-deploy er planlagt utenfor produktfasene og blokkerer ikke fase 1. Manuell og kontrollert deploy gjelder inntil det finnes en testet kjede med minst privilegert deploy-bruker, GitHub Environment og secrets, grønn obligatorisk CI på `main`, deploy-lås, databasebackup, health/smoke-kontroll, rollback og tilstrekkelig logging/hardening. Serverens root-nøkkel skal ikke lagres som GitHub-secret.

## Teknisk workflow-status

- GitHub er felles sannhetskilde mellom lokal kode, Codex og ChatGPT.
- ChatGPT kan lese repoet når prosjekteier ber om oppdatert analyse.
- Fredrik Development System er installert som prosjektets utviklingsplattform.
- Repo-reglene ligger i `AGENTS.md`, og 15 prosjektbaserte Codex-skills ligger i `.agents/skills/`.
- `$fortsett-prosjekt` er installert som en tynn Codex-bro fra ChatGPT-handoff til `$start-arbeidsokt`; ChatGPT-rutinen med samme navn er dokumentert separat.
- `$start-arbeidsokt` og `$avslutt-arbeidsokt` danner et skrivebeskyttet SESSION-lag rundt de fire arbeidsnivåene, i tråd med `ADR-006`.
- Alle 15 skills er strukturelt validert. `$fortsett-prosjekt` er eksplisitt runtime-testet i en ny skrivebeskyttet Codex-session med konfliktmerking, full delegering til `$start-arbeidsokt` og uendret arbeidsmappe.
- Fredrik Skill Pack, ChatGPT og Codex er prosjektets valgte arbeidsverktøy. Claude eller Superpowers er ikke valgt som en parallell arbeidsflyt; nyttige prinsipper fra andre rammeverk kan innarbeides i det eksisterende systemet når de gir konkret verdi.
- Codex skal lese `docs/README.md`, dette dokumentet og relevant feature-/arkitekturdokument før implementering.
- Større implementeringer krever godkjent ADR.
- Funksjonelle endringer skal ledsages av dokumentasjonsoppdatering eller eksplisitt vurdering av at dokumentasjonen fortsatt er korrekt.
- Automatisk staging-deploy er et separat infrastrukturløp og er ikke implementert eller verifisert.

## Åpne avklaringer

- valgt mekanisme for automatisk staging-deploy
- obligatoriske tester og CI-gates før deploy
- endelig kontrakt mellom CRM-public og Musikkontoret.no
- lokal private/public-storage, same-origin/media-origin-serving, cache/purge/verifikasjon, permanent journalteknologi/read-model/cursor og full katastrofe-RTO; S3/CDN og provider-spesifikke gater tas bare opp igjen ved dokumentert behov
- representative pixel-/dimensjons-/kvalitetsgrenser, sRGB-/fargeprofilkontrakt, SVG-policy, eventuell sikker rasterisering/skadevarekontroll/bakgrunnskø, API-schema, aliasmapping, public release key-struktur, concurrency/databaseconstraints, retensjonsmekanisme, sync/async-grense og observability i fase 3B
- eksplisitt publiseringsfelt for organisasjonens e-post
- roller for kontaktpublisering, bulkpublisering og full kontakt-eksport
- behandlingsgrunnlag og retensjon for kontakt-, import-, eksport- og auditdata
- versjonering av ny public kontaktkontrakt
- om personens offentlige tittel senere skal være koblingsspesifikk
- bibliotek og konkret normaliseringsstandard for internasjonale telefonnumre
- modell- og feltnavn, constraints og API-kontrakt for originalverdi, normalisert sammenligningsverdi, land-/regionkontekst og internnummer
- migrerings-, backfill-, konfliktreview- og rollbackopplegg for eksisterende telefondata

## Dokumentasjonsstatus

`docs/` er autoritativ dokumentasjonsstruktur og er kvalitetssikret på overordnet nivå mot dagens kodebase. PR #10 fullførte session-workflowen og holdt gamle rotbaserte handoff-, `REFERENCE`- og `STATUS`-filer utenfor repoets parallelle sannhetskilder. Den godkjente produktrekkefølgen er dokumentert i [ROADMAP.md](ROADMAP.md).
