# Security and Roles

## Editor-brukerpanel – avgrenset kodeleveranse 2026-10-25

Session/Login leverer navn fra eksisterende navnefelt med username-fallback og
`can_access_admin = is_active and is_staff`, som dagens standard Django-admin.
Tenantens superadmin/gruppeadmin innebærer ingen adminadgang. Plattform-
superbruker og aktiv tenantrolle vises separat; kontorvalget viser bare dagens
autoriserte tenantliste, uten påstått hjemmekontor. Admin-lenken går til `/admin/`;
ingen ny administrasjonsflate eller tilgang er opprettet. Backend håndhever
fortsatt alle rettigheter. Lagret kontakt kan bare fjernes med eksisterende
sletterettigheter; nye lokale rader krever ingen DELETE. Ingen 6A-/6B-endring.
Kode på PR #92 er ikke deployet av denne rettingsrunden.

## Tenantprivate notater – inaktiv grunnmur stagingverifisert 2026-10-24

[Kode-PR #85](https://github.com/fredrik-stack/kreative-norge-crm/pull/85) er separat
reviewet og ordinært merget på `5c39ec51b3f5a7af20f05f2367d51afa0075e952`;
main-CI `40035930772` er SUCCESS, 6/6. Eksakt kode/image er deployet API-only,
og bare additiv0035 er anvendt. Begge overlaytabeller er tomme, FK/unikhet/PK og
identitetsvern er verifisert; `TENANT_NOTE_OVERLAYS_ENABLED` er effektivt/varig av.
Eksisterende CRM-innhold, miljø, media/static, safety og teknisk API/admin/PUBLIC
består; arkivbundne pre/post-backup-/restorekontroller er grønne og timere aktive.
Ett read-only inventar viser 273 NULL-, 6 tomme og 6 tekstnotater på 285 profiler,
med korrekt egen assignment og ingen observerte scopeavvik. 60 legacytags,
97 koblinger, 13 ubrukte; ingen klassifisering eller flytting.
[Sanitert stagingevidens](../status/STAGING_PHASE_6A_NOTE_OVERLAYS_2026-10-24.md)
og [mandat/rutematrise](../operations/TENANT_NOTE_OVERLAYS.md) beskriver grunnlag
og senere beslutningsbehov. Legacy note/tags er autoritative; ingen overlaylesing,
shared tilgang, private tags eller fullført trinn 7/6A. Evidenspublisering følger
GitHub; dokumentasjonsmerge utløser ingen deploy.


**Datert 6A.2-backfillstatus 2026-10-17:** Eiergodkjent eksakt plan er anvendt i staging: ett domain, sju tenantbindinger, 285 profilbindinger og 285 egne legacyassignments. Batch `phase6a2-staging-20261017-01` er COMMITTED_VERIFIED med matchende frisk read-back og separat no-op-plan uten restendringer. Bevaring og arkivbundet post-restore av faktisk backfill er verifisert. Samme API kjører og driftsvinduet er avsluttet med timere gjenopprettet; prosjekteier har bekreftet eksisterende Editor-/admin-/PUBLIC-lesing uten feil. STAGING VERIFIED / OWNER-CONFIRMED innen avtalt backfill-/bevarings-/lesescope, se [datert evidens](../status/STAGING_PHASE_6A2_BACKFILL_2026-10-17.md). Ingen shared-aktivering eller ferdigmelding av hele 6A. Midlertidig slettebegrensning består; senere catch-up/apply krever separat godkjenning. Skrivebeskyttet review av de åtte dokumentfilene er fullført uten kritiske eller viktige funn. Dokumentasjonen er publisert og PR-reviewet uten blokkerende funn i [PR #80](https://github.com/fredrik-stack/kreative-norge-crm/pull/80). Kontrollert dokumentasjonsmerge er bestilt 2026-10-17; faktisk merge/head og CI følger GitHub og SESSION WRAP-UP. Ingen ny drift eller applygodkjenning inngår. Eldre daterte avsnitt nedenfor beskriver historisk grunnlag.

**Status:** delvis implementert, detaljkartlegging gjenstår

Roller i `TenantMembership`:

- superadmin
- gruppeadmin
- redigerer
- leser

Foreløpig tilgang:

- lese: alle roller
- opprette og redigere: superadmin, gruppeadmin og redigerer
- slette: superadmin og gruppeadmin
- import/eksport: superadmin, gruppeadmin og redigerer

Systemet bruker Django session-auth og CSRF. Dagens kombinasjon av tenant-
medlemskap, globale Django-grupper og Django-superuser beskriver nåtilstanden;
den godkjente hardeningen for shared tilgang beskrives nedenfor.

## 6A.1-skjemaavgrensning 2026-10-13

6A.1 legger til nullable domain-bindinger og separate assignmenttabeller; shared tilgang er ikke aktivert. 6A.1 er STAGING VERIFIED / OWNER-CONFIRMED innen avtalt skjemagrunnmur/API-runtime, se datert stagingevidens. Nye felt er utelukket fra eksisterende adminskjemaer/serializers, og de nye modellene er ikke adminregistrert. Ingen nye støttede skriveinnganger eller featureflagg er innført. Legacytenant-filtrering og global rollefallback er uendret.

**Historisk kontrakt ved 6A.1:** Assignmentenes strukturelle `full_clean()` er ingen autorisasjons- eller databasegaranti for lik domain: save/update/bulk kan omgå den. Senere assignment-write/backfill må ha en støttet transaksjonell grense og beskytte endring av domain på targets. Assignment-FK-ene beskytter parentsletting, men erstatter ikke en autorisert livssyklus for eksplisitt assignmentfjerning. Se [datamodellens 6A.1-avgrensning](DATA_MODEL.md).

## 6A.2 – lokalt implementert migreringsgrense

**Gjeldende stagingstatus 2026-10-14:** Ny API og 0034/integritetsvern er
deployet/anvendt; ingen reell domenebinding, assignment eller batch er opprettet.
Dry-run var read-only med null writes. Eksisterende miljø/flagg, rettigheter og
safety/deny-state er bevart. STAGING VERIFIED / OWNER-CONFIRMED innen avtalt
API-/schema-/lesescope, basert på tekniske bevis og eiers fullførte lesekontroll.
Maskinell ekstern Cloudflare-avvisning er adskilt fra manuelt eierbevis.
Ingen applygodkjenning eller shared-aktivering følger av dette.
Se [datert evidens](../status/STAGING_PHASE_6A2_SCHEMA_DRY_RUN_2026-10-14.md).

`backfill_legacy_domain` er en operatørstyrt, eksplisitt migreringshandling for
eksisterende tilhørighet. Ingen bruker kan legge profil til en ny tenant gjennom
API/admin/import som følge av denne leveransen. Aktiv staff/platform-superuser-ID
registreres med operasjonell CLI-tilgang, miljø/databaseidentitet og godkjent plan.
Dette erstatter ikke agreement, membership, capabilities, revision/audit eller
privacyprojeksjon for senere shared handlinger. Global rollefallback er uendret.

Smalt ORM-vern og PostgreSQL-triggere verner strukturfelter/assignments, inklusive
bulk og samtidige parentendringer. Privat insertadgang gjelder bare tjenestens
valgte profil/tenant-tupler inne i transaksjonen og opphører ved feil. Batchregister
og eksplisitt read-back skiller PREPARED fra COMMITTED_VERIFIED uten blind retry.
Ingen beskyttelse mot DB-administrator som deaktiverer triggere er påstått.

Prosjekteier har godkjent midlertidig sletteavvisning ved senere backfill, også når
bare egen legacyassignment finnes. API gir 409, admin låser bound legacytenant og
viser protected-delete. Vanlig tillatt profilredigering fortsetter. Ingen ny
livssyklus eller assignmentfjerning er autorisert. **Historisk leveransestatus før staging:** Leveransen er gjennomgått uten blokkerende funn 2026-10-14 og publisert i PR #77. Kontrollert kode-merge uten deploy er bestilt; faktisk siste
head, merge og CI følger GitHub og SESSION WRAP-UP. Ikke staginganvendt eller aktivert. Se [runbook](../operations/LEGACY_DOMAIN_BACKFILL.md).

## Operatørbasert PK-shadow 2026-10-23

`SHARING_DOMAIN_SHADOW_ENABLED=False` er fail-closed standard. Gaten tillater
bare eksplisitt operatørkommando og gir ingen bruker eller request ny tilgang.
Aktive views, permissions og serializers er urørt; legacylesing er autoritativ.
Eksakt domain-/tenantscope valideres før måling i ett read-only snapshot.
Rapporten inneholder bare godkjent scope, driftsmetadata, aggregater og faste
avvikskoder, ingen profil-PK-er/-hashverdier eller rå person-/kontaktdata.
Dette er ingen aktivering av målarkitekturens shared capabilities/avtalekontrakt.
[Mandat, feil-/stoppkontrakt og aktivering](../operations/DOMAIN_READ_SHADOW.md).
**Staging 2026-10-24:** Én operatørmåling er teknisk verifisert med FULL_EQUAL;
ordinær API og varig miljø har fortsatt effektiv gate False. Aktive flags/mounts,
safety READY/cursor 13 og legacylesing er bevart. Autorisert teknisk backendlesing
brukte eksisterende plattformbruker innen read-only-transaksjon, uten ny login
eller sessionskriving. [Evidens og begrensninger](../status/STAGING_PHASE_6A_READ_SHADOW_2026-10-24.md).
Dette aktiverer ingen av de framtidige shared rettighetene nedenfor.

## Godkjent sharing-domain-sikkerhet – ikke implementert

[ADR-011](../decisions/ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md)
godkjenner målarkitekturen for deling innen eksakt SharingDomain. Dagens direkte
tenantroller og gruppefallback er fortsatt aktiv nåtilstand; ingen shared
capabilities eller agreementgate er implementert.

Framtidige domain-wide read-, match-, assignment- og writehandlinger skal kreve
alle disse kontrollene server-side:

- `user.is_active`
- aktiv `TenantMembership` i den aktive tenanten
- eksakt SharingDomain-likhet
- gjeldende, versjonert og auditerbar agreement acceptance
- eksplisitt capability for handlingen
- objekt-, assignment- og eventuelt image-home-scope

Alle menneskelige brukere, også plattform-superadmin, må akseptere gjeldende
agreement. Tenant-`SUPERADMIN` er ikke plattform-superadmin. Den konseptuelle
capabilityen `ADD_EXISTING_SHARED_ENTITY_TO_OWN_TENANT` gir bare assignment til
brukerens egen aktive tenant, aldri en vilkårlig annen tenant.

Dagens globale Django-gruppefallback skal fjernes eller begrenses før shared
capabilities aktiveres. Et globalt gruppenavn skal aldri automatisk gi rolle i
en vilkårlig tenant. Frontend-skjuling er ikke en sikkerhetsgrense, og alle
rolle-, membership-, agreement-, capability-, assignment- og domainbrudd skal
ha negative backendtester.

Canonical core kan redigeres av aktive plattform-superadmins,
tenant-superadmins, gruppeadmins og redigerere med øvrige porter oppfylt; leser
kan ikke skrive. Endringen gjelder alle assignments og krever audit og
revision-/stale-kontroll. Andre tenanters overlays skal aldri serialiseres.

## Godkjent sted-, kart- og providersikkerhet – ikke implementert

[ADR-012](../decisions/ADR-012-PLACE_IDENTITY_GEOGRAPHIC_CLASSIFICATION_AND_ACTOR_ONLY_MAPS.md)
bevarer alle ADR-011-portene. Global Place er bare offentlig geografisk
referansedata; OrganizationPlace/PersonPlace kan leses og skrives gjennom det
canonical objektets autoriserte SharingDomain-/assignmentkontekst. Geografiske
tenantforslag er rådgivende og kan aldri gi membership, capability, assignment
eller autorisasjon.

En autorisert tenantbruker/importreviewer kan gjennom en kontrollert server-side
tjeneste velge eksisterende eller opprette source-backed/brukerbekreftet
canonical Place, knytte det til eget autoriserte canonical objekt og eksplisitt
publisere OrganizationPlace med separat capability. Normalflyten krever ikke
plattform-superadmin, men håndhever duplicate-/similarity-, revision-/stale- og
auditkrav. Vanlig bruker kan ikke vilkårlig mutere eksisterende global sannhet;
merge, redirect/tombstone, deaktivering av referert Place og globale kilde-,
hierarki-, koordinat-, provider- eller multi-domain-konflikter krever
plattformcapability.

Editor- og PUBLIC-kart bruker separate read-only, dataminimerte actor-
projections. Personer, kontakter, private notater, andre tenanters overlays og
internal tags, private bildeoriginaler, credentials og audit-/agreementdetaljer
er forbudt i kartpayload og i sted-/kartproviderquery. PersonPlace har aldri eget
koordinat-, markør- eller kartproviderscope og utløser ingen
sted-/kartproviderquery med persondata. Et eksplisitt Place-oppslag før kobling
kan bare bruke stedsverdi og nødvendig geografisk kontekst. Dette hindrer ikke
at den provider-nøytrale Place-raden har lovlig Kartverket-/SSB-proveniens, og
endrer ikke den separate, eksplisitte og eksisterende providerkontrakten for
bildekandidatsøk.

En senere Google-aktivering krever separate, minst privilegerte Editor/PUBLIC-
browserkeys og eventuell servercredential, origin-/IP- og API-restriksjoner,
miljøisolasjon, kvoter, sanitert logging og default-off gates. Ingen key eller
Google-konfigurasjon finnes i dagens runtime.

Google-coordinate persistence krever en separat default-off lagrings-, backup-,
purge- og restore-reconciliation-gate; providerpålagt purge kan aldri stoppes av
featureflag eller rollback. Relevante Editor-/PUBLIC-/framtidige Google-flater
krever dessuten juridisk godkjente Customer Application-vilkår med gjeldende
Google Maps End User Additional Terms- og Privacy-lenker. Dette er separate
porter fra personvernerklæring, consent/brukerhandling og attribusjon.

## Godkjent planlagt bilderollematrise

[ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) beslutter en capability-basert bilderollematrise. Hele matrisen er ikke implementert; dagens generelle read/write/delete-regler gjelder fortsatt utenfor de eksplisitte bildehandlingene. 3E.4 implementerer det avgrensede takedown-subsettet server-side som beskrevet nedenfor. Fase 3F gjenbruker eksisterende tenant-scopede image write-capabilities for typed importbeslutninger; flagg, ImportRow og målobjekt er ikke en autorisasjon i seg selv.

I målarkitekturen:

- plattform-superadmin betyr dagens Django `is_superuser` eller en senere eksplisitt global principal og kan arbeide på tvers av tenants
- `TenantMembership.Role.SUPERADMIN` forblir tenant-avgrenset og får samme image-scope som gruppeadmin
- gruppeadmin kan utføre alle bildehandlinger, formell takedown, restore, retensjon og karantene i egen tenant
- plattform-superadmin og gruppeadmin/tenant-superadmin kan hente privat original innenfor sitt scope
- redigerer kan finne, laste opp, godkjenne, låse, erstatte, arkivere, gjenopprette og velge fallback, men får bare kontrollert review-preview og kan ikke hente privat original, utføre formell takedown eller administrere retensjon/karantene
- leser kan se bilde og vanlig status, men ikke sensitiv kilde, audit eller karanteneinformasjon

Rettighetene skal håndheves server-side per handling og objekt. Bilde-capabilities endrer ikke de separate rollespørsmålene for kontaktpublisering og full kontakteksport.

Legacyinventaret er en skrivebeskyttet operatørkommando og eksponerer aggregater som standard; `--verbose` redakterer credentials og alle queryverdier. Tenantbrukere med eksisterende image write-capability kan bare hente legacykandidater for en Organization i egen tenant. En typed importbeslutning krever aktiv autentisert principal med samme capability i samme tenant både ved oppretting og anvendelse; cross-tenant asset, rendition-sett, selection eller mål avvises. Beslutningen kan ikke endre publiseringsflagg.

## Godkjent public image runtime-sikkerhet – serving ACTIVE i staging

[ADR-009](../decisions/ADR-009-PUBLIC_IMAGE_RUNTIME_RELEASE_DELIVERY_AND_RESTORE_SAFE_DENY_STATE.md) fastsetter at public byte-serving autoriseres per release gjennom samme ledger/read-model som `PublicImageProjection`. En anonym sluttbruker trenger ikke innlogging, men Django-gaten skal avvise denied/retired/ukjent release, scope mismatch, upublisert aktør, ukjent cursor og ufullstendige eller korrupte filer før intern Nginx-serving. Artifact- og private roots får ingen anonym alias eller public mount.

Det restore-sikre off-server ankeret bruker minst privilegium. Fase 3E.1A har bevist host/systemd som execution placement uten safety-ledger-mount, Borg-klient, writersecret eller administratorcredential i API/web; admin-/recoverytilgang har separat custody. 3E.1B-broen er deployet som root-eid lokal Unix-socketfoundation uten å endre dette eierskapet; faktisk root-peer gjennom Docker, socket `0600` og containerisolasjon er liveverifisert i staging. Materialiseringsflagget er aktivt etter syntetisk reserve/activate-gate.

3E.1C legger til bare én read-only `authorize`-operasjon. Den krever eksakt release-, tenant-, Organization-, variant-, public-key- og checksum-scope og kan ikke skrive/repairere ledger, ankre, kjøre Borg eller hente generell historikk. En writer-preferred gate gjør at nye lesere ikke kan gå forbi ventende lifecycle-mutasjon. `web` får bare delivery-root read-only og supplementary GID `2000` for den dedikerte hostgruppen; den får ingen socket, artifacts, private filer, ledger eller credentials. Nginx kan bare lese etter Djangos interne redirect og nekter symlinks. Livegaten 2026-08-24 beviste disse grensene, negativ scope-autorisasjon, bridge-/filfeil, restart og sanitert logging. Servingflagget er fortsatt default-off i kode/eksempel og `True` bare i ignorert stagingmiljø. ADR-et lover ikke absolutt WORM eller vern mot kompromittert Hetzner control plane/root.

3E.4 håndhever formell takedown server-side: plattform-superadmin på tvers av tenants; aktiv tenant-`SUPERADMIN`/`GRUPPEADMIN` bare i egen tenant; `REDIGERER`, `LESER`, inaktive brukere, manglende medlemskap og globale Django-gruppenavn avvises. API-et mottar bare en allowlistet reason code og utleder Organizationens eksakte aktive release; caller kan ikke levere release, checksum, event-ID eller key. Koden og eksempelkonfigurasjonen er default-off, mens staginggaten har bevist konkret release-deny, tenant-scopet checksum-deny uten informasjonslekkasje, legacyguard, projection/gateway-samsvar, originblokkering, cacheverifikasjon og restore-safe no-reactivation. Global checksum-deny er ikke del av MVP-en.
