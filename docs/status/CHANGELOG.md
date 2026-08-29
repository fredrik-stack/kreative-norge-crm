# Changelog

## 2026-08-30

### Fase 4 formelt lukket etter endelig owner-smoke

- registrert at prosjekteier gjennomførte siste manuelle kontroll og godkjente
  de tre gjenstående UI-punktene 2026-08-29; se
  [owner-approval-notatet](PHASE_4_OWNER_APPROVAL_2026-08-29.md)
- bekreftet at fase 4A–4H, samlet teknisk stagingverifikasjon, første
  owner-smoke-remediation og andre owner-smoke UI-polish er gjennomført og
  reverifisert
- satt autoritativ status til `PHASE 4 = CLOSED / VERIFIED` og registrert at
  ADR-010 er implementert innen avtalt fase-4-scope
- bevart ADR-005 som delvis implementert: global `PersonContact.is_public`
  sammen med aktørspesifikk `publish_person` er fortsatt en mellommodell;
  relasjonsspesifikk kontaktpublisering og øvrig migrering kommer senere
- satt fase 5 – produkt- og UX-design for Import 2.0 – som neste aktive
  produktfase uten å starte planlegging eller implementering
- ingen kode-, runtime-, data-, staging- eller produksjonsendring; deploy er
  ikke relevant for denne dokumentasjons-close

## 2026-08-29

### Siste UI-polish etter andre owner-smoke teknisk stagingverifisert

- fjernet Organization-telefon fra hovedkortene i aktøroversikten, men beholdt
  den i oversiktsmodal, redigering og søk
- lagt til backend-avledet read-only landkodehint for utenlandske nasjonale
  telefonformater i interne Organization-, Person- og PHONE-
  `PersonContact`-responser; frontend viser råverdi med hint og bruker fortsatt
  canonical `tel:`-mål uten hardkodet landkart
- endret koblingsknappen fra `Rediger kontaktkanaler` til `Rediger`
- beholdt public API-shape, råverdier, canonical identitet og
  publiseringssemantikk uendret; ingen schema- eller dataendring
- verifisert lokalt med 570 backendtester, 41 frontendtester, 17
  Playwright-tester, produksjonsbuild, begge produksjonsimages, Django-check og
  ingen migrasjonsdrift; PR- og main-CI er 6/6 grønne
- deployet eksakt merge `c502701`, verifisert rollback-transaksjon,
  uendret publiseringsfingerprint, public API-shape, byteeksakt frontendbundle,
  PUBLIC projection og safety `READY` uten persistente testdata; se
  [stagingevidensen](STAGING_PHASE_4_OWNER_SMOKE_UI_POLISH_2026-08-29.md)
- status holdes eksakt på
  `PHASE 4 TECHNICALLY VERIFIED / READY_FOR_OWNER_SMOKE`

### Tre owner-smoke-funn rettet og teknisk stagingreverifisert

- beholdt svensk/nasjonal råtelefon som visning og lagt read-only servergenerert
  `phone_dial_uri` fra lagret canonical E.164 for Organization, Person og PHONE-
  `PersonContact`; manglende canonical identitet gir ikke-klikkbar råtekst
- vist Organization-telefon på interne aktørkort og i oversiktsmodal uavhengig
  av `publish_phone`, med offentlig status som separat merking
- forklart alle effektive kombinasjoner av `publish_person` og
  `PersonContact.is_public` i aktørredigeringen og presisert «Kan vises
  offentlig» i personredigeringen uten å koble eller endre flaggene
- beholdt public API-shape og publiseringssemantikk; PUBLIC HTML bruker canonical
  dialmål når det finnes og rå synlig tekst
- verifisert lokalt og i grønn PR-/main-CI med 568 backendtester, 38
  frontendtester, 17 Playwright-tester, produksjonsbuild, Django-check og ingen
  migrasjonsdrift
- deployet eksakt merge `589b86f`, verifisert svensk/norsk raw/canonical,
  uendret publiseringsfingerprint, PUBLIC, bundlehash og image/safety uten
  persistente testdata; se [stagingevidensen](STAGING_PHASE_4_OWNER_SMOKE_REMEDIATION_2026-08-29.md)
- andre owner-smoke gjenstår, så status er fortsatt
  `PHASE 4 TECHNICALLY VERIFIED / READY_FOR_OWNER_SMOKE`

## 2026-08-26

### Fase 4 teknisk verifisert og klar for prosjekteiers smoke

- gjennomført samlet 4H-gate på eksakt 4G-merge `d9b0589` for additivt schema/defaults, Editor, API, Import, matching, cross-tenant, PUBLIC og backfill-idempotens
- verifisert synlig staging-UI med Playwright, fire gyldige internasjonale/nasjonale varianter, invalid, extension og separat clearing uten publiseringssideeffekt; alle testdata og midlertidig bruker ble slettet eksakt
- kjørt åtte transaksjonelle importrader med `VALID`, `INVALID`, `NEEDS_REGION`, `KEEP`, region-snapshot, identisk retry og ingen automerge; tre testfiler ble slettet
- beholdt rå-/publiseringsfingerprints eksakt, backfill-dry-run `0`, PUBLIC `122 = 1 asset + 121 fallback`, safety `READY` cursor 13, ni deliveryfiler og restarttellere `0`
- kjørt full sluttmatrise med 560 backendtester, 31 frontendtester, produksjonsbuild, Django-check og ingen migrasjonsdrift
- tatt post-4H-backup `kreative-norge-staging-20260826T061135Z`, fullverifisert repository/archive-data og verifisert `0032`, tellinger, regions-/canonical state, fingerprints, image og safety på isolert restorekopi
- dokumentert [samlet 4H-evidens](STAGING_PHASE_4H_PHONE_TECHNICAL_VERIFICATION_2026-08-26.md); status er `PHASE 4 TECHNICALLY VERIFIED / READY_FOR_OWNER_SMOKE`, mens fase 5 og produksjon ikke er startet

### Fase 4G kontrollert backfill anvendt og verifisert i staging

- merget PR #64 som `d9b0589acee433034acb2706f204383361049a41` etter frozen-head-review uten funn og seks grønne PR-/main-CI-jobber
- tatt og fullverifisert backup `kreative-norge-staging-20260825T234721Z`, samt bevist isolert apply/rollback mot ekte restorekopi før live write
- anvendt batch `phase4g-staging-20260825T235228Z` med 61 additive endringer: 3 tenantregioner, 2 Organization-identiteter og 56 PHONE-kontaktidentiteter
- bevart råtelefon og publiseringsfingerprints eksakt, kontrollert restriktivt no-clobber rollbackmanifest uten raw/new canonical payload og avsluttet med to identiske dry-runs på `0`

### Fase 4G kontrollert telefonbackfill implementert; staging apply gjenstår

- lagt dry-run-first, tenant-scopet og idempotent `backfill_phone_identity` med eksplisitt `--apply`, eksakt tenantgate og aggregert personvernredigert output
- backfiller bare tenantregion og gyldige additive Organization-/PHONE PersonContact-felt, mens råtelefoner, Person, OrganizationPerson, primærstatus og publisering aldri skrives
- verifiserer eksisterende canonical identitet og Person/primær PHONE-paritet fail-closed; ugyldige og regionløse verdier beholdes med canonical `NULL`
- krever unik batch-ID og restriktivt no-clobber rollbackmanifest uten råtelefon utenfor Git; rollback gjenoppretter bare batchfeltene og stopper ved senere drift
- rapporterer klassifisering og faktiske endringer per modell/tenant/resultat samt rå-, publiserings- og additiv fingerprint
- dokumentert obligatorisk dobbel tørrkjøring, Borg-backup, isolert restore/rollback og post-apply idempotens i [operatørprosedyren](../operations/PHONE_BACKFILL.md)

### Fase 4F READY_FOR_4G etter Import-stagingverifikasjon

- merget PR #63 som `9119b03e263bc7c848b3b2e32db9b7a41d9e4964` etter frozen-head-review uten funn og seks grønne PR-/main-CI-jobber
- verifiserte eksplisitt `NO`, snapshot/default/null-kontekst, `VALID`, `INVALID`, `NEEDS_REGION`, blank `KEEP`, commit-skip og uendret publisering med små syntetiske stagingfiler
- rullet alle syntetiske databaserader tilbake, fjernet begge opplastede filer og bekreftet identiske katalog-/Import-fingerprints før og etter
- beholdt PUBLIC `122/122`, projection `1 asset + 121 fallback`, safety `READY` cursor 13, ni deliveryfiler og restarttellere `0`; fase 4F er `READY_FOR_4G`

### Fase 4F Import-telefonkontrakt implementert; staginggate gjenstår

- fryser eksplisitt jobbregion, tenantdefault eller `null` i hver `ImportJob` uten skjult Norge-default og viser snapshotet i Editor
- klassifiserer ikke-tomme telefoner som `VALID`, `INVALID` eller `NEEDS_REGION`, mens blank input er `KEEP` uten adapterkall
- bruker canonical E.164 som sterkt tenant-scopet `NAME_AND_PHONE`-signal, men aldri telefon alene eller tvetydige treff som automatisk personmerge
- committer bare gyldig råverdi/canonical identitet/faktisk brukt region og bevarer eksisterende telefon ved blankt eller usikkert utfall
- lar telefonnormalisering og matching stå helt uten publiseringswrite; bare eksplisitte importkolonner kan endre publiseringsflagg
- beholder kontrollert eksakt råverdi-fallback frem til fase 4G-backfill og har ingen schema- eller migrasjonsendring

### Fase 4E READY_FOR_4F etter API- og synlig Editor-stagingverifikasjon

- merget PR #62 som `8315c404f719f823f59eb1f104f7e5e921f9c02d` etter separat frozen-head-review uten funn og seks grønne PR-/main-CI-jobber
- deployet eksakt merge og verifiserte norsk, svensk, internasjonal, ugyldig og regionløs Organization-/Person-telefon gjennom API og synlig Editor
- beholdt publiseringsflagg, tenantdefault og alle katalogfingerprints uendret etter full opprydding av syntetiske rader og bruker
- beholdt PUBLIC/API/image/safety grønt og restarttellere på null; fase 4E er `READY_FOR_4F`

## 2026-08-25

### Fase 4E Editor/internal telefon-write implementert; staginggate gjenstår

- koblet Organization, Person og PHONE-`PersonContact` til den felles 4C-adapteren gjennom én backend-writegrense
- la til eksplisitt `phone_region`, read-only tenantdefault og intern `phone_region_used` uten å eksponere canonical E.164 offentlig
- la til synlig regionvalg i Organization-, Person- og kontaktredigering med per-telefon override og regionuavhengige `+`-numre
- bevarte rå presentasjonsverdi og publiseringsflagg, synkroniserte primær personkontakt og hindret incidental backfill ved unrelated save
- verifiserte 4D i staging på merge `0198269892b7e59143393b4ed3f104098e81a24e`: backup/restore, migrasjon `0032`, alle nye felt `NULL`, uendrede rå-/publiseringsfingerprints, isolert reverse/forward og grønne API/PUBLIC/image/safety-gater

## 2026-08-25

### Fase 4D additiv telefonmodell implementert; staginggate gjenstår

