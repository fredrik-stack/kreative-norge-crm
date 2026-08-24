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

Systemet bruker Django session-auth og CSRF. Kombinasjonen av tenant-medlemskap, globale Django-grupper og Django-superuser skal beskrives mer detaljert i neste fase.

## Godkjent planlagt bilderollematrise

[ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) beslutter en capability-basert bilderollematrise. Hele matrisen er ikke implementert; dagens generelle read/write/delete-regler gjelder fortsatt utenfor de eksplisitte bildehandlingene. 3E.4 implementerer det avgrensede takedown-subsettet server-side som beskrevet nedenfor.

I målarkitekturen:

- plattform-superadmin betyr dagens Django `is_superuser` eller en senere eksplisitt global principal og kan arbeide på tvers av tenants
- `TenantMembership.Role.SUPERADMIN` forblir tenant-avgrenset og får samme image-scope som gruppeadmin
- gruppeadmin kan utføre alle bildehandlinger, formell takedown, restore, retensjon og karantene i egen tenant
- plattform-superadmin og gruppeadmin/tenant-superadmin kan hente privat original innenfor sitt scope
- redigerer kan finne, laste opp, godkjenne, låse, erstatte, arkivere, gjenopprette og velge fallback, men får bare kontrollert review-preview og kan ikke hente privat original, utføre formell takedown eller administrere retensjon/karantene
- leser kan se bilde og vanlig status, men ikke sensitiv kilde, audit eller karanteneinformasjon

Rettighetene skal håndheves server-side per handling og objekt. Bilde-capabilities endrer ikke de separate rollespørsmålene for kontaktpublisering og full kontakteksport.

## Godkjent public image runtime-sikkerhet – serving ACTIVE i staging

[ADR-009](../decisions/ADR-009-PUBLIC_IMAGE_RUNTIME_RELEASE_DELIVERY_AND_RESTORE_SAFE_DENY_STATE.md) fastsetter at public byte-serving autoriseres per release gjennom samme ledger/read-model som `PublicImageProjection`. En anonym sluttbruker trenger ikke innlogging, men Django-gaten skal avvise denied/retired/ukjent release, scope mismatch, upublisert aktør, ukjent cursor og ufullstendige eller korrupte filer før intern Nginx-serving. Artifact- og private roots får ingen anonym alias eller public mount.

Det restore-sikre off-server ankeret bruker minst privilegium. Fase 3E.1A har bevist host/systemd som execution placement uten safety-ledger-mount, Borg-klient, writersecret eller administratorcredential i API/web; admin-/recoverytilgang har separat custody. 3E.1B-broen er deployet som root-eid lokal Unix-socketfoundation uten å endre dette eierskapet; faktisk root-peer gjennom Docker, socket `0600` og containerisolasjon er liveverifisert i staging. Materialiseringsflagget er aktivt etter syntetisk reserve/activate-gate.

3E.1C legger til bare én read-only `authorize`-operasjon. Den krever eksakt release-, tenant-, Organization-, variant-, public-key- og checksum-scope og kan ikke skrive/repairere ledger, ankre, kjøre Borg eller hente generell historikk. En writer-preferred gate gjør at nye lesere ikke kan gå forbi ventende lifecycle-mutasjon. `web` får bare delivery-root read-only og supplementary GID `2000` for den dedikerte hostgruppen; den får ingen socket, artifacts, private filer, ledger eller credentials. Nginx kan bare lese etter Djangos interne redirect og nekter symlinks. Livegaten 2026-08-24 beviste disse grensene, negativ scope-autorisasjon, bridge-/filfeil, restart og sanitert logging. Servingflagget er fortsatt default-off i kode/eksempel og `True` bare i ignorert stagingmiljø. ADR-et lover ikke absolutt WORM eller vern mot kompromittert Hetzner control plane/root.

3E.4 håndhever formell takedown server-side: plattform-superadmin på tvers av tenants; aktiv tenant-`SUPERADMIN`/`GRUPPEADMIN` bare i egen tenant; `REDIGERER`, `LESER`, inaktive brukere, manglende medlemskap og globale Django-gruppenavn avvises. API-et mottar bare en allowlistet reason code og utleder Organizationens eksakte aktive release; caller kan ikke levere release, checksum, event-ID eller key. Koden og eksempelkonfigurasjonen er default-off, mens staginggaten har bevist konkret release-deny, tenant-scopet checksum-deny uten informasjonslekkasje, legacyguard, projection/gateway-samsvar, originblokkering, cacheverifikasjon og restore-safe no-reactivation. Global checksum-deny er ikke del av MVP-en.
