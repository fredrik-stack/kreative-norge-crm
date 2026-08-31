# Security and Roles

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

Canonical Place, providerreferanser og aktive kartpunkter forvaltes gjennom en
egen plattformcapability med revision-/stale-kontroll og audit. En tenantbruker
kan velge Place og endre typed stedskobling innen eget objektscope, men kan ikke
mutere eller deaktivere global geografisk sannhet på tvers av SharingDomains.

Editor- og PUBLIC-kart bruker separate read-only, dataminimerte actor-
projections. Personer, kontakter, private notater, andre tenanters overlays og
internal tags, private bildeoriginaler, credentials og audit-/agreementdetaljer
er forbudt i kartpayload og providerquery. PersonPlace har aldri eget Google-,
koordinat-, markør- eller kartproviderscope og utløser ingen providerquery med
persondata. Dette hindrer ikke at den provider-nøytrale Place-raden har lovlig
Kartverket-/SSB-proveniens.

En senere Google-aktivering krever separate, minst privilegerte Editor/PUBLIC-
browserkeys og eventuell servercredential, origin-/IP- og API-restriksjoner,
miljøisolasjon, kvoter, sanitert logging og default-off gates. Ingen key eller
Google-konfigurasjon finnes i dagens runtime.

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