- lagt nullable `Tenant.default_phone_region` uten modell- eller database-default; nye tenants får fortsatt ingen skjult region
- lagt canonical sammenligningsverdi og faktisk brukt normaliseringsregion på `Organization` og PHONE-`PersonContact`, men bevisst ingen normalisert verdi på legacyfeltet `Person.phone`
- lagt databaseconstraints for E.164-form, uppercase regionform, region-avhengighet og PHONE-scope samt tenant-scopede oppslagsindekser
- håndhevet unik normalized telefon bare innen tenant + person + kontakttype; samme telefon er fortsatt tillatt for ulike personer og organisasjoner
- lagt schema-only migrasjon `0032` uten backfill; eksisterende råverdier, publiseringsflagg og API-kontrakt er uendret
- testet forward/reverse fra realistiske eksisterende rader; reverse blokkeres etter at additive telefonidentitetsdata er lagret
- beholdt 4C-adapteren uten callers; Editor-, Import- og kontrollert legacybackfill kommer i separate 4E–4G-gater

### Fase 4C READY_FOR_4D etter API-only stagingverifikasjon

- merget implementerings-PR #59 som `b9cc84e` etter separat frozen-head-review med `0 BLOCKER/HIGH/MEDIUM/LOW` og grønne 6/6 PR-/main-CI-runs `32891948790`/`32892503493`
- deployet eksakt merge ved å bygge og rekreere bare API; den kjente Compose 1.29.2-`ContainerConfig`-feilen ble håndtert med dokumentert API-only stop/remove/recreate, mens database og web beholdt identiske containere
- verifisert `phonenumbers==9.0.37`, identisk host-/containerhash for adapteren og syntetisk `VALID`, `NEEDS_REGION`, `INVALID`, regionuavhengig `+`, extensionavvisning og E.164-idempotens
- klassifisert faktiske 4B-data to ganger med `region=None` i read-only transaksjoner: Organization 2 `NEEDS_REGION`; Person 54 `NEEDS_REGION` + 1 `VALID`; PHONE-kontakt 55 `NEEDS_REGION` + 1 `VALID`
- bevist identiske Organization-, Person-, PHONE PersonContact- og OrganizationPerson-fingerprints før/etter, uten råverdier, datawrite, schema, migrasjon, API, Editor, Import, matching, repair, backfill eller publiseringsendring
- beholdt PUBLIC `122/122`, image projection `1 asset + 121 fallback`, ni deliveryfiler med uendret manifest og safety `READY` cursor 13; se [4C-evidensen](STAGING_PHASE_4C_PHONE_NORMALIZATION_2026-08-25.md)
- klassifisert fase 4C `READY_FOR_4D` og stoppet før 4D

### Fase 4C normaliseringsdomene implementert; stagingverifikasjon gjenstår

- pinnet `phonenumbers==9.0.37` og kapslet biblioteket bak én ren intern adapter uten Django-, modell-, settings-, database-, nettverks-, fil-, logg-, tenant- eller entitykobling
- lagt immutable typed resultat med eksakt `VALID`, `INVALID` og `NEEDS_REGION`, E.164 bare ved gyldig resultat, valgfri faktisk brukt region og stabile ikke-sensitive årsakskoder
- håndhevet eksplisitt region for nasjonale numre uten skjult Norge-default, regionuavhengige `+`-numre, bibliotekstyrte `00`-/IDD-regler, gyldighetskontroll og eksplisitt avvisning av extensions
- dekket kontrakten med syntetiske tester for Norge, Sverige og Storbritannia, ugyldige/kontekstløse verdier, idempotens, determinisme, personvern og alle definerte årsakskoder
- beholdt modeller, migrasjoner, data, API, Editor, Import, matching, repair, backfill og publisering uendret; stagingdeploy og evidence-PR gjenstår før `READY_FOR_4D`
- dokumentert domenekontrakten i [Phone normalization domain](../architecture/PHONE_NORMALIZATION.md)

### Fase 4B skrivebeskyttet telefonbaseline READY_FOR_4C

- kjørt to separate PostgreSQL-inventar i eksplisitte transaksjoner med `transaction_read_only=on`; hele aggregatresultatet var byteidentisk og fingerprints for Organization, Person, PHONE PersonContact og OrganizationPerson var uendret
- kartlagt alle tre tenants: 128 organisasjoner med 2 telefoner, 157 personer med 55 direkte telefoner, 56 primære PHONE-kontakter og 176 OrganizationPerson-lenker, uten tenantavvik, flere primærkontakter, direktefelt/primærkontakt-avvik eller delte eksakte persontelefoner
- dokumentert syntaktisk profil uten E.164-påstand: 111 av 113 ikke-tomme lagringsrader mangler eksplisitt internasjonalt prefiks, 2 starter med `+`, 0 med `00`, og 10 lagringsrader er syntaktisk uvanlige fordi fem samsvarende person-/kontaktrader forekommer i begge lagringssteder
- bevart personvern ved bare å lagre tellinger, kategorier og SHA-256-digests; ingen rå telefoner, navn, e-post, eksport, dump eller screenshots ble lagt i Git eller rapport
- verifisert samme stagingrepo, container-ID-er, images, starttider og restartteller `0` før/etter; ingen dependency, kode, migrasjon, data, konfigurasjon, restart, recreate eller deploy ble utført
- klassifisert resultatet `READY_FOR_4C` i [4B-evidensrapporten](STAGING_PHASE_4B_PHONE_BASELINE_2026-08-25.md); 4C er ikke startet

### Fase 4A: internasjonal telefonarkitektur dokumentert

- opprettet foreslått [ADR-010](../decisions/ADR-010-INTERNATIONAL_PHONE_IDENTITY_AND_NORMALIZATION.md) som presiserer ADR-005 med E.164-identitet, libphonenumber-modellen, eksplisitt regionkontekst og typed gyldig/ugyldig/tvetydig utfall
- fastlagt én telefonkontrakt for `PersonContact` og `Organization.phone`, med bevart presentasjonsverdi og additiv kanonisk sammenligningsverdi
- fastlagt at lik E.164 er et sterkt matchsignal, men ikke global unik personidentitet eller grunnlag for automatisk merge
- delt fase 4 i 4A–4H: ADR, skrivebeskyttet databaseline, normaliseringsdomene, additiv modell, Editor, importkontrakt, kontrollert backfill og stagingverifikasjon
- flyttet produkt-/UX-design for Import 2.0 og de senere kontakt-, Import- og eksportfasene ett fasenummer frem i roadmapen
- beholdt fase 3 og 3F `CLOSED / VERIFIED`; ingen kode, dependency, modell, migrasjon, data, staging, deploy eller bildearkitektur ble endret
- stoppet før 4B; extensions er utenfor MVP/fase 4, og ADR-010 må reviewes, prosjekteiergodkjennes og merges før databaseline starter

### Fase 3F og fase 3 CLOSED / VERIFIED

- merget implementasjons-PR #54 som `438a480` etter endelig frozen-head-review med `0 BLOCKER/HIGH/MEDIUM/LOW` og seks grønne PR-/main-CI-jobber
- tatt fullverifisert og isolert restore-verifisert predeploy-backup `kreative-norge-staging-20260824T230354Z`, deployet eksakt merge og anvendt additiv migrasjon `0031` uten backfill
- kjørt byteidentisk aggregert legacyinventar to ganger, bevist gate av → på → av og verifisert no-network/no-write, KEEP/SET/FALLBACK, scope/stale/deny/idempotens og eksisterende import på isolerte syntetiske data
- bevart normal public katalog `122 = 1 asset + 121 systemfallback`, safety `READY` cursor 13, fire releases, permanent denyhistorikk og ni deliveryfiler med uendret manifest
- bevist older DB/media mot nyere safety-ledger, kjørt orphan dry-run med 0 eligible/0 slettet og tatt fullverifisert/isolert restore-verifisert postdeploy-backup `kreative-norge-staging-20260824T231112Z`
- avsluttet shared staging med `IMPORT_IMAGE_DECISIONS_ENABLED=False`; Import 2.0-UX, telefon-ADR/fase 4, fysisk legacyfeltdropp, generell retensjon og providerpurge er ikke startet; se [3F-rapporten](STAGING_PHASE_3F_LEGACY_IMPORT_2026-08-25.md)

## 2026-08-24

### Fase 3F legacyovergang og typed Import-bildekontrakt implementert default-off

- lagt additiv migrasjon `0031` med én typed `ImportImageDecision` per `ImportRow`, immutable review-/actor-/approval-snapshots og beskyttet én-til-én-binding til anvendt `ImageReviewEvent`, uten backfill av eksisterende importdata
- lagt fail-closed `IMPORT_IMAGE_DECISIONS_ENABLED=False`; typed apply revaliderer tenant, actor, selection/revisjon, asset/rendition-sett og approval, gjenbruker selectionkommandoene, er idempotent og endrer ingen publiserings- eller release-state
- fjernet automatisk Open Graph-refresh fra vanlig Organization create/update og import-commit; legacy URL-feltene er read-only, mens eksplisitt refresh-endepunkt beholdes
- lagt read-only `audit_legacy_image_sources` og tenant-scopet `GET images/legacy-candidates/`; listing bruker bare DB/safety, redakterer operatørdetaljer og starter ingen DNS/HTTP, automatisk preview eller approval
- oppdatert Editor med separat legacykandidatgruppe og eksplisitt previewvalg, og lagt backend-, migrasjon-, frontend- og browserregresjoner for no-network/no-write, tenant/stale/idempotens og bevaring av eksisterende selection
- beholdt Import 2.0-produkt-/review-UX, fysisk legacyfeltdropp, generell retensjon/providerpurge og telefon-/fase 4-arbeid utenfor leveransen; separat review, merge, backup og staging-/restoregate gjenstår før `CLOSED`

### Fase 3E.4 CLOSED / ACTIVE i staging

- merget PR #52 som `087026e` etter separat frozen-head-review uten BLOCKER/HIGH/MEDIUM og seks grønne PR-/main-CI-jobber
- tatt fullverifisert predeploy-backup, oppgradert den ekte safety-ledgeren additivt fra schema v1/cursor 7 til schema v2 med uendret ledger-ID og bevart v1-historikk, og aktivert writegaten bare i ignorert stagingkonfigurasjon
- utført én permanent syntetisk release-/tenant-checksum-deny via intern API; ankret cursor 11 før fallback/origin-delete og bevist `404/no-store`, ingen gammel ETag-`304`, Cloudflare `BYPASS` og tre fjernede originfiler
- bevist idempotent retry, samme-byte approval/restore/release-blokkering, full 3E.3-rollback med aktiv legacyguard og fysisk mediarestore som fortsatt var 404/fallback og ble fjernet kontrollert
- republisert ny syntetisk source-checksum som ny selection revision 3, release-UUID og tre keys; gammel release/checksum/URL forble denied
- restartet API/web/bridge, tatt og fullverifisert post-deny-backup `kreative-norge-staging-20260824T191855Z`, og unpublisert bare testaktøren uten å slette deny-/audit-/releasehistorikk
- avsluttet med safety `READY` cursor 13, normal katalog `122 = 1 asset + 121 systemfallback`, fire release-aggregater, ni deliveryfiler og kode-/eksempelstandard fortsatt av; se [stagingrapporten](STAGING_PHASE_3E4_TAKEDOWN_2026-08-24.md)

### Fase 3E.4 formell takedown implementert bak default-off skrivegate

