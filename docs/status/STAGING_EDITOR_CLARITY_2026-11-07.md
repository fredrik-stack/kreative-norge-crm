# Editor CRM – kontrollert API- og frontend-staging 2026-11-07

**IMPLEMENTERT / ORDINÆRT MERGET / MAIN-CI GRØNN / TEKNISK STAGINGVERIFISERT**

[18 hele viewportbilder](evidence/editor-clarity-staging-2026-11-07/index.html) ·
[manifest/SHA-256](evidence/editor-clarity-staging-2026-11-07/manifest.json) ·
[lokalt kode-/tekstgrunnlag](EDITOR_CLARITY_REVIEW_2026-11-07.md).

## Versjon og mandat

[PR #94](https://github.com/fredrik-stack/kreative-norge-crm/pull/94) har base
`5cc6e966d211c6c6a969b63e7f8380c751e6cb2e`, separat reviewet runtime
`582454101114c4baef70cc833ca5282345702940` og docshead
`105f8544122bc2b88e0830adf4df4e86cbf63121`. Produksjonskode er uendret mellom
runtime og docshead. [PR-CI 42401321690](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/42401321690)
er SUCCESS, 6/6 på siste head. Ordinær merge er
`fe28c5b66d11e312b976c3ff53ff088f09d75d6e`; [main-CI 42401986176](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/42401986176)
er SUCCESS, 6/6 på denne eksakte mergecommiten.

API og frontend på staging kjører denne mergeversjonen. Ny kode-/stagingleveranse
følger [eiers §15](../features/UI_6_FELLES_SPEC.md#15-editor-identitet-og-lesbarhet--eierbestilling-2026-11-07),
inkludert uttrykkelig deaktivert Kart. Ny visuell forhåndsgodkjenningsgate er ikke
innført. Dette dokumenterer teknisk verifikasjon; prosjekteiers nye manuelle
visuelle sluttaksept er ikke påstått, og hele UI-6/v1 ferdigmeldes ikke.

## Deploy og bevaring

- Fersk før-backup, full Borg-data-/arkivverifikasjon og isolert PostgreSQL-restore
  var grønne før bytte. API+web ble bygget fra eksakt grønn merge. Bare API/web
  ble gjenskapt; API stoppet kontrollert med Gunicorn/SIGTERM og exit0.
- Direkte Gunicorn-oppstart omgår standardkommandoens migrate/collectstatic.
  Ingen migrasjoner/collectstatic ble kjørt; tom migrasjonsplan er verifisert.
  Backendkilder samsvarer med merge; avhengigheter er uendret. Webbundle samsvarer
  byte for byte med det lokale kontrollerte produksjonsbygget. Lokal HTTP og
  faktisk HTTPS-browser bruker denne bundlen. Nginx sin eksisterende50x-side er
  bevart separat fra Vite-assettene.
- Databasens opprinnelige container/identitet består. Eksakte radfingeravtrykk for
  alle CRM-tabeller, også M2M, ble sammenlignet i repeterbar skrivebeskyttet
  transaksjon før deploy og etter begge syntetiske rydderunder. Alle eksisterende
  rader er uendret. Ingen deduplisering, assignment, ombinding eller catch-up.
- Private bilder, renditions, public delivery, static, miljøfil/-verdier og safety
  er sammenlignet på server og bevart. Tidligere gates består; ingen ny aktivering.
  Containerlokale imports/exports var fraværende, også kontrollert før fjerning av
  gammel API. Ingen filer fra slike områder ble kastet.
- PUBLIC API og seks eksisterende asset-/fallbackvarianter er uendret. Aktiv
  PUBLIC-detalj har ikke Primærlenke; Nettside består. Listen er ikke påstått
  identisk HTML-byte for byte: eksisterende tilfeldig taggrekkefølge består.
- To etter-backuper, full verifikasjon og isolert restore fulgte de to ferdige
  syntetiske rydderundene. Totalt tre ferske checkpoints er grønne. Backup-/verify-
  timere ble midlertidig stanset rundt jobbene og kontrollert aktive/enabled etter
  hver runde. Ingen prune/compact; bare private kopier av backupscriptet ble brukt.
  Restore-opprydding fjernet bare sin egen isolerte container/tilhørende anonyme
  volum. Installerte backupscript er bevart.

Detaljerte DB-/media-/miljø-/safety-/backupfingeravtrykk og arkividentiteter forblir
root-only på staging. Sanitert evidens inneholder bare kontrollstatus/kildecommit,
syntetiske browserbilder og lokale operatørkildehashes. En første planlagt eksport
av slike detaljer ble avvist av automatisk godkjenningskontroll før kjøring;
serverbasert verifikasjon med kun PASS/FAIL-retur ble deretter godkjent og brukt.
Ingen eksisterende credentials eller reelle person-/kontaktdata ble hentet.

[Deployattestasjon](evidence/editor-clarity-staging-2026-11-07/deployment.json),
[første sluttkontroll](evidence/editor-clarity-staging-2026-11-07/server-checks-cycle1.json)
og [endelig sluttkontroll](evidence/editor-clarity-staging-2026-11-07/server-checks.json)
binder de publiserte resultatene til kildeversjonen.

## Ekte browserreise: 16 hovedkontroller + 2 mobilhandlingskontroller

Vanlig HTTPS, TLS-verifikasjon, staging-host/SNI, Django-session og CSRF brukes.
En midlertidig localhost CONNECT-proxy tillot bare staging gjennom SSH til Caddy;
dette er ikke et nytt bevis for Cloudflare-kanten. API-er/nettverk ble ikke mocket.
Ingen auth-/rettighetsomgåelse eller eksisterende brukerkonto ble brukt.

En ny, egen syntetisk tenant med nonstaff-/ikke-superbruker og gruppeadmin-
medlemskap fikk upubliserte testprofiler. Passord ble generert lokalt og sendt inn.
41 aktører i første runde ga reell scrolling også ved 1920×1080. Ekte API opprettet
profiler, fem egne tags, kontaktkanaler og personkobling. Ny, separat syntetisk
syklus ga to supplerende mobilbilder etter at første syklus var fullstendig ryddet.

| Kontroll | Resultat |
|---|---|
| Ekte innlogging, nøyaktig én egen tenant, nonstaff og riktig bundle/Editor CRM | PASS |
| Samme ikoner, deaktivert Kart, ingen Admin for nonstaff, ingen horisontal overflyt | PASS 1920/390/320 |
| Kort148px, kvadrat90px sentrert; navn innen tekstkolonnen, vekt600, mobilnavn17px/sted13px | PASS 1920/390/320 |
| Synlige tags passer i faktisk restareal; +N er presist, alle fem i modal | PASS 1920/390/320 |
| Klikk kontaktperson, eget personkort, browser-Tilbake/knapp til aktør; Escape lukker aktørkortet | PASS 1920/390/320 |
| Faktisk rullet oversikt → Rediger aktør → scroll0 | PASS 1920/390/320 |
| Bare én synlig første e-post-/telefonetikett; korrekt tilgjengelig navn | PASS 1920/390/320 |
| Idle Klar borte; ekte UI-lagring av tittel med API-readback og bevarte kontaktkanaler | PASS |
| Ekte leser ser kontaktkort, mangler Rediger/Import og får 403 ved POST | PASS 390 |
| Grønn Rediger i mobilmodal: normal intern rulling, innen viewport, udekket klikksenter og faktisk redigeringsrute | PASS 390/320 |

[Hovedjournal](evidence/editor-clarity-staging-2026-11-07/browser-checks.json) og
[mobiltillegg](evidence/editor-clarity-staging-2026-11-07/mobile-action-checks.json)
har 16+2 kontroller.18 originale hele viewport-PNG dekker 1920×1080 og390/320×844.
Escape fra personkort tilbake til aktør er lokalt E2E-verifisert; denne
stagingreisen testet Escape på aktørkortet. Aktørkortets første bilder viser toppen; de to handlingsbildene er rullet inni
modalen og viser Rediger. Ingen utsnitt eller ny Importillustrasjon.

Egne profiler/relasjoner/kanaler/tags ble slettet med eksakt tenant-/identitetsguard
og 204/404-kontroll. Bare eget testmedlemskap skiftet til leser og tilbake; egen
bruker/tenant ble fjernet etter at barn var borte. Fullradkontroll etterpå beviser
både opprydding og at eksisterende CRM-rader består. Sekvenser ble ikke nullstilt.
Lokalt testpassord, egen Vite og den midlertidige tunnel/proxy er fjernet/stanset.

## Review, dokumentasjon og avgrensning

Separat skrivebeskyttet kodereview lukket to funn før merge: eget historietrinn
for personkort og korrekt bredde/ellipsis på 320px. Samlet base→5824541 og
kodeleveransens docs/evidens på105f854 har ingen åpne kritiske/viktige funn.
Operatørreview lukket en feil som kunne rapportert PASS etter avbrutt/tilbakerullet
deploy; sluttPASS krever nå frisk verifisert runtime, ingen deployfeil og aktive
timere. Browserhelperens opprydding omfatter også negativproben ved uventet 201.
Supplerende mobilhelper er separat kontrollert. Revieweren kjørte ingen scripts,
nettverk, SSH, DB eller browser. [Versjonsbinding](evidence/editor-clarity-staging-2026-11-07/operator-review.json).

Lokalt er66 Vitest, TS/bygg,32 eksplisitte Editor-reiser og to DB-frie PUBLIC-
malrenderinger grønne; bredere backend-/PUBLIC-reiser er grønne i 6/6-CI.
Ingen lokal Docker var nødvendig; remote Docker bygget API/web og kjørte isolert
restore. Publisering av denne rene dokumentasjonen følger egen separat review,
PR-/main-CI og ordinær merge. Dokumentasjonsmergen skal ikke deployes; endelig
publiseringsstatus hører til PR-en, uten ny dokumentasjonsrunde for dens egen merge.

PUBLIC beholder Kreative Norge. URL-data/API-kompatibilitet, lagrings-/publiserings-
vilkår, metadatafarger, Import v6 rev.4/O-24 og godkjent5E består. Ingen modell-/
schemaendring, backfill, shared-/overlay-/provider-/kartaktivering, produksjonsdeploy,
ny formell brukertest eller neste produktetappe inngår.


## Avgrenset CI-oppfølging – dialogfokus før Escape

Etter dokumentasjonsmerge `e9a405612007f7ca46cc1dfdf6cc2c3af5be9520` feilet
[main-CI 42404083399](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/42404083399)
i én av 36 browserreiser: 320px-steget som trykker Escape umiddelbart etter klikk
på kontaktpersonen. De 35 øvrige var grønne. CI-feilkonteksten viser oversikten
uten dialog etter tastetrykket. Samme uendrede test var grønn i 12 lokale gjentakelser;
den eksakte hendelsesrekkefølgen lot seg ikke gjenskape lokalt.

Routeren bruker startTransition. Klikk alene beviser ikke at persondialogens
mount-effect har flyttet fokus og bundet Escape. Testen avventer derfor nå
`toBeFocused()` på den eksakt navngitte persondialogen før første Escape, og
på aktørdialogen før andre Escape. Alle opprinnelige utfallsasserts beholdes;
ingen kunstig fokus, sleep, økt timeout eller retry er lagt til. Dette lukker en
konkret mangel i testens beredskapskontroll. Overgangsracet er en begrunnet
rotårsakshypotese; ingen runtimefeil er påvist fra dette alene.

Sluttvarianten med begge fokusvilkår er grønn i 36 målrettede lokale gjentakelser:
12 hver ved 1920/390/320. Alle opprinnelige etterkontroller består.

Bare test/dokumentasjon endres. De 18 stagingkontrollene, bildene, manifestet og
deployet merge fe28c5b er uendret. Ingen ny deploy eller stagingkjøring følger av
rettingen. Målrettede sluttresultater, separat review og fersk PR-/main-CI spores
i testoppfølgingen som lenkes fra [PR #95](https://github.com/fredrik-stack/kreative-norge-crm/pull/95),
uten en ny dokumentasjonsrunde for oppfølgingens egen merge.
