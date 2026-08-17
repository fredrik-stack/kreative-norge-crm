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

[ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) beslutter en capability-basert bilderollematrise. Den er ikke implementert; dagens generelle read/write/delete-regler gjelder fortsatt.

I målarkitekturen:

- plattform-superadmin betyr dagens Django `is_superuser` eller en senere eksplisitt global principal og kan arbeide på tvers av tenants
- `TenantMembership.Role.SUPERADMIN` forblir tenant-avgrenset og får samme image-scope som gruppeadmin
- gruppeadmin kan utføre alle bildehandlinger, formell takedown, restore, retensjon og karantene i egen tenant
- plattform-superadmin og gruppeadmin/tenant-superadmin kan hente privat original innenfor sitt scope
- redigerer kan finne, laste opp, godkjenne, låse, erstatte, arkivere, gjenopprette og velge fallback, men får bare kontrollert review-preview og kan ikke hente privat original, utføre formell takedown eller administrere retensjon/karantene
- leser kan se bilde og vanlig status, men ikke sensitiv kilde, audit eller karanteneinformasjon

Rettighetene skal håndheves server-side per handling og objekt. Bilde-capabilities endrer ikke de separate rollespørsmålene for kontaktpublisering og full kontakteksport.

## Godkjent public image runtime-sikkerhet – ikke implementert

[ADR-009](../decisions/ADR-009-PUBLIC_IMAGE_RUNTIME_RELEASE_DELIVERY_AND_RESTORE_SAFE_DENY_STATE.md) fastsetter at public byte-serving autoriseres per release gjennom samme ledger/read-model som `PublicImageProjection`. En anonym sluttbruker trenger ikke innlogging, men Django-gaten skal avvise denied/retired/ukjent release, scope mismatch, upublisert aktør, ukjent cursor og ufullstendige eller korrupte filer før intern Nginx-serving. Artifact- og private roots får ingen anonym alias eller public mount.

Det restore-sikre off-server ankeret skal bruke minst privilegium. Ubegrenset/admin Storage Box-credential skal ikke ligge i CRM-runtime, og admin-/recoverytilgang har separat custody. Eksakt execution placement og credentialmodell må bevises i fase 3E.1A; ADR-et lover ikke absolutt WORM eller vern mot kompromittert Hetzner control plane/root.

Formell takedown forblir deaktivert frem til fase 3E.4 har bevist gruppeadmin-/tenant-superadmin-/plattform-superadmin-scope, konkret release-deny, tenant-scopet checksum-deny uten informasjonslekkasje, legacyguard, projection/gateway-samsvar, originblokkering, cache expiry/purge/verifikasjon og restore-safe no-reactivation. Global checksum-deny er ikke del av MVP-en uten senere konkret behov og egen beslutning.