- lagt additiv, transaksjonell safety-ledger schema-v2-upgrade som bevarer v1-events/hashes/ledger-ID/cursor/receipts og tilfører append-only tenant-checksum-deny og rebuildbar legacyguard uten PostgreSQL som parallell authority
- lagt smal bridge-`deny` som skriver release- og checksum-deny i én SQLite-transaksjon før synkron anchor, samt read-only `check_checksum`/`legacy_guard` og checksum-aware `authorize`
- lagt `PUBLIC_IMAGE_TAKEDOWN_ENABLED=False`, tenant-/rolleavgrenset intern API-action med lukket reason code, eksakt targetutledning, append-only `formal_takedown`-audit og ny systemfallback-selectionrevisjon
- lagt deny-first, canonical tre-filers no-follow origin-delete med idempotent missing/partial retry; release-DB, mappings, privat original, artifacts og historikk beholdes
- håndhevet tenant/checksum guard fail-closed ved approval/replacement, restore og releaseoppretting, og legacyguard uavhengig av 3E.3- og write-gatene
- testet v1→v2/replay/restore, atomisk deny, anchor-/DB-/partial-delete-crash, roller/cross-tenant, same-byte block, safe republish, older DB/media-state, projection/serving/API/PUBLIC, 404/no-store og gammel ETag uten 304
- beholdt stagingledger v1 og takedownskriving av; separat backup, upgrade, permanent syntetisk deny, cache-/restore-/republish-evidens og evidence-PR gjenstår før `CLOSED / ACTIVE`

### Fase 3E.3 CLOSED / ACTIVE i staging

- merget implementerings-PR #49 og aktiveringsblocker-fix PR #50 etter separate fullreviews uten funn og seks grønne CI-jobber per endelig head; endelig deployet merge er `e04220b`
- deployet først med schema/PUBLIC av, bevist legacybaseline og production fallback v1, og kjørt schema `OFF → ON → OFF → ON` og full PUBLIC `OFF → ON → OFF → ON` uten endret ledger-, DB- eller delivery-state
- aktivert én projection for target-API, PUBLIC list/detail, canonical, Open Graph og Twitter; bevist asset/fallback/unpublished, aliases, hostinvarians, privacy og ingen legacybilde i aktiv reise
- browserverifisert desktop/mobil, full fallbackkatalog, lange navn/overflow, credit-kontrakt og én-gangs static fallback med blank alt ved asset-bytefeil
- funnet og automatisk rollbacket en 299-query N+1 i den avsluttende staginggaten; rettet person-/kontaktprefetch og målt endelig API-liste til 11 queries for 122 aktører og 0,110–0,192 sekunder eksternt
- beholdt safety `READY` på cursor `7`, `122 = 1 asset + 121 systemfallback`, seks deliveryfiler med manifest `fb94a302...` og fullverifisert/isolert restore-verifisert backup `kreative-norge-staging-20260824T131620Z`
- beholdt kode-/eksempelstandardene av og stoppet før 3E.4, deny/retire, origin delete, purge og legacyopprydding; se [stagingrapporten](STAGING_PHASE_3E3_CUTOVER_2026-08-24.md)

### Fase 3E.3 API/PUBLIC/head-cutover implementert bak default-off gate

- lagt fail-closed `PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=False`, som krever projection, target-API-schema, controlled serving og gyldige origins uten å innføre tenant-enrollment
- koblet PUBLIC list/detail til samme read-only `PublicImageProjection` som API-et, med fixed-query prefetch, square i kort/hero, share i detail-head og ingen legacyresolver i aktiv branch
- lagt canonical fra konfigurert `PUBLIC_SITE_ORIGIN` + `reverse()`, Open Graph/Twitter, description-/alt-escaping, 160 × 160 desktopdetail, grønne tags, offentlig kreditering og én-gangs browserfallback ved asset-bytefeil
- gjort target-API-schema og aliasinvarianten klar for stagingaktivering: `thumbnail_image_url == preview_image_url == image.square.url`
- etablert production fallback v1 på ryddige canonical static-stier ved å kopiere de eksisterende, visuelt kontrollerte fallbackbytene eksakt; gamle emergency-stier beholdes for rollback/historikk og systemfallback har blank alttekst
- lagt settings-, API-, PUBLIC-, head-, safety-, host/proxy-, privacy-, fixed-query- og Chromium desktop/mobiltester uten modellendring eller migrasjon
- beholdt både API-schema- og PUBLIC-cutoverflagg av som kode-/eksempelstandard; stagingdeploy, kontrollert aktivering, rollback og visuell kataloggate gjenstår før 3E.3 kan markeres `CLOSED / ACTIVE`

### Fase 3E.2 CLOSED / SHADOW VERIFIED i staging

- merget implementerings-PR #47 som `90ff5e9` etter separat review med `0 BLOCKER`, `0 HIGH`, ett rettet performancefunn og grønne PR-/main-CI- og image-workflows
- tatt og fullverifisert backup `kreative-norge-staging-20260824T074240Z`, deployet eksakt merge uten migrasjon og rekreert bare API med begge nye gater først av
- bevist byteidentisk API list/detail, én canonical OpenAPI-route uten `image`, semantisk uendret PUBLIC og fortsatt controlled media før shadow
- aktivert bare projection-shadow og målt fullkatalogen til `122 = 1 asset + 121 systemfallback`, fem queries, tre authorize-kall, `0` safety-unavailable og `0` scopefeil
- bevist faktisk asset, teknisk fallback, unpublished fail-closed, seks HEAD `200`, sanitert logg og uendret safety cursor `7`, DB-radantall og seks deliveryfiler/checksummer
- bevist API-only rollback etter et avgrenset Compose 1.29.2-verktøyavvik, deretter rerunnet hele korrigerte gaten grønt
- beholdt `PUBLIC_IMAGE_PROJECTION_ENABLED=True` bare i ignorert stagingkonfigurasjon og `PUBLIC_IMAGE_API_SCHEMA_ENABLED=False`; PUBLIC/API bruker fortsatt legacybilder og 3E.3 er ikke startet
- dokumentert hele gaten i [stagingrapporten](STAGING_PHASE_3E2_SHADOW_2026-08-24.md)

### Fase 3E.2 projection og public API shadow implementert bak default-off gater

- konsolidert `/api/public/actors/` til `crm.urls_public`, `PublicActorPublicViewSet` og `PublicActorSerializer`, med `org_number` som detail-lookup og den shadowed duplikatruten/serializeren fjernet
- lagt read-only `PublicImageProjection` som gir eksakt `asset` eller `system_fallback`, autoriserer alle tre varianter gjennom eksisterende safety-`authorize` og bruker samme release-/scope-/mappinginvarianter som controlled serving
- gjenbrukt 3B.1s tre tekniske fallback-PNG-er byte-for-byte på versjonert Django-static-sti; endelig grafikk og fallback-alttekst gjenstår i 3E.3
- lagt target `image`-schema og aliaslikhet bak `PUBLIC_IMAGE_API_SCHEMA_ENABLED=False`, mens `PUBLIC_IMAGE_PROJECTION_ENABLED=False` styrer projection/shadow og begge standardverdier er fail-closed
- lagt detail-shadowlogging uten URLs/intern metadata og `audit_public_image_projection` for skrivebeskyttet fullkatalogmåling av projection, safetyutfall, legacydiff, query count og runtime
- lagt route-, legacy contract-, asset/fallback-, safety-, tenant/scope-, no-I/O-, query-, audit-, alias- og OpenAPI-tester uten ny modell eller migrasjon
- staging shadow-gaten er senere gjennomført separat; schema, PUBLIC, 3E.3 og formell takedown er fortsatt av

### Fase 3E.1C kontrollert serving aktivert og verifisert i staging

- presisert den plattformavhengige sockettesten etter gjentatt Linux-`ECONNRESET`: både reset og EOF godtas som transportutfall når en uautorisert peer avvises uten domenerespons; produksjonskode og stagingruntime er uendret
- merget de separat reviewede PR-ene #41–#44 og deployet eksakt sluttmerge `38663b5` etter grønn seks-jobbers main-CI-run `32668678789`
- aktivert bare det ignorerte stagingflagget `PUBLIC_IMAGE_SERVING_ENABLED=True`; kode- og eksempelstandard forblir `False`
- bevist canonical GET/HEAD og reautorisert 304 for square/landscape/share med identiske bytes, checksum-`ETag` og `private, max-age=60, must-revalidate`
- bevist tom `404/no-store` for ukjente/ikke-canonical/upubliserte releases, tom `405/no-store` for unsafe methods og tom `503/no-store` ved bridge- og filfeil
- bevist read-only `scope_mismatch`, socket activation, API/web/bridge-restart, Nginx-worker-GID `2000`, mountisolasjon, eksplisitte origins og sanitert structured logging
- verifisert at PUBLIC HTML/API, publisert aktørantall og permanent legacyredirect er uendret og ikke inneholder den aktive release-UUID-en
- tatt post-activation-backup `kreative-norge-staging-20260823T220249Z` med grønn full verify og isolert restore; 3E.1C er `CLOSED / ACTIVE`, mens 3E.2–3E.4, projection, PUBLIC-kobling og takedown fortsatt er uimplementert

## 2026-08-23

### Fase 3E.1C kontrollert serving implementert bak separat gate

- rettet pre-aktiveringsfunn der Compose `group_add` alene ikke overlevde Nginx-masterens privilegiedropp; web-imaget oppretter nå den faste GID-en og melder `nginx` eksplisitt inn i delivery-gruppen, med kontrakttest og krav om live worker-verifikasjon
- rettet livegatefunn der Nginx’ statiske filhandler erstattet checksum-ETag-en; auto-ETag er nå av bare i den interne delivery-locationen, som eksplisitt setter `ETag` fra `$upstream_http_etag` slik at Djangos reautoriserte checksum bevares
- rettet negative livegatefunn med tom `404/no-store`-catch-all for ikke-canonical mediaformer og avgrenset CSRF-unntak på den write-frie media-viewen, slik at andre metoder gir tilsiktet `405/no-store` før domenekall
- rettet pre-merge-observabilityfunn med en eksplisitt INFO-consolehandler for den strukturerte servingloggeren, slik at utfall, release-ID, variant, status, safety-kategori/cursor og varighet faktisk når containerloggen uten paths eller secrets
- lagt canonical `GET`/`HEAD /media/releases/<uuidv4>/<variant>.<ext>` gjennom Django med publiserings-, scope-, immutable mapping- og komplett tre-filers byteverifikasjon før intern Nginx `X-Accel-Redirect`
- utvidet den eksisterende lokale safety-broen med eksakt read-only `authorize`, parallelle lesere og writer-preferred lifecycle-gate uten Django-ledgermount, anchor-repair eller Borg-tilgang
- lagt read-only deliverymount i `web`, dedikert kollisjonssjekket hostgruppe/supplementary GID `2000`, setgid-/`0640`-kontrakt og en `internal` Nginx-location med symlinkforbud; private originaler, artifacts, safety-state og credentials forblir utenfor web
- lagt `PUBLIC_IMAGE_SERVING_ENABLED=False` som egen kode-/eksempelstandard og eksplisitte HTTPS-origins bundet til eksakte `DJANGO_ALLOWED_HOSTS`, uavhengig av requestens `Host`-/proxyheadere
- valgt foreløpig `private, max-age=60, must-revalidate`, checksum-`ETag`, `no-store` på 404/503 og ingen shared proxycache/`immutable`; projection, API/PUBLIC, legacy-cutover, takedown og 3E.2–3E.4 er ikke aktivert
- stagingaktiveringen er senere gjennomført og dokumentert separat; rollback er fortsatt bare servingflagget av og API/web-recreate

### Fase 3E.1B-materialisering aktivert og verifisert med public serving av

