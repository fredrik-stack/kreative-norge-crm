# Admin bare på desktop – 2026-11-07

**IMPLEMENTERT PÅ BRANCH / LOKALT VERIFISERT – MERGE/STAGING GJENSTÅR**

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

Separat review, siste-head PR-CI, ordinær merge og main-CI kreves før deploy.
Kun web/frontend skal bygges/gjenskapes. API/DB/containerdata, miljø, flagg, media,
static og sikkerhetsmekanismer beholdes. Ingen migrasjon, collectstatic,
rolleendring eller ny produktetappe. Ingen lokal PostgreSQL/Docker er nødvendig
for denne avgrensede stilendringen.

Staging skal verifisere eksakt frontendbundle og responsive meny med bare
syntetisk autorisert API-visning i browser; ingen eksisterende adminsession eller
reelle tenant-/profil-/kontaktdata skal hentes. Slike browserbilder beviser
frontendvisningen på staging, ikke ny autentiserings-/RBAC-verifikasjon. Eksisterende
adgangskrav dekkes av kilde/CI og tidligere ekte kontroll. API-videresending/HTTP
kontrolleres uten innlogging. Detaljerte driftsverdier holdes på server; bare
kontrollstatus og kildecommit publiseres. Faktiske resultater kommer etter deploy.
