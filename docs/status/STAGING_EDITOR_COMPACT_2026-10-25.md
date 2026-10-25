# Editor PR #92 – sluttgodkjent og teknisk stagingverifisert

**25.10.2026 · SAMLET VISUELT EIERGODKJENT / API+FRONTEND DEPLOYET / TEKNISK STAGINGVERIFISERT**

[Åtte stagingbilder](evidence/editor-staging-2026-10-25/index.html) ·
[manifest/SHA-256](evidence/editor-staging-2026-10-25/manifest.json) ·
[PR #92](https://github.com/fredrik-stack/kreative-norge-crm/pull/92).

## Mandat, aksept og kode

Prosjekteier ga25.10 samlet sluttgodkjenning av siste visuelle grunnlag på
head `4cdff63d0fb3432d7b2dacc181d9a23ce3a9fc91`: «Jeg er nå helt fornøyd og gir samlet
sluttgodkjenning.» Samme bestilling omfattet ordinær merge, main-CI og kontrollert
API+frontend-staging. Dette lukker den avgrensede PR-leveransen, ikke hele UI-6,
6A/6B/6C, Import2.0 eller Editor/PUBLIC-v1. Ingen ny produktetappe er startet.

- Ordinær kode-merge **`d698888ee851bd884e148b0bca8ae0b4f3219704`**, uten adminomgåelse.
- [PR-CI40233459542](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/40233459542) på eksakt godkjent head: SUCCESS6/6.
- [Main-CI40234720716](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/40234720716) på eksakt mergecommit: SUCCESS6/6 før drift.
- Tidligere66 frontendtester/24 Editor-reiser og versjonsbundne kode-/dokumentreviews
  står i [siste visuelle rapport](EDITOR_THUMBNAIL_VISUAL_REVIEW_2026-10-25.md) og PR.
  Ingen ny implementering eller lokal test-/Docker-runde er påstått i denne økten.

[UI-6 §14](../features/UI_6_FELLES_SPEC.md#14-samlet-sluttgodkjenning-og-teknisk-staging--2026-10-25)
er gjeldende leveransestatus. §10–13 er godkjent innen PR-scope: venstremeny,
kompakte profiler,148px kort/90px sentrert kvadrat, fem personkolonner,
metadatafarger og manuell person-/kontaktlagring. Grønn mobil-Rediger består.
Import v6 rev.4/O-24/5E og begge Google Maps-aktørkart består som avtalt v1-scope.

## Drift og versjonsidentitet

Fulgt [stagingrunbook](../../deploy/staging/README.md) og
[backup/restore](../operations/BACKUP_AND_RESTORE.md). Rent serverrepo ble
fast-forwardet fra `3ede68fd44b8bda42f99b2a7c8c8f7e37820669b` til eksakt kode-merge.
API-kilde før deploy var5c39ec5; webkilde3ede68f.154 API-/runtimefiler er hashbundet
til målcommiten; Python-avhengighetenes fingeravtrykk er uendret.

| Aktiv runtime | Identitet |
|---|---|
| API-container | `598cb50a1369f22376328e3735716c94d642b5afdc9b0aef8bd7ca963ac1f9be` |
| API-image | `sha256:b236d0f53194c697d6a995d3f1b59b17f78ee392ed835ea90c1d1fed79d0294f` |
| Web-container | `266f0764e8ec1705d5228c1df7acb6ae223651ad44034af374906425bc1fce52` |
| Web-image | `sha256:608df9dc06d90d707f2e152940cacf9a83ac397c5f82c45cffda14f308a94b68` |

Bare API og web ble kontrollert recreatet med kommandoavgrenset Compose API1.44.
Gammel Gunicorn ble avsluttet kontrollert med exit0, og fraværende imports/exports
ble kontrollert også i stoppet containerlag før fjerning. Direkte Gunicorn-kommando
unngikk migrate/collectstatic. **Null ventende eller utførte migrasjoner.**
Databasecontainer/volum, miljøfil/effektive flagg, mounts, media/static og Caddy
ble bevart. Ingen prune/compact, infraoppgradering eller produksjonsdeploy.

Lokalt bygg, kjørende webimage og faktisk HTTPS via Caddy-origin har identisk
index/JS/CSS; [eksakte bytes og SHA](evidence/editor-staging-2026-10-25/https-bundle.json).
De versjonerte assetnavnene er `index-Buhjlg5h.js` og `index-D9Qi-31M.css`.
Alle distfiler og eksakt assetsett ble kontrollert; nginx sin kjente50x.html
ble separat kontrollert mot baseline, ikke feilaktig regnet som Vite-bundle.

## Backup, restore og tilbakeføring

Tre ferske checkpoints er full repository-/arkivverifisert og isolert PostgreSQL-
restoreverifisert. Arkiv-ID/dumpchecksum er bundet til hvert arkiv og finnes i
[runtimeevidensen](evidence/editor-staging-2026-10-25/runtime.json).

| Tidspunkt | Arkiv |
|---|---|
| Før deploy | `kreative-norge-staging-20261025T212230Z` |
| Etter deploy | `kreative-norge-staging-20261025T212400Z` |
| Etter browserreise/cleanup | `kreative-norge-staging-20261025T212716Z` |

Privat kopi av installerte backupskript utelot bare prune/compact; restorekopien
fjernet sin egen isolerte container med eget anonymt volum. Installerte skript
forble uendret. Ingen restvolumer fra de isolerte restorekjøringene. Begge
backuptimere er bekreftet active/enabled; servicejobbene avsluttet.

Gammelt API-image `sha256:63000cdd2a3e4b25e8a49768466a6eade74407d39a52a6291654b3772c0d0ad5` og webimage `sha256:b6c0e8152c3d9f714551843f27d4aa31e24346d4d68e223813a8f256f62816c6`
er bevart som `kreative-norge-crm_api:pr92-rollback` og
`kreative-norge-crm_web:pr92-rollback`, med privat kommandokonfigurasjon og
verifisert statickopi. Ved regressjon tilbakeføres bare API/web, uten schema-/
datareversering eller media-/ledger-/volumsletting. **Ingen rollback ble utført.**
Operatørreview lukket før drift fire konkrete feilforløp: delvis web-stopp,
ukjent API-fjerningsutfall, timerfeil og feilklassifisering av50x.html. Siste
reviewede deployharness SHA256 `ab676cdd4471cc3095f216a64b71b4e628083e5a356c2d52ee58d9107d886dab`.
Dette var separat skrivebeskyttet statisk review, ikke en utført feilinjeksjon.

## Ekte stagingreise og bevisgrenser

Chromium145.0.7632.6 brukte faktisk `https://staging.northernsound.no` gjennom
midlertidig, lokalt avgrenset CONNECT-/SSH-transport til Caddy-origin. TLS/SNI,
Host, secure session, faktisk innlogging og CSRF var normale. Ingen API-mocks,
nettverksfeilinjeksjon, authomgåelse eller ny Cloudflare-kantverifikasjon.
Kun to syntetiske upubliserte aktører, én syntetisk person og én midlertidig
nonstaff gruppeadmin i tenant1 ble brukt; eksisterende taksonomi ble bare gjenbrukt.

[Ti kontroller](evidence/editor-staging-2026-10-25/checks.json) er grønne:

1. Faktisk visningsnavn/tenantrolle, ikke Admin for nonstaff; annen tenant gir403.
2.1920/390/320px: kort148px/lik bredde, kvadrat90px/senteravvik<0,5CSSpx,
   brun/blå/grønn metadata og ingen horisontal side-overflyt.
3. Alle tre bredder: synlig/udekket grønn Rediger i modal, riktig redigeringsrute,
   to Lagre og én Slett under eksisterende rolle.320px-modal er rullet til footer.
4. Nederste skjemabundne aktør-Lagre skriver og gir korrekt API-read-back.
5. UI-opprettet person med fire private kontakter; lokale endringer/blur gir null
   writes. Lagre gir korrekt verdi, samme kontakt-ID-sett og sann lagretstatus.
6. Ekstra kontakt fjernes lokalt først; Lagre sletter eksakt kjent-ID.
7. Fem desktopkolonner og typefarger i personoversikt; mobil uten sideoverflyt.
8. Eksisterende Import-/Eksport-ruter lastes uten jobb-/import-/eksportwrites.

Åtte hele viewport-PNG er vedlagt:1920×1080 og390/320×844; ingen fullsidebilder
eller utsnitt. Personoversikten har1920/390. Syntetiske profiler er filtrert frem,
og bildene er tekniske bevis, ikke nytt designforslag eller ny UX-/brukertestrunde.
Ingen ny200%-zoom-/leserrolle-/ukjent-POST-feiltest i staging; tidligere lokale
versjonsbundne kontroller og grønn main-CI er adskilt fra denne stagingreisen.
Eiers samlede visuelle aksept ble mottatt **før** deploy; ingen senere manuell
eierbrowserkontroll påstås eller kreves som ny godkjenningsrunde i dette mandatet.

## Bevaring og avsluttet tilstand

Syntetiske profiler ble slettet gjennom ordinært API med identitetskontroll og404-
read-back; eksakt testbruker/medlemskap ble fjernet og testøkten logget ut.
Ingen bred cleanup, sekvensreset, reell profilendring eller assignment/backfill.
Normale PK-sekvenser og authtrafikk kan være påvirket; ingen live restore er utført.

Etter cleanup matcher **eksakte radfingeravtrykk for alle eksisterende CRM-tabeller**
før-baselinen, ikke bare antall. [Sluttkontroll](evidence/editor-staging-2026-10-25/preservation.json):
128 aktører,157 personer,223 kontakter,176 aktør/personkoblinger,60 tags;
128/157 assignments og0/0 noteoverlays. Media/static og miljø/mounts er uendret.
Safety READY/cursor13 og permanent denyhistorikk er bevart. Shadow-/overlaygater
er effektivt av, Import image decisions av; tidligere aktive bildegater består.

[PUBLIC-sammenligning](evidence/editor-staging-2026-10-25/public-comparison.json)
bekrefter uendret API-katalogbytefingeravtrykk,122=1asset+121fallback,
alle seks canonical bildevariantbytes og begge representative detalj-HTTP200.
PUBLIC-listens rå HTML-hash er **ikke lik**: eksisterende `random.shuffle(tags)`
stokker filterrekkefølgen per respons. Dette ble bekreftet med to ferske kall og
uendret listekilde; full HTML-bytelikhet påstås ikke. Aktiv cutover hadde allerede
grønn detaljtagg; PR-ens malretting gjelder også eldre detaljvariant.
En tidlig read-only probe antok intern `id` i PUBLIC-API; den feilet uten write og
ble rettet til eksisterende orgnummer/redirect-rute før full sammenligning.

Staging er teknisk verifisert og driftsvinduet avsluttet. Nødvendig sanitert evidens
publiseres i egen docs-PR med separat review/merge/CI. GitHub er fasit for dens
faktiske head/merge; dokumentasjonsmerge utløser ingen deploy eller ny rapportrunde.