- fast-forwardet staging rent til `main` på merge `ee42c82`, verifisert grønn main-CI-run `32646334974`, 25 målrettede lokale tester og fersk pre-activation-backup med isolert restore
- aktivert bare `PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=True` og bevist hard no-clobber mot avvikende eksisterende bytes uten database-, ledger- eller permanent delivery-mutasjon
- kjørt permanent syntetisk reserve → DB-binding → kontrollert crash etter første fil → API-restart → materialisering/read-back → activate for release `248806b9-613c-4c1f-bcf5-64c5b15cfff9`
- bevist at første retry bevarte eksisterende fil og fullførte de to manglende, mens ny full retry opprettet ingen filer eller ledger-events; safety-ledgeren er `READY` på cursor `5`
- beholdt én sporbar syntetisk release og tre persistente delivery-filer, og verifisert dem i post-activation-backup `kreative-norge-staging-20260823T185950Z` med full repository-/arkivkontroll og isolert restore
- bekreftet at web mangler delivery-mount og Nginx-route, delivery-storage mangler `base_url`, og plausible URL-paths ikke serverer bildebytes; 3E.1C, projection, API/PUBLIC og offentlig bildebruk er fortsatt av
- dokumentert full evidens i [aktiveringsrapporten](STAGING_PHASE_3E1B_MATERIALIZATION_ACTIVATION_2026-08-23.md)

### Fase 3E.1B-foundation deployet og gateverifisert med materialisering av

- deployet eksakt PR #38-merge `d756b4b` etter grønn tomtabellpreflight og fersk Borg-backup; migrasjon `0029` ble anvendt uten backfill og release-count forble `0`
- installert og aktivert root-eid systemd socket/bridge, verifisert faktisk API-peer gjennom `SO_PEERCRED`, og bekreftet 5/45/50/60-sekunders timeoutkjede med bare `reserve`/`activate` caller-aktivt
- verifisert API-only delivery-/socketmount, fravær av ledger/Borg/credentials i API og fravær av delivery/safety/Borg i web; ingen Nginx-/Caddy-route eller offentlig media-URL ble lagt til
- bevist delivery-persistens gjennom API-containerutskifting og identisk SHA-256 i ny off-server backup, full repository-/arkivverifikasjon og isolert restore; den syntetiske live-proben ble fjernet etterpå
- beholdt `PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=False`, `0` releases og uendret safety-ledger-head; faktisk syntetisk reserve/materialize/retry/activate gjenstår som egen activation-gate
- dokumentert liveevidens og den kjente Compose 1.29.2-`ContainerConfig`-recoveryen i [stagingrapporten](STAGING_PHASE_3E1B_FOUNDATION_2026-08-23.md)

## 2026-08-22

### Fase 3E.1B.1–3E.1B.2: release-materialisering implementert, ikke stagingaktivert

- lagt fail-closed migrasjon `0029` med immutable positivt selection-revision-snapshot og unik release per selection; legacyrader stopper migrasjonen uten backfill eller automatisk reconciliation
- lagt atomisk safety-ledger-reservasjon, minimal root-eid AF_UNIX/systemd-bro for `reserve`/`activate` og streng framed JSON-client uten direkte ledger-/Borg-fallback i Django
- refaktorert release-tjenesten til idempotent snapshot → ankret reserve → revalidert DB-binding → create-only materialisering/read-back → ankret activation
- lagt separat `public_image_delivery` og `/srv/kreative-norge/media/public-delivery`, eksplisitt API-only compose/socket-mount og backupallowlist; ingen webmount, Nginx-route eller offentlig URL
- lagt migration-, protocol-, AF_UNIX-client-, no-clobber-, crash/retry-, materialiserings- og ekte PostgreSQL-concurrencytester
- beholdt `PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=False`; repository foundation er ikke deployet, restore-verifisert eller aktivert i staging

Dette dokumentet samler større brukermerkbare og arkitekturelle endringer. Små kosmetiske justeringer trenger ikke registreres.

## 2026-08-20

### Fase 3E.1B: materialisering og release-livssyklus arkitektonisk presisert

- presisert ADR-009 med en lokal fail-closed Unix-socket/systemd-bro som privilegieseparasjonsgrense; bare `reserve`, `activate`, `retire` og `deny` er autorisert, og API/web får fortsatt ingen ledger-mount, Borg eller credentials
- låst MVP-idempotens til maksimalt én public release per selection-revisjon, med gjenbruk av samme permanent reserverte UUID/canonical keys ved retry og ny selection-revisjon ved republisering
- beholdt lifecycle-authority i safety-ledgeren uten besluttet PostgreSQL lifecycle-kolonne, og avgrenset public delivery-cleanup til senere release-/ledger-aware dry-run/apply uten automatisk filsletting
- delt senere implementasjon i 3E.1B.1 for bro/reservation/DB-binding og 3E.1B.2 for separat delivery-root/materialisering/activation; ingen runtimekode, migrasjon, storage, serving eller stagingendring er utført

### Fase 3E.1A: safety-ledger og restore-gate aktivert i staging

- aktivert host-side SQLite safety-ledger, dedikert kryptert Borg off-server anchor og femminutters fail-closed health-timer uten safety-mount eller credentials i API/web
- verifisert forskjellig repository-ID fra ADR-008-backupen, separat recovery-custody for minst to ansvarlige, genesis og syntetisk reservation/ACTIVE/DENIED med synkron create/read-back/receipt
- bevist idempotent retry, konfliktavvisning, logical delete, compact exit `0` uten fysisk komprimering, writerens raw-`rm`-capability og separat transaction recovery av både probe og nyeste DENIED-head
- bevist at stale manifest med eldre ACTIVE-head avvises i incident restore før destination/receipt, mens separat recovery av autoritativ cursor/fullhash gir rebuildbar `DENIED` og `READY`
- bevist nyere safety-DENIED over eldre ACTIVE-state, isolert fail-closed corruption/stale cursor/repository mismatch og identisk ledger/receipts/repository-ID etter host-restart
- registrert prosjekteiers aksept av Borg/Hetzner- og raw-`rm`-restrisikoen; status er bare `ACTIVE` for 3E.1A og aktiverer ikke public bytes, materialisering, serving, PUBLIC, takedown eller 3E.1B–3E.4
- dokumentert full stagingevidens i [aktiveringsrapporten](STAGING_PHASE_3E1A_ACTIVATION_2026-08-20.md); rapportens draftstatus beskriver aktiveringsøyeblikket, mens PR #36 senere er merget til `main`

## 2026-08-11

### Fase 3D.2: flere bildekilder, synlig søk og fokus-UX merget til main

- merget PR #33 til `main` som `48f23f183dacb8331a64b86f1d7574250cbfbe02`; alle fem jobber i main-CI-run `31535260891` er grønne på eksakt mergecommit

- bevart den grønne Brave-liveverifikasjonen som historisk evidens, men deaktivert staging-credentialen etter testen; bare API ble rekreert, `brave_configured=False` og kontrollert `brave_not_configured` er verifisert, mens DB, web, volum, media, PUBLIC og 0 public releases er uendret
- dokumentert at Brave er `LIVE VERIFIED`, men `CURRENTLY ACTIVE: NOT ACTIVE` for ordinære Editor-sluttbrukere inntil avtaleeier har dokumentert skriftlige sluttbrukerforpliktelser etter gjeldende Terms punkt 4(c) og nødvendige privacy notices/samtykker; ingen consent-/termsmotor inngår i fase 3D.2
- synkronisert ADR-, staging-, backup-, arkitektur-, roadmap- og prosjektstatus etter siste review og registrert grønn sluttreview-baseline i CI-run `31520955798` på head `964a97d89f5489aeaff26cb822b2753c76b40d6e`
- fulgt opp prosjekteiers visuelle stagingtest med presis X/Y-finjustering og 100–300 % Foto-zoom, mens Venstre/Midt/Høyre og Topp/Midt/Bunn beholdes som snarveier til samme cropoppskrift
- lagt additiv migrasjon `0028` med `ImageRenditionSet.zoom=1.0000` som historisk default, databaseconstraint 1–3, zoom i immutable renderhash og reverse-guard etter at non-default zoom finnes
- brukt samme kantklampede cover-geometri i alle tre live-previewene og serverprocessing, slik at 100 % tilsvarer dagens maksimale cover-utsnitt uten tom flate; Logo viser hele motivet med contain og avviser/skjuler fokus og zoom
- erstattet synlig domenespråk med `Ingen aktivt valgt bilde ennå.` og `Aktivt bilde`, og lagt korte forklaringer av Foto versus Logo
- lagt godkjent Brave privacy-copy ved queryen og rettighetscopy ved resultatene; `country=NO`, `search_lang=nb`, `safesearch=strict` og `spellcheck=false` er nå uttrykkelig eiergodkjent
- utvidet den interne, feature-gated kildereisen i Editor fra offisiell nettside/Open Graph til Brave Image Search, limt direkte bilde-URL og manuell JPEG-/PNG-/WebP-upload, uten at discovery, søk, preview eller processing kan velge bilde automatisk
- gjort Brave-forslaget deterministisk og synlig: lagret aktørnavn er basis, nøyaktig én kommune legges automatisk til, mens flere kommuner, kategori og aktivt tilknyttet person krever eksplisitt valg; tags brukes aldri og det brukes ingen AI
- bevart redaktørens eksakte manuelle query og vist både brukte og ikke brukte CRM-kilder før søk; lagt deterministisk lokal rangering med offisielt domene som sterkeste signal
- lagt server-side Brave-adapter mot official Image Search-endepunkt med `country=NO`, `search_lang=nb`, `safesearch=strict`, `spellcheck=false` og `count=30`, kontrollerte timeout-/rate limit-/providerfeil og uten eksponering av API-nøkkel
- dokumentert `search_lang=nb` som bevisst avvik fra ønsket `no`, fordi Braves offisielle enum ikke støtter `no`
- lagret aldri full providerrespons; bundet bare eksakt query, querykilder og normaliserte nødvendige kandidatfelt til omtrent 30 minutter gamle, tenant-/Organization-/brukerbundne signerte refs uten persistent kandidatmodell eller søkehistorikk
- skilt appens transient signed-ref fra providerens retention: Brave opplyser at standard query-logger kan beholdes i opptil 90 dager, mens Zero Data Retention krever Enterprise/egen avtale
- beholdt valgt Brave-events `source_type` og provider, men ikke providerens bilde-/side-URL eller query, i tråd med standardvilkårenes begrensning på persistent lagring/caching; rettighetsgodkjenning av selve bildet forblir et menneskelig ansvar
- gjenbrukt den sikre fetch-, preview-, processing- og approvalkjeden for Brave og limt URL; Brave-gridet kan bruke provider-thumbnail, mens valgt live-preview og serverprocessing bruker samme signerte original-URL
- lagt multipart-upload direkte gjennom samme kontrollerte ingest-/renditionprofil og økt staging-nginxgrensen fra 10 til 16 MiB for 15 MiB filgrense pluss multipart-overhead; grensen og faktisk multipartflyt er verifisert i staging
- lagt norske provider-/fetch-/processingfeil, fokusforvalg Venstre/Midt/Høyre og Topp/Midt/Bunn og umiddelbar, veiledende Foto-crop-preview; serverens faktiske `square`-, `landscape`- og `share`-previews er fortsatt fasit før approval
- gjort asset-alttekst valgfri med schema-only migrasjon `0027`; eksakt tom streng bevares uten skjult aktørnavn-fallback, whitespace-only avvises, og eksplisitt systemfallback-selection krever fortsatt tekst
- dokumentert og testet migrasjonens rollbackgrense: reverse fungerer før blanke verdier finnes, men blokkeres av de gamle constraintene etter første blanke asset-/event-alt; da er operativ rollback feature-off og fremoverrettet retting, med krav om verifisert pre-deploy-backup før aktivering og aldri skjult datautfylling
- verifisert 124 målrettede provider-, kandidat-, API-, modell-, selection- og migrasjonstester, deretter hele lokale leveransen med 365 backendtester, 22 frontendtester, 10 Playwright-tester, backup-/stagingkontrakter, produksjonsbygg og begge containerbygg; `makemigrations --check --dry-run` viser ingen modellavvik
- beholdt featureflaggets kode-default avslått og PUBLIC, public release/materialisering, public projection, serving, legacybilder og persistent kandidathistorikk uendret
- fullverifisert precision/zoom-oppfølgingen lokalt med 372 backendtester på ren migrert database, 28 frontendtester, 11 Playwright-reiser, 4 stagingkontrakttester, 68 backuptester, frontendbuild og begge produksjonscontainerbyggene
- verifisert precision/zoom-oppfølgingen i alle fem CI-jobber i run `31471806873`, tatt grønn Borg-backup `kreative-norge-staging-20260811T081243Z` og deployet runtimecommit `3686f08` kontrollert uten database-/volumrecreate
- anvendt migrasjon `0028` i staging og gjennomført faktisk API-processing med X/Y `0.3700/0.6800`, zoom `1.5000` og tre private no-store-previews; dette la bare til ett immutable rendition-sett og tre interne renditions, med 0 selection-/event-/publiserings-/releaseendring
- verifisert 0 storagechecksumavvik, 0 orphans, 0 slettinger, 0 public releases, uendret 122 publiserte aktører og grønne origin-smokes; prosjekteier har senere fullført vanlig browser-smoke og visuelt godkjent precision/zoom-, Foto/Logo-, blank-alt- og live/server-previewreisen
- verifisert alle fem GitHub CI-jobber grønne i run `31441538397`, deployet commit `971a9c0` etter fersk grønn Borg-backup og dokumentert URL-/upload-/blank-alt-/PUBLIC-/storageevidens i [stagingrapporten](STAGING_IMAGE_SOURCES_2026-08-11.md)
- aktivert eksisterende server-side Brave-credential i staging og verifisert boolsk konfigurasjonsstatus, 30 ekte kandidater for den foreslåtte queryen `Festspillene Helgeland VEFSN`, privat originalpreview, secure fetch, processing og tre private no-store-renditionpreviews med aktiv `search_lang=nb`
- bekreftet at den endelige Brave-kontrollen bare la til ett privat asset, ett immutable rendition-sett og tre interne renditions: selection-, review-event-, publiserings- og public-releaseantall var uendret, fortsatt med 0 public releases og 0 orphans
- registrert prosjekteiers aksept av Foto-zoom som innzooming og retur til standard cover-nivå uten zoom ut til tom flate, og Logo uten crop-/zoomkontroller som riktig kontrakt

