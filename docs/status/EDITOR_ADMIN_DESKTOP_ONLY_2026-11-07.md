# Admin bare på desktop – 2026-11-07

**ORDINÆRT MERGET / MAIN-CI GRØNN / FRONTEND-ONLY STAGINGVERIFISERT**

Eier har gjennomgått og godkjent øvrig UI fra PR #94–96 og bestilt denne eneste
korreksjonen helt til staging. [UI-6 §16](../features/UI_6_FELLES_SPEC.md#16-admin-bare-på-desktop--eierføring-2026-11-07)
er styrende. Base `6fd10fd5c32748b940bbbfc0ffcc47c325e95829`.

## Endring og lokal kontroll

Én egen klasse på den eksisterende Admin-lenken og display:none i eksisterende
max-width:900px-regel. Lenken er skjult, uten Tab-/tilgjengelighetsvalg, i mobilmenyen.
Fra 901 px beholder autorisert desktopbruker samme lenke, ikon og navigasjonsvern.
Ingen endring av can_access_admin, direkte Django-adminadgang, øvrig meny eller Kart.

Den eksisterende Admin-browsertesten er oppdatert til eierføringen. Den kontrollerer
1920→390→320→900→901→390→1920 uten reload: skjult Admin og fire aktive lenker +
deaktivert Kart på mobil; fem lenker + Kart på desktop. Nonstaff har ingen Admin
i DOM etter reload. Dette er syntetiske API-fixtures, ikke ekte admininnlogging.
Målrettet test og TypeScript/produksjonsbygg er grønne. Øvrige produktasserts beholdes.

## Leveranse og evidensgrense

Separat review, siste-head PR-CI, ordinær merge og main-CI er fullført før deploy.
Kun web/frontend ble bygget/gjenskapt. API/DB/containerdata, miljø, flagg, media,
static og sikkerhetsmekanismer beholdes. Ingen migrasjon, collectstatic,
rolleendring eller ny produktetappe. Ingen lokal PostgreSQL/Docker er nødvendig
for denne avgrensede stilendringen.

Stagingverifikasjonen kontrollerte eksakt frontendbundle og responsiv meny med bare
syntetisk autorisert API-visning i browser; ingen eksisterende adminsession eller
reelle tenant-/profil-/kontaktdata skal hentes. Slike browserbilder beviser
frontendvisningen på staging, ikke ny autentiserings-/RBAC-verifikasjon. Eksisterende
adgangskrav dekkes av kilde/CI og tidligere ekte kontroll. API-videresending/HTTP
kontrolleres uten innlogging. Detaljerte driftsverdier holdes på server; bare
kontrollstatus og kildecommit publiseres. Faktiske resultater følger nedenfor.


## Faktisk staging og publisert bevis

[PR #97](https://github.com/fredrik-stack/kreative-norge-crm/pull/97), head
`c740db79c720d1b34c0d8aff8bc9c8b142e4a1c2`, er separat skrivebeskyttet reviewet
ut fra base 6fd10fd uten kritiske/viktige funn. [PR-CI 42407991371](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/42407991371)
er SUCCESS, 6/6. Ordinær merge `a49b9d109e2c00f4cb000c31ed21c2a97db9d640` har
[main-CI 42408479236](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/42408479236)
SUCCESS, 6/6 på eksakt merge.

Kun web er bygget og gjenskapt fra denne kilden. De faktiske serverfilene og lokal
HTTP matcher kontrollert produksjonsbygg byte for byte; samme JS/CSS er lastet
over HTTPS i browser. Nginx 50x og read-only mounts består. API og DB har uendret
container/image/StartedAt/config/mounts; miljøfilen er uendret. Ingen API-restart,
migrate, collectstatic, aktivering eller profil-/kontakthandling.

Én fersk før-backup, full Borg-data-/arkivverifikasjon og isolert PostgreSQL-restore
er grønne. Private kopier av installerte backupscript ble brukt uten prune/compact;
installerte script er bevart. Restore fjernet bare sin egen isolerte container og
tilhørende anonyme volum; volumsettet er bevart. Backup-/verify-timere er
gjenopprettet active/enabled. Rollback til før-webimage og Git er klargjort, men
ble ikke utløst. Ingen backup-/DB-/miljøfingeravtrykk eller container-ID-er er
publisert; detaljene er private på staging.

[Syv responsive kontroller/nonstaff](evidence/editor-admin-desktop-staging-2026-11-07/browser-checks.json),
[deployattestasjon](evidence/editor-admin-desktop-staging-2026-11-07/deploy-checks.json),
[fem hele viewportbilder](evidence/editor-admin-desktop-staging-2026-11-07/index.html)
og [manifest](evidence/editor-admin-desktop-staging-2026-11-07/manifest.json) binder resultatene
til mergeversjonen. Faktisk stagingfrontend ble kontrollert ved 1920→390→320→900→901→390→1920:

- Admin skjult ved 320/390/900, ute av tilgjengelighetsvalgene og Tab-rekkefølgen.
- Admin synlig på 901/1920 ved syntetisk can_access_admin; samme href/ikon.
- Resizing begge veier uten reload; Kart deaktivert og øvrige menypunkter består.
- Nonstaff uten Admin i DOM på desktop etter reload.

Denne browserreisen brukte vanlig TLS-verifikasjon og staging-SNI/Host via en
midlertidig SSH/CONNECT-tunnel til Caddy, med utelukkende syntetiske API-data.
Alle øvrige API-kall var sperret. En gjenbrukt helpers no-slash continue-rute ble
fanget i separat operatørreview og eksplisitt overstyrt før kjøring. Ingen ekte
adminsession, kontoendring eller nye tenant-/profildata ble brukt. Beviset gjelder
frontendens visning gitt tillatelsesflagget; det er ikke ny backend-RBAC-/auth-
eller Cloudflare-edge-verifikasjon. Reell API-videresending og HTTP ble kontrollert server-side både før og etter
webbyttet uten innlogging. Egne lokale tunnel/proxy er stanset.

[Operatørreview/kildehashes](evidence/editor-admin-desktop-staging-2026-11-07/operator-review.json)
er separat og skrivebeskyttet, uten scripts/browser/nett/SSH/DB/writes. Sanitert
evidens publiseres med eget docsreview, PR-/main-CI og ordinær merge; docsmergen
skal ikke deployes, og dens egen mergestatus føres i PR uten ny dokumentasjonsrunde.
Ingen neste produktetappe er startet.