## 2026-08-10

### Fase 3D.1: host-persistent staging-runtime aktivert

- serialisert immutable ingest-vinduet mot destruktiv cleanup med en felles PostgreSQL transaction-level advisory read/write-lock som holdes fra før storage-write/reuse gjennom databasecommit
- erstattet path-basert orphan-sletting med descriptor-relativ, komponentvis `O_NOFOLLOW`-traversering og relativ unlink fra verifisert parent directory fd
- lagt deterministiske PostgreSQL concurrency- og directory-swap-regresjonstester, negativ HTML-sniffing og strukturell Compose-verifikasjon av at bare API har imagemounts
- utvidet obligatorisk CI til full Django discovery, stagingkontrakttester, `bash -n` og ShellCheck av staging-scriptet
- la til eksplisitte private/public bildepaths under `/srv/kreative-norge/media/`, API-only bind mounts og sikker root-eid katalogforberedelse uten public serving
- beholdt `IMAGE_ASSET_FEATURE_ENABLED=False` som kode- og eksempelstandard, og aktiverte bare den ignorerte stagingkonfigurasjonen etter grønn persistence-, backup- og restore-gate
- la til deterministisk write/verify/cleanup-probe og verifiserte samme checksums på hosten og gjennom begge storagealiasene etter API-recreate
- la til dry-run-first orphan-cleanup med lokal-root-, symlink-, missing-reference-, alder-, PostgreSQL-lock- og recheck-gater
- rettet case-insensitiv bytes-sniffing av HTML i official discovery etter at den faktiske stagingreisen avdekket `bytes.casefold`-feilen
- verifiserte 336 backendtester gjennom full discovery, 64 berørte image-/candidate-/runtime-tester, 3 stagingkontrakttester, ShellCheck 0.10.0, 15 frontendtester, frontendbuild og begge produksjonscontainerbuildene
- verifiserte samme kontrakt i GitHub CI med 336 backendtester, eksplisitt logging av de nye testmodulene, 3 stagingkontrakttester, ShellCheck 0.9.0 og alle fem jobber grønne
- deployet runtimecommit `17919df` kontrollert til staging og verifiserte feature `True`, API-only imagemounts, 16 av 16 DB-refererte filer med korrekte checksums, 0 public releases, grønn orphan dry-run uten sletting og tre HTTPS-smokes på `200`
- gjennomførte faktisk official discovery, kandidat-preview, processing og first lock i staging; opprettet ett privat asset, tre interne renditions, aktiv selection og ett review-event uten public release
- verifiserte to separate Borg-arkiver og isolerte restore-smokes: én med deterministisk probe og én med faktisk fase 3D.1-original; eksakte uttrekk matchet forventede checksums
- bekreftet at aktiv selection, previews og storagechecksums overlevde en ny kontrollert API-recreate
- beholdt PUBLIC, public release, canonical `releases/...`, public projection og offentlig media-serving uendret
- registrert prosjekteiers gjennomførte visuelle staginggate: Parkenfestivalen fungerte med official discovery og Logo/contain; Bodø Bluesklubb fungerte med official discovery og Foto, og no-upscale ved for liten kilde ble godkjent som forventet kvalitetsbeskyttelse
- besluttet fase 3D.2 med norske processingfeil, fokusforvalg, live Foto-crop, valgfri alt-tekst og prioriterte kilder fra offisiell/OG via Brave og limt URL til manuell upload; dette er ikke implementert i denne leveransen
- dokumenterte Docker Compose 1.29.2s `ContainerConfig`-feil som åpen driftsrisiko etter kontrollert eksakt container-recreate

## 2026-08-09

### Fase 3D.1: offisiell kandidatflyt fra Editor til selection

- lagt én sikker, IP-bundet fetchadapter for official discovery, kandidat-preview og valgt processing med fail-closed DNS/SSRF-, redirect-, downgrade-, credential-, timeout-, MIME- og størrelseskontroll
- lagt website/Open Graph-discovery fra `Organization.website_url`, lagrede OG-kandidater, maksimalt én sidefetch, deduplisering og maksimum seks kandidater uten persistent kandidatmodell
- bundet transient kandidat og approval til tenant, Organization, bruker og proveniens gjennom kortlivede signerte refs; caller kan ikke levere fri URL, proveniens, asset eller rendition-sett ved approval
- lagt ephemeral private/no-store kandidat-preview og checksumverifisert intern preview av square/landscape/share uten privat original, intern path eller public serving
- koblet bare valgt kandidat gjennom fase 3C.7 med Foto → cover, Logo → contain og valgfritt normalisert fotofokus; processing oppretter ingen selection, event eller release
- lagt eksplisitt approval til eksisterende `lock_organization_image_selection`, inkludert first lock, expected-revision og replacement med eksisterende event-/provenienskontrakt
- lagt feature-gated `Aktørbilde` i Organization-editoren med kandidatgalleri, teknisk status, tre previews, warnings, alt-tekst, kreditering og aktiv selection; legacy Public Preview forblir separat
- verifisert 26 målrettede kandidat-/fetch-/API-/storage-/selectiontester, hele backendpakken på 324 tester, 15 frontendtester, frontendbuild, deterministisk Playwright-flyt og backend-/web-produksjonsbuild i Linux-containere
- beholdt `IMAGE_ASSET_FEATURE_ENABLED=False`; ingen Brave, limt URL, brukerupload, public release/materialisering, projection, PUBLIC, serving, journal, purge, staging eller deploy inngår

## 2026-08-08

### Fase 3C.7: intern upload-only ingest og deterministisk prosessering

- pin-net Pillow 12.3.0 bak en intern adapter og implementert kontrollert, begrenset lesing og faktisk dekoding av statisk JPEG, PNG og WebP
- håndhevet 15 MiB, 36 MP, single-frame, EXIF orientation før rendering, eksplisitt sRGB-normalisering, kontrollert feil ved korrupt ICC og profilfrie renditions uten automatisk oppskalering
- implementert processing profile v1 med `cover`, standardsentrum eller normalisert fokus, `contain` uten fokusavhengighet, og nøyaktig `square`, `landscape` og `share`
- beregnet source- og artifact-checksums fra ferdige bytes før storage-write og lagt tenant-scopede, deterministiske interne keys som er separate fra canonical public release keys
- lagt provider-nøytral immutable storagehelper som krever eksakt requested key, gjenbruker identiske bytes, avviser konflikt og collision-renaming og verifiserer skrevne bytes før databasecommit
- lagt feature-gated `ingest_uploaded_image`, som skriver og verifiserer privat original og tre artifacts før ett atomisk `ImageAsset`/`ImageRenditionSet`/`ImageRendition`-aggregate opprettes eller gjenbrukes
- beholdt storage-orphans ved databasefeil som immutable, ikke-servert retrygrunnlag; implicit reparasjon av delvise eller inkonsistente aggregater avvises
- verifisert 26 målrettede PostgreSQL-/storage-/processingtester og hele backendpakken på 298 tester, inkludert eksisterende bilde-, selection- og releaseregresjoner
- beholdt `IMAGE_ASSET_FEATURE_ENABLED=False`; ingen API-, Editor-, PUBLIC-, release-, serving-, journal-, purge-, staging- eller deployendring inngår

## 2026-08-07

### Fase 3B.3-A: additiv public release-domenegrunnmur

- lagt additivt til `OrganizationImageRelease` og `OrganizationImageReleaseRendition` med migrasjon `0026`, direkte organization-typed relasjoner og uten `GenericForeignKey`
- implementert intern UUIDv4-generering og canonical builder for `releases/<release_uuid>/<variant>.<ext>`; caller kan ikke levere release-ID eller public storage key
- gjort den feature-gated aggregate-tjenesten til eneste støttede insertvei; ny instance-save og default-/base-/reverse-managerens create, get-or-create, bulk-create og upsert avvises, mens en privat fullvaliderende insertprimitiv bare brukes inne i tjenestens transaksjon
- vurdert parent-locking av rendition-settet, men ikke innført en ny mekanisme uten konkret reproducerbar release-integritetsfeil; selection og de tre frosne rendition-radene låses fortsatt
- fryst release-mappingen til tenant, Organization, selection og rendition-sett gjennom immutable beskyttede relasjoner, og fryst variant, outputformat, artifact key og artifact-checksum per release-rendition
- håndhevet global unikhet for release-ID og public key, unik variant og rendition per release, nøyaktig builder-binding og komplett square/landscape/share i den atomiske domenetjenesten
- blokkert støttede ORM-veier for update, ForeignKey-reassosiering, bulk update, upsert/update-conflict og delete; `PROTECT` beskytter referert historikk mot sletting, mens manager-/modellreglene hindrer reassosiering gjennom ordinære skriveruter
- verifisert at R1 → R2 får nye UUID-er og keys, men kan gjenbruke identiske artifact-bytes uten ny encoding eller fil-I/O
- verifisert additiv forward/backward-migrasjon, tom initial release-tabell, constraints og invariantene med 26 målrettede PostgreSQL-tester og hele backendpakken på 272 tester
- beholdt `IMAGE_ASSET_FEATURE_ENABLED=False`; ingen storage-I/O, journal, serving, purge, API/projection, Editor, PUBLIC, staging eller deploy inngår, og permanent reservation-/deny-journal i separat failure-domain er fortsatt en senere gate

### Fase 3B.3: public release identity og canonical key-kontrakt godkjent

- fastsatt tilfeldig UUIDv4 som separat immutable public release identity, forskjellig fra processing artifact identity og `OrganizationImageSelection.revision`
- fastsatt canonical relativ storage key `releases/<release_uuid>/<variant>.<ext>` med lowercase UUIDv4, variantene square/landscape/share og extensionmappingen JPEG → `jpg`, PNG → `png` og WebP → `webp`
- utelatt tenant-/Organization-identitet, selection-revisjon, rendition-sett-ID, artifact key/checksum/hash, request host, filesystempath, credentials, tokens, queryparametere og mutable displayverdier fra public key
- godkjent organization-typed release aggregate uten `GenericForeignKey`, immutable historisk mapping, databaseunikhet, slettingsbeskyttelse og nøyaktig én public key per nødvendig variant; eksakte modell-/feltnavn og håndhevingsmekanisme avgjøres i fase 3B.3-A
- fastsatt at public key genereres internt og må være eksakt canonical builder-resultat fra release-ID, variant og outputformat; caller-key, feil UUID/variant/extension og delvis aggregate avvises
- godkjent no-clobber: samme key og forventede bytes kan være idempotent retry, andre bytes er hard konflikt, og tidligere release-ID-er/keys frigjøres eller gjenbrukes aldri
- bekreftet at replacement, restore og senere autorisert republisering alltid får ny release-ID og nye keys, også når eksisterende rendition-bytes gjenbrukes uten ny encoding
- beholdt permanent journalteknologi, takedown-/publish-saga, serving, nginx/Caddy, cache/purge, unpublish, retention, fallback-key, API/projection, workergrense, observability og full disaster-RTO som separate senere gater
- beholdt `IMAGE_ASSET_FEATURE_ENABLED=False`; ingen modell, migrasjon, filskriving, runtime, API, Editor, PUBLIC, import, staging eller deploy inngår i beslutningsleveransen

### Fase 3B.1R: representativ kvalitetsvalidering gjennomført og godkjent

- gjennomført den isolerte lokale harnessen og manuell review på 24 rettighetsavklarte fixtures uten nettverk; private kilder, privat manifest og visuell/full evidens forblir Git-ignorert
- godkjent 36 MP som konfigurerbar standard for maksimal decoded pixelmengde etter at 20 MP avviste to nyttige kilder, mens 36 MP var den laveste testede kandidaten som beholdt alle 24; 15 MiB forblir konfigurerbar maksimal kildefilstørrelse
- godkjent ingen universell minimumsbredde eller -høyde, ingen automatisk oppskalering, `contain` uten crop for logo og separat `cover`-/crop-/scaling-margin-vurdering av `square`, `landscape` og `share`
- gjort manglende obligatorisk no-upscale-rendition til teknisk `NOT READY FOR APPROVAL` uten å slette eller nødvendigvis avvise kildekandidaten
- beholdt edge variance og blockiness som advisory; outliers kan gi warning/manual review sammen med konkrete visuelle problemer, men ingen numerisk edge-, blur-, blockiness- eller whitespacegrense er automatisk hard fail
- godkjent profilfri offentlig output etter eksplisitt sRGB-normalisering eller -konvertering før crop/resize; untagged registreres som antatt sRGB, mens korrupt/uleselig ICC er kontrollert teknisk feil
- beholdt processing profile v1, Pillow-adapterretning, JPEG/PNG/WebP-input, no-upscale, CRM-runtime, featureflag, storage-I/O, API, Editor, PUBLIC, frontend, staging og deploy uendret
- markert fase 3B.1R som **GJENNOMFØRT / GODKJENT**, men beholdt hele fase 3B som aktiv med senere serving-, purge-, journal-, API-, retention-, sync/async- og observabilitygater

## 2026-08-06

### Fase 3B.1R-A: isolert representativ kvalitets-harness

- bekreftet at PR #23 er merget og at ordinær selection-livssyklus er komplett bak fortsatt avslått `IMAGE_ASSET_FEATURE_ENABLED`
- lagt en Git-ignorert lokal datasettkontrakt med anonym fixture-ID, rettighetsgrunnlag, redistribusjonsgate, fit, varianter, fargeprofilforventning og manuelle reviewtemaer uten representative kildefiler
- lagt en eksplisitt offline-runner med streng path-/manifestvalidering, én child-prosess per fixture, uendret source-checksum og output bare til valgt output-root
- målt kildeformat, dimensjoner, metadata-nøkler uten verdier, crop/no-upscale, edge variance, enkel blockiness, logowhitespace, kandidat-pixelgrenser, tid og peak RSS som advisory evidens
- skilt mellom sRGB, ikke-sRGB, untagged og korrupt ICC og generert inspecterbare kandidater for konvertert profilfri sRGB og konvertert sRGB med standardprofil uten å beslutte endelig outputkontrakt
- lagt lokal statisk HTML-/CSV-/JSON-review, kontaktark og redacted maskinevidens som aldri inneholder bildebytes når redistribusjon ikke er tillatt
- beholdt root requirements, produksjons-Dockerfile, CRM-runtime, modeller, migrasjoner, API, Editor, PUBLIC, storage, staging og deploy uendret
- beholdt fase 3B.1R som ufullført fordi et faktisk lokalt rettighetsavklart datasett og separat evidensgodkjenning gjenstår; ingen endelig kvalitetsgrense er besluttet

## 2026-08-05

### Fase 3C.6: ordinær restore av arkivert asset-selection som ny revisjon

- bekreftet at PR #22 og fase 3C.5 er merget, og lagt additiv migrasjon `0025` med `selection_restored`, nullable restore-source-referanse og immutable source-ID-/revisjonssnapshots
- lagt `restore_archived_organization_image_selection` bak avslått feature, med eksplisitt tenant, capability, organisasjonslås, `expected_revision` og en eksplisitt eldre arkivert asset-selection som kilde
- beholdt både restore-kilden og dagens aktive selection som historikk; bare dagens aktive status arkiveres, mens restore alltid oppretter en helt ny aktiv revisjon
- kopiert rendition-sett, alt-tekst og offentlig kreditering uendret fra restore-kilden og revalidert nøyaktig square-, landscape- og share-rendition
- registrert tidligere aktiv selection og restore-kilden i append-only event uten ny approvaltekst, kilde-URL, provider eller tekniske warnings; endret godkjenningsgrunnlag eller presentasjonsinnhold krever vanlig replacement
- verifisert rollback ved eventfeil, `SET_NULL` med bevarte snapshots, tenant-/rolleavvisning, null writes ved røde gater og reell PostgreSQL-concurrency med nøyaktig én vellykket restore
- beholdt `IMAGE_ASSET_FEATURE_ENABLED=False`, legacybildeflyten og backupgrunnmuren **ACTIVE**; ingen API-, Editor-, PUBLIC-, storage-, fil-, bildebehandlings-, runtime- eller stagingendring inngår
- satt fase 3B.1R som neste kvalitetsgate før faktisk processing eller storage-runtime; ingen ny selection-kommando planlegges etter denne leveransen

## 2026-08-03

### Fase 3C: atomisk selection-kommando og append-only locking-/replacement-event

- bekreftet at PR #20s `OrganizationImageSelection`-skjema er merget, og lagt additiv migrasjon `0023` som bare oppretter `ImageReviewEvent` med nullable live-referanser og varige snapshots
- gjort eventet append-only gjennom støttede applikasjons-/ORM-veier uten å omtale løsningen som database-WORM
- lagt én feature-gated og tenant-scopet `lock_organization_image_selection` som eneste godkjente skriverute for atomisk første låsing og replacement med event
- brukt target-`Organization` som concurrency-lås og `expected_revision` som eksplisitt konfliktgate; eventfeil ruller tilbake arkivering og ny selection
- håndhevet egen-tenant-scope for redigerer, gruppeadmin og tenant-superadmin, mens plattform-superadmin må angi target tenant
- lagret begrenset provenance, validerte warnings og intern `image-approval-v1`-tekst som event-snapshot for asset-selection; fallback lagrer ingen falsk rettighetsgodkjenning
- begrenset eventets base manager til lesing, inserts og nødvendig `SET_NULL`; ordinære mutasjons-/upsertveier blokkeres uten å bryte actor-sletting eller tenant-cascade
- gjort begge URL-snapshotfeltene fail-closed for andre schemes, URL-credentials, fragmenter og kjente credentials-, signatur-, token-, AWS-, Google- og Azure SAS-parametere uten nettverk eller omskriving
- beholdt `IMAGE_ASSET_FEATURE_ENABLED=False`, legacybildeflyten og backupgrunnmuren **ACTIVE**; ingen API-, Editor-, PUBLIC-, storage-, fil-, bildebehandlings-, runtime- eller stagingendring inngår

### Fase 3C: additiv Organization-selection uten runtimebruk

- lagt til `OrganizationImageSelection`, der hver rad representerer én låst aktiv eller arkivert revisjon for én organisasjon
- håndhevet unik revisjon, positiv revisjon, maksimalt én aktiv selection, ikke-tom alt-tekst og eksklusivt valg mellom immutable rendition-sett og systemfallback i databasen
- gjort låsebruker, låsetidspunkt og alt-tekst obligatoriske; bruker og rendition-sett beskyttes med `PROTECT`, mens organisasjon bruker `CASCADE`
- beholdt asset, fit, fokus og prosesseringsversjon normalisert gjennom det eksakte rendition-settet uten dupliserte selection-felt
- dokumentert at `clean()` avviser tenant-mismatch, men at senere domenetjeneste fortsatt må håndheve tenant, capability, atomisk revisjon/concurrency, arkivering, ny aktiv rad og append-only event
- beholdt featureflagget avslått, legacybildeflyten uendret og backupgrunnmuren **ACTIVE**; ingen domenekommando, eventmodell, filer, storage-I/O, API, frontend eller deploy inngår

### Fase 3C: additiv bildedomenemodell uten runtimebruk

- lagt til tenant-eide `ImageAsset`, `ImageRenditionSet` og `ImageRendition` med vanlige heltallsnøkler og én reverserbar schema-migrasjon
- lagt provider-nøytral validering på private/artifact storage keys og lowercase SHA-256, format-/MIME-kontroll og positive dimensjons-/filstørrelsesconstraints
- håndhevet tenant-avgrenset unikhet, fokuspunkt i intervallet 0–1 og `PROTECT` fra rendition-sett til asset og rendition til sett
- dokumentert at `clean()` avviser cross-tenant-relasjoner, mens en senere domenetjeneste må håndheve samme invariant før runtimebruk
- beholdt `IMAGE_ASSET_FEATURE_ENABLED=False`; ingen filer, mapper, storagekall, `Organization`-kobling, selection, review/audit, API, frontend, legacyendring eller deploy inngår
- beholdt backupgrunnmuren **ACTIVE** og krever separat godkjenning før neste fase 3C-leveranse

### Fase 3C: avslått image-storage-konfigurasjonsgrunnmur

- lagt `IMAGE_ASSET_FEATURE_ENABLED` inn fail-closed og avslått som standard uten kobling til runtimeflyt
- bevart eksisterende `default`- og `staticfiles`-backends og lagt separate lokale `FileSystemStorage`-aliaser for private originaler og offentlige renditions
- validert tomme, relative, root-, overlappende, staticfiles- og repo-overlappende paths uten å opprette mapper eller filer ved settings-load eller system check
- beholdt modeller, migrasjoner, API, frontend, legacybildeflyt, ImportJob-/ExportJob-storage, Compose, stagingmiljø og deploy uendret
- beholdt backupgrunnmuren **ACTIVE**; aliasene brukes ikke til filskriving eller serving, og neste fase 3C-leveranse krever separat godkjenning

## 2026-08-02

### ADR-008 backupgrunnmur aktivert

- etablert separat BX11 Storage Box med 1 TB i FSN1, dedikert skrivbar subaccount, verifisert host key og dedikert nøkkelinnlogging uten å lagre identifikatorer eller nøkkeldata i repoet
- initialisert kryptert `repokey-blake2`-repository med Borg 1.2.8 og bekreftet separat off-server custody av passfrase, kryptert repositorynøkkel og nødvendig recovery-metadata for minst to ansvarlige
- kjørt første manuelle systemd-backup med grønn PostgreSQL custom-format dump, `pg_restore --list`, manifest, checksums, repository-ID, arkivstatus og skrivebeskyttet repository-inspeksjon
- kjørt full repository- og dataverifikasjon og isolert PostgreSQL 16 restore-smoke av samme arkiv med `--network none`, ingen publisert port, ufarlige tellinger og full cleanup
- målt første backup til 8 sekunder og restore-smoke til 8,7 sekunder; registrert foreløpig RPO som inntil omtrent 24 timer pluss timerforsinkelse, uten å love full katastrofe-RTO
- bekreftet første Storage Box-snapshot og nyere synlig Hetzner Cloud Backup
- aktivert nattlig backup- og ukentlig verify-timer etter grønn teknisk, recovery- og Console-gate; begge er enabled/active uten failed units
- beholdt CRM-runtime, database, data, publiseringsflagg, DNS og Cloudflare uendret; ingen applikasjonsdeploy eller containerrestart/recreate ble utført
- satt backupgrunnmuren til **ACTIVE**; host-persistent media-runtime og ekstern feilvarsling gjenstår som separate leveranser

### Sikkerhetsherding av forberedt backupgrunnmur

- strammet den felles lokale Borg-porten til stabil versjon `>=1.2.8` og `<1.3.0`; eldre `1.2.x`, `1.3.x`, `2.x`, prerelease og malformed output avvises før repository- eller backuparbeid for init, key export, inspect, backup, verify og restore
- lagt en semantisk pathgate før mutasjoner: root, brede systemområder, parent traversal, ikke-normaliserte paths, symlinkkomponenter og farlige mediaoverlapp avvises
- bundet work, status, restore-gate og Borg cache/config/security til dedikert backup-state og hindret ambient Borg-directoryvariabler i å flytte skrivbare områder
- avgrenset host-media til eksplisitte underkataloger under Kreative Norges media-root og API-media til eksplisitte underkataloger under `/app`
- herdet recovery-key-export med operator-eid, ikke group/world-writable parent, directory-/symlinkavvisning og atomisk no-clobber med bevart mode `0600`
- rettet den felles pathliste-parseren slik at også eneste og siste element i en kolonseparert allowlist alltid valideres
- utvidet den syntetiske backup-testpakken til 68 tester for versjonsgrenser, felles kommandogate, pathfamilier og siste listeelement, overlapper, symlinks, validering før arbeid og atomisk recovery-destinasjon
- beholdt backupgrunnmuren **PREPARED, NOT ACTIVE** og passphrase-/key-/Storage Box-custody **MANUAL REQUIRED**; ingen server, staging, runtime, database, tjeneste, container, deploy eller timer er endret

## 2026-08-01

### ADR-008 og Hetzner backupgrunnmur forberedt

- godkjent én-server-MVP med Django, PostgreSQL og aktiv media på dagens Hetzner Cloud-server, navngitte lokale Django-storagealiaser for fremtidig media og utsatt S3-/AWS-/Backblaze-/CDN-løp
- lagt en inaktiv backupmodul under `ops/backup/` med PostgreSQL custom-format dump, `pg_restore --list`, eksplisitte fil-/konfigurasjonspaths, sikkert manifest, kryptert Borg 1.2.x/`borg-1.2`, repo-ID-lås og retention 14/8/12
- lagt nattlig backup- og ukentlig verify-unit med `flock`, root-only state, lav prioritet og statusfil, men ikke installert eller aktivert timerne
- lagt isolert restore-smoke mot PostgreSQL 16 uten port eller live databaseinngrep og en hard aktiveringsport som krever grønn backup, dump, repository-check og restore av samme arkiv
- rettet lock-/status-racet slik at verify og restore bare kan skrive operativ status etter at den felles låsen er ervervet; lock contention oppretter eller endrer ingen status-/restore-ressurser
- lagt eksplisitt `export-recovery-key` for Borgs krypterte repositorynøkkel med felles Borg-/SSH-/repository-ID-preflight, sikker absolutt destinasjon, no-clobber, root/`0600`, tomfilkontroll og ingen nøkkelmateriale i output
- lagt skrivebeskyttet `inspect-repository` som verifiserer repository-ID og viser bare arkivantall og nyeste sikre arkivnavn uten arkivmedlemmer eller muterende Borg-kommandoer
- dokumentert eksisterende risiko for at import-/eksport-/rapportfiler kan ligge i API-containerlaget fordi dagens Compose mangler media-mount; ingen filer eller runtime ble flyttet
- fullført en anonymisert, skrivebeskyttet stagingbaseline som verifiserte serverdisk, Compose, PostgreSQL, Docker-volumes, FileField-/mediapaths, eksisterende manuelle dumps, fravær av kolliderende automatisert backup og manglende Borg-/Storage Box-oppsett
- bekreftet at `/app/imports` og `/app/exports` ikke finnes og at filantallet er null, men at nye FileField-filer fortsatt kan gå tapt i API-containerlaget før en separat host-persistent runtimeleveranse
- korrigert backupmalens staging-environmentpath til `.env.staging` både for Compose og serverkonfigurasjons-allowlisten
- registrert prosjekteiers Console-verifikasjon: Cloud Backups er ENABLED AND FIRST BACKUP VERIFIED med første synlige backup på 11,6 GB og 0 Cloud Volumes; dette er fortsatt bare et ekstra helserverlag
- anbefalt, men ikke bestilt, BX11 med 1 TB i FSN1, kapasitetsreview ved 60–70 prosent bruk og minst 20–30 prosent ledig margin
- synkronisert ADR-007 mot ADR-008: første MVP bruker lokal host-persistent private/public-storage og kontrollert lokal serving; S3/CDN/IAM/KMS/Object Lock og provider-spesifikke purge-/`versionId`-porter er bare betingede senere krav
- beholdt leveransen PREPARED, NOT ACTIVE fordi Storage Box, Borg, recovery-secret, eksportert repositorynøkkel, off-server custody, første Borg-backup, restore-smoke, Storage Box-snapshots og timere fortsatt ikke er opprettet eller aktivert
- ikke endret CRM-runtime, Compose, database, data, publisering, modeller, API, Editor, PUBLIC, Import 2.0, containere, DNS eller Cloudflare

### Fase 3B.2: storage-, delivery-, takedown- og restoreprinsipper godkjent

- godkjent to-key-kontrakt med separat deterministisk processing artifact identity og immutable public release identity; ny offentlig revisjon bruker ny release key uten krav om ny encoding, mens eksakt key-struktur på dette tidspunktet fortsatt var åpen og senere ble fastsatt i ADR-007 punkt 25
- godkjent dedikert unversioned aktiv public rendition-store eller likeverdig namespace uten offentlig tilgjengelige historiske versjoner; suspended versioning behandles ikke automatisk som aldri-versioned
- presisert at public delivery ikke krever anonym bucket: første MVP bruker kontrollert same-origin/lokal media-origin fra host-persistent storage; ekstern provider-endpoint, origin-begrenset objektlager og CDN er bare betingede senere krav
- godkjent private originaler med separat lokal host-persistent storage, permissions og rollebeskyttet tilgang; provider-versioning, IAM/public-access-block og eksplisitt `versionId`-bevis gjelder bare dersom objektlagring senere innføres
- godkjent hybridbackup med private originaler, metadata/profil, nødvendige referanser og audit, aktive public rendition-bytes og deny-journal i separat failure-domain; deterministisk regenerering er sekundær reparasjonsvei
- godkjent fail-closed restore-gate med ikke-offentlig karantene, nyeste deny-journal, replay/read-model, reconciliation og checksum-/referanseverifisering før public serving
- godkjent append-only/WORM-orientert autoritativ deny-journal med idempotente events, separat backup/failure-domain og deny-first-rekkefølge før origin-delete og purge; permanent teknologi er fortsatt åpen
- godkjent framtidige scopes for public release deny, tenant-checksum deny og særskilt global checksum deny; bare release deny er bevist, og checksum-deny er ikke implementert
- godkjent idempotent purgekontrakt med retryklassifisering, request-/hendelses-ID og verifikasjon; Moto og recording-adapterne forblir kun prototypeevidens, ikke produksjonsleverandør eller IAM-/CDN-bevis
- gjort skrivebeskyttet provider-/driftsgate til neste anbefalte planleggingsleveranse og beholdt fase 3B.1R og senere API-, concurrency-, retention- og sync/async-gater som påkrevd før fase 3C
- ikke implementert storage, CDN, journal, read-model, checksum-deny, modeller, migrasjoner, API, Editor eller PUBLIC; runtime, data, staging og deploy er urørt og legacy URL-/faviconflyt gjelder fortsatt

## 2026-07-31

### Fase 3B.2: isolert storage-, takedown- og restoreprototype på PR-branch

- lagt en isolert Django 5.1-lab under `spikes/storage_pipeline/` med eksplisitt bevart `default`/`staticfiles` og separate private/public image-aliaser uten å endre runtime-settings eller root-avhengigheter
- pin-net Moto Server 5.2.2, django-storages og boto3 i laben og testet create/put/get/head/delete, policy, versioning, version listing, delete marker og copy mot disponibel lokal emulator
- gjenbrukt fase 3B.1s processing artifact key og bevist separat tenant-/actor-/release-skopet R1/R2-key uten re-encoding eller overskriving av gamle public keys
- gjennomført T0–T5 med nyere deny-journal utenfor gammelt app-snapshot, origin delete, stale-cache-simulering, idempotent purge, kontrollert reintroduksjon, reconciliation, fallback og autorisert R2 mens R1 forblir denied
- sammenlignet direkte backup av aktive renditions med regenerering fra privat original + canonical metadata og anbefalt hybridmodell til prosjekteiers vurdering
- dokumentert Moto-gap der unsigned `VersionId` kunne nå eldre privat versjon; recording private-access boundary håndhever ønsket domenekontrakt, men faktisk leverandør/IAM må verifiseres senere
- anbefalt til vurdering to-key-kontrakt, unversioned aktiv public storage, hybridbackup og separat varig deny-journal; ved prototypeleveransen var anbefalingene ennå ikke godkjent, og ingen produksjonsleverandør var valgt
- lagt til separat path-filtrert spike-CI og tekstlig evidens uten secrets, eksterne data, staging eller produksjonskontakt
- ikke implementert bildearkitekturen i CRM-runtime og ikke endret modeller, migrasjoner, API, Editor, PUBLIC, root requirements, produksjonscontainere, ordinære Compose-filer, staging eller deploy; legacy URL-/faviconflyt gjelder fortsatt, fase 3B.1R og senere fase 3B-gater gjenstår

### Fase 3B.1: isolert bildebehandlings- og renditionprototype

- sammenlignet Pillow og pyvips/libvips praktisk i en separat prototypepakke og dedikert labcontainer uten runtimekobling
- generert 20 syntetiske fixtures og verifisert sikker dekoding, MIME-/byteskontroll, pixelgrense, EXIF, metadatafjerning, alpha, contain, cover, fokus og ingen automatisk oppskalering
- generert square-, landscape- og 1200 × 630-sharevarianter, deterministisk dynamisk fallback og tre statiske nødvarianter
- dokumentert byte-identisk Pillow-output over tre kjøringer og retningsgivende CPU-, minne-, tids- og filstørrelsesmålinger
- prosjekteier har godkjent Pillow bak intern adapter, statisk JPEG/PNG/WebP-input, processing profile v1, no-upscale, immutable key-invarianten og 15 MiB som konfigurerbar standardverdi
- beholdt 20 megapiksler, universelle korteste-side-bånd og edge-variance-/blurintervaller som ikke-godkjente prototypeverdier; fase 3B.1R med representative ekte bilder og sRGB/fargeprofiler er påkrevd før fase 3C
- godkjent neste fase 3B.2 som en isolert storage-, immutable-key-, purge-, deny- og restorelab uten CRM-runtime, modeller, migrasjoner, API, Editor, PUBLIC eller stagingdeploy
- flyttet den isolerte spikejobben fra ordinær CI til en separat, path-filtrert workflow med manuell trigger
- ikke endret Django-runtime, modeller, migrasjoner, API, frontend, default storage, database, staging eller deploy

### Fase 3A og ADR-007

- godkjent fase 3A-kartleggingen av thumbnail-, bilde-, storage-, import- og kortflyten som beslutningsgrunnlag
- godkjent [ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) med flyten `ImageCandidate` → kontrollert fetch og validering → tenant-eid `ImageAsset` → `OrganizationImageSelection` → `ImageRendition` → felles public image projection
- besluttet append-only bildehistorikk, versjonert ett-klikk-godkjenning, eksplisitt locking/replacement, rolleavgrenset takedown og karantene, retensjonsregler og deterministisk systemfallback
- besluttet lokal filsystemstorage og S3-kompatibel staging-/produksjonsretning gjennom Djangos `STORAGES`, med private originaler, immutable offentlige renditions og samlet backup/restore
- besluttet additiv public API-overgang og den fremtidige Import 2.0-kontrakten `KEEP_LOCKED_IMAGE`, `SET_APPROVED_IMAGE` og `USE_APPROVED_FALLBACK`
- gjort fase 3B teknisk prototype til neste aktive leveranse; leverandør, bibliotek, terskler, formater, SVG, kø, API-schema og øvrige spikevalg er fortsatt åpne
- ikke endret applikasjonskode, modeller, migrasjoner, storage, data, staging eller deploy; dagens legacy bilde-URL- og faviconflyt er fortsatt implementert adferd

## 2026-07-30

### Fase 2: kontrollert stagingreparasjon av telefonkontakter

- forhåndskontrollert kandidat-ID `1`, `2`, `132` og `150` i tenant `musikkontoretnord` uten å skrive ut kontaktverdier; alle tilhørte riktig tenant, manglet `PHONE`-kontakt og hadde ingen duplikat- eller flertydighetskonflikt
- opprettet og verifisert en tidsstemplet PostgreSQL-backup før dataendringen
- kjørt den eksplisitt godkjente, tenant-avgrensede `PHONE --apply`-reparasjonen, opprettet nøyaktig fire private primære telefonkontakter og fått `changes_applied=4`
- bekreftet med ny dry-run at ingen kandidater eller konflikter gjenstod og at `changes_applied=0`
- bekreftet med felt- og fingeravtrykkssammenligning at eksisterende telefon- og e-postkontakter, direkte persontelefoner og publiseringsflagg var uendret
- verifisert de nye private primærkontaktene i Editor-API og fravær av telefon-eksponering i aktivt PUBLIC API og PUBLIC HTML
- beholdt fase 2 som aktiv frem til prosjekteiers visuelle sluttkontroll; ingen produksjonsdeploy, publiseringsendring eller endring utenfor valgt tenant ble utført

### Fase 2 lukket og fase 3 aktivert

- lukket fase 2 som gjennomført 2026-07-30 etter at prosjekteier visuelt bekreftet i staging at undersøkelseseksemplets telefon finnes under Kontaktkanaler, er markert som primær og fortsatt har offentlig telefon avslått
- gjort robust thumbnail-, bilde- og kortarkitektur til aktiv produktfase uten å starte implementeringen
- besluttet at den konservative PHONE-reparasjonskommandoen beholdes uendret som en avgrenset legacy-reparasjon og at telefonarkitekturen ikke blokkerer fase 3
- lagt en beslutningsgate før fase 4 kan godkjennes som ferdig: et eget ADR skal da spesifisere internasjonal telefonmodell, landkontekst og normalisering
- planlagt implementering av den nye telefonarkitekturen tidlig i fase 5 og gjort stabil telefonmodell til forutsetning for full telefonmatching i fase 6
- fastlagt prinsipper om bevart originalverdi, separat normalisert sammenligningsverdi, uttrykkelig land-/regionkontekst, internasjonale numre, separat internnummer, én sentral backendtjeneste, review av tvetydige verdier og ingen publisering som følge av normalisering eller matching
- beholdt bibliotek, modell- og feltnavn, constraints, API-kontrakt, migrering og backfill som uavklart; ingen ny telefonarkitektur eller nytt ADR ble implementert

## 2026-07-29

### Verifisert staging- og frontendbaseline

- fullført fase 1 med skrivebeskyttet kontroll av lokal/GitHub `main`, staging-repo, kjørende Docker-images og containere, nginx, Caddy, frontendbundles og HTTPS-/cachekjeden
- bekreftet at kjørende JavaScript- og CSS-bundles matchet en ren build fra dagens `main`, og at proxy eller Cloudflare-cache ikke var årsak til observerte frontendavvik
- kontrollert PUBLIC på desktop/mobil og en autentisert Editor-visning; Editor-forsiden er godkjent designreferanse
- fordelt gjenstående kort-, bilde-, tag-, overflow- og formavvik til fase 3 og fase 5
- bekreftet at ingen kode, data, publiseringsflagg eller deploy ble endret under fase 1

### Fase 2: telefon, publiseringsstandarder og offentlig tittel

- utvidet `repair_person_contacts` bakoverkompatibelt med eksplisitt telefonmodus, tenant-filter, trygg dry-run og privat oppretting; konflikter rapporteres og den berørte posten hoppes over uten automatisk endring
- beholdt eksisterende e-postmodus som standard og lot eksisterende kontakt- og publiseringsflagg være urørt
- gjort publisering av ny e-post, ny telefon, ny kontaktperson og ny eksisterende personkobling avslått som standard i Editor og nullstilt ved faktisk aktør- eller tenantbytte
- tydeliggjort forskjellen mellom offentlig personvisning og offentliggjøring av en konkret kontaktkanal
- lagt `Person.title` additivt til aktivt public API og PUBLIC HTML når feltet har verdi
- utvidet backend-, frontend- og Playwright-regresjonstester uten schema-migrasjon eller data-apply utenfor testdatabasen
- merget PR #12 som merge-commit `6768af8a3b48314aec028ec5972939c6ef0e38e8` og deployet samme applikasjonsversjon kontrollert til staging
- verifisert PostgreSQL, Django, migrasjoner, containere, HTTPS, public API/HTML, alle PUBLIC-kortlenker og at ny frontendbundle faktisk serveres
- verifisert skrivebeskyttet at Editor nullstiller de fire publiseringsvalgene, skjemaet, feiltilstand og koblingsstatuser ved aktørbytte uten å sende tenantmutasjoner
- verifisert `Person.title`, fravær av tom tittelrad og fravær av direkte `Person.phone`-fallback i PUBLIC
- kjørt tenant-avgrenset `PHONE`-dry-run for `musikkontoretnord`: `49` undersøkt, `4` kandidater (`1`, `2`, `132`, `150`), ingen konflikter og `changes_applied=0`
- beholdt fase 2 som aktiv; ingen produksjonsdeploy, data-apply, kontaktverdi- eller publiseringsendring ble utført

## 2026-07-28

### Arbeidsflyt og produkt-roadmap

- merged PR #10 og fullført den repo-baserte session-workflowen med `ADR-006`, `$start-arbeidsokt`, `$avslutt-arbeidsokt`, `$fortsett-prosjekt` og totalt 15 validerte skills
- ryddet autoritativ dokumentasjon ved å holde gamle rotbaserte handoff-, `REFERENCE`- og `STATUS`-filer utenfor repoet og ignorere genererte Playwright-resultater
- godkjent revidert produkt-roadmap med staging/frontend-baseline først, deretter liten kontaktstabilisering, robust bildearkitektur, Import 2.0-design, langsiktig kontaktarkitektur, Import 2.0-implementering og eksport
- integrert AI som et gjennomgående produktprinsipp for bildevalg og importstøtte, uten automatisk overskriving eller publisering uten eksplisitt regel eller menneskelig godkjenning
- skilt sikker automatisk staging-deploy ut som et parallelt infrastrukturløp; det er fortsatt planlagt og ikke implementert eller verifisert

## 2026-07-26

### PUBLIC og kontaktpublisering

- rettet PUBLIC HTML slik at aktørkort bruker kanonisk ID-basert detaljrute (`/public/actors/id/<actor_id>/`) og ikke lenger lager ødelagte lenker for publiserte aktører uten organisasjonsnummer
- beholdt legacy-rute for organisasjonsnummer som redirect når den identifiserer én publisert aktør entydig
- lagt til skrivebeskyttet `check_public_actor_links` for å kontrollere alle PUBLIC-kortlenker
- lagt til `publish_existing_email_contacts` som dry-run først, transaksjonell og idempotent staging-/datakommando for godkjent publisering av eksisterende e-postkontakter
- korrigert relasjonsspesifikt unntak fra `Kathrine Schem` til `Kathrine Schjem`
- kjørt staging-datakjøring etter backup: `164` av `164` eksisterende e-postkontakter er offentlige, og tre aktive aktør-person-koblinger er satt til `publish_person=False`
- bekreftet at telefonpublisering og `Organization.is_published` ikke ble endret

## 2026-07-24

### Utviklingsarbeidsflyt

- godkjent og implementert `ADR-006` for session-flyt og varig prosjektminne
- lagt til `$start-arbeidsokt` og `$avslutt-arbeidsokt`
- standardisert Git-baseline, project health, SESSION WRAP-UP og neste Codex-session-prompt
- utvidet ADR-006 med `$fortsett-prosjekt` som strategisk ChatGPT-rutine og tynn Codex-bro
- lagt til fast `CHATGPT SESSION SUMMARY` og dokumentert kontinuitet mellom nye ChatGPT-samtaler og Codex-sessioner
- validert alle 15 skills og bekreftet `$fortsett-prosjekt` i en separat skrivebeskyttet Codex-session

## 2026-07-23

### Dokumentasjon

- etablert ny dokumentasjonsstruktur på egen branch
- kartlagt at IMPORT er langt mer utviklet enn eldre prosjektfiler beskriver
- registrert at EKSPORT har datamodell og API-grunnlag, men ikke komplett motor
- registrert at public HTML foreløpig kun brukes i staging
- registrert ønsket om automatisk staging-deploy ved push
- godkjent `ADR-005` som målarkitektur for helhetlig personkontakt og relasjonsspesifikk publisering; implementering er ikke startet
