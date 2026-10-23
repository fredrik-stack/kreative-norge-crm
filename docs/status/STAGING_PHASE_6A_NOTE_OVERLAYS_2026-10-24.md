# ADR-011 trinn 7 – inaktiv notatgrunnmur i staging

**Dato:** 2026-10-24, Europe/Oslo. **Status:** TEKNISK SCHEMA-/STAGINGVERIFISERT; TOMME OVERLAYS / GATE AV.
Ingen notater er flyttet, ingen tags klassifisert og ingen leser/writer lagt om. Hele trinn 7 og 6A er ikke ferdig.

## Mandat, review og runtime

Prosjekteier bestilte additiv grunnmur, avgrenset inventar og sammenhengende leveranse. [Mandat, lagringskontrakt og rutematrise](../operations/TENANT_NOTE_OVERLAYS.md).
- [Kode-PR #85](https://github.com/fredrik-stack/kreative-norge-crm/pull/85): faktisk separat, skrivebeskyttet review uten kritiske/viktige funn på base `2181ceee598965ab4083226443dcce885d44db51` / head `f82717b4d96b55d980ad3cdf5a2d203341de83a8`. [Versjonsbundet resultat](https://github.com/fredrik-stack/kreative-norge-crm/pull/85#issuecomment-6376197042).
- Ordinær merge og deployet kode: `5c39ec51b3f5a7af20f05f2367d51afa0075e952`.
- [PR-CI 40035348969](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/40035348969) og [main-CI 40035930772](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/40035930772): SUCCESS, 6/6 før staging.
- 18 målrettede lokale PostgreSQL 16-tester bestod; 179 samlet (14 første + 165 eksisterende regresjoner), deretter alle 18 inklusive inventar. Modell-/migrasjonssamsvar, lenker og diffcheck bestod.
- Gammel runtime: `ad876846275ff46b3d2827a9507598ecf3ba6e1d`, image `sha256:3928cec7d7b3795049cabee8485af46bb88944e5ad644d425041ad7096f794d5`.
- Faktisk nytt image: `sha256:63000cdd2a3e4b25e8a49768466a6eade74407d39a52a6291654b3772c0d0ad5`; API `d3be6947c1def8679eb69597025498729e5055267397dc73006103172b65d6e3`, running med restart count 0.
- 150 gamle og 154 målfiler ble sammenholdt med eksakte Git-baseliner, både image og kjørende ny kode. Dependencies-fingerprint uendret. Hele runtimeforskjellen var gjennomgått: nye modeller/guard/migrasjon/tester/inventarskript og default-off setting; aktive views, serializers, admin, import, frontend og Compose var urørt.

## Kontrollert schema-apply og drift

Fersk preflight bekreftet database `postgresql:7621672066239828005:crm_db`, ren gammel runtime, eksisterende safety og backupdrift. Målimage hadde eksakt én forward-migrasjon, `0035_tenant_note_overlay_foundation`, og uendret eksisterende CRM-innhold før apply.

0035 ble kjørt eksplisitt med MigrationExecutor, bare schemaoperasjonene og migrasjonsregistreringen, uten post_migrate-signaler, contenttype-/permissionopprettelse, seed eller datakopiering. Migrasjonsprosessen hadde PGOPTIONS lock timeout 2 s / statement timeout 30 s. Etterpå var planen tom, begge overlaytabeller tomme, PK/unikhet/FK og begge aktiverte identity-triggere verifisert.

Gammel API ble stoppet ved TERM til verifisert Gunicorn-master med exit 0. Bare API ble recreatet; Gunicorn startet direkte uten migrate/collectstatic. Nginx ble testet/reloadet for ny upstream. Web/DB beholdt ID, image og restart count. Docker 29.1.3 / Compose 1.29.2 og kommandoavgrenset API 1.44 ble beholdt.

Imports/exports var fraværende både i preflight og ved kontroll av stoppet gammel container før fjerning. Gammelt image, privat konfigurasjonsgrunnlag og tar-verifisert statickopi ble beholdt som lokal runtime-rollback. Ingen schema-reverse, live restore, generell prune eller infraoppgradering.

Separat statisk driftsreview fant først manglende migrasjonstimeouts og ufullstendig nginx-/helsekontroll ved eventuell rollback. Begge ble rettet før kjøring. Endelig SHA-bundet helper og siste stopped-layer-filkontroll ble reviewet uten viktige funn. Ingen feil eller tilbakeføring oppstod under denne utføringen.

## Arkivbundne checkpoints

Privat kopi av eksisterende backupmodul utelot prune/compact; restorekopien fjernet bare sin egen isolerte restorecontainer med eget anonymt volum. Installerte skript forble uendret. Begge checkpoints hadde full repository-/dataverifikasjon og isolert PostgreSQL-restore med eksisterende tabell-/mediakontroller. Arkiv-ID og dumpchecksum ble kontrollert mot hvert arkiv før/etter restore; pre-ID ble lest tilbake etter post. Ingen restorevolumer ble etterlatt.

| Checkpoint | Arkiv | Arkiv-ID | Dump SHA-256 |
| --- | --- | --- | --- |
| pre | `kreative-norge-staging-20261023T225509Z` | `b301c5bf98235ef929e46ddec7f8b3a603313a66536b23edd18ccf521a09e8df` | `74af868b5c8cd9dc64373e8508d50e10f78db1f82672cd39e974c64186214efb` |
| post | `kreative-norge-staging-20261023T225625Z` | `9dc60fe159a73b69aee024ed912ce3a252093d82ff387134d37d0e6c324aa7b0` | `60564163bf3956d21d43f852dd16fe314e6348651f29a587e602399f95272f3e` |

Images/statickopi er separat lokalt tilbakeføringsgrunnlag, ikke påstått Borg-dekning. Begge eksisterende timere er bekreftet active/enabled, med inaktive services ved sluttkontroll.

## Ett notat-/taginventar

Inventarversjon 1; `ops/staging/inventory-tenant-notes.py` fra deployet SHA. Én kjøring, exit 0; ingen gjentakelse av PK-shadow eller duplikatinventar.
- Snapshot: `25162:25162:`.
- UTC: `2026-10-23T22:56:17.094047+00:00`–`2026-10-23T22:56:17.107870+00:00` (2026-10-24 kl. 00:56:17 CEST).
- Samme forbindelse: REPEATABLE READ READ ONLY før første datalesing; snapshot/isolation/read-only bekreftet ved start/slutt; transaksjonslokale statement 30 s / lock 2 s.
- Domain `1 / musikkontoret / Musikkontoret` og hele eksakte tenantsettet nedenfor revalidert. Alle 14 modell-/tenantkombinasjoner fullført. Notatkategorier beregnet i SQL uten henting av rå notattekst; taggnavn/profilidentiteter inngår ikke i rapporten.

| Modell | Tenant ID / slug | Profiler | Note NULL | Eksakt tom | Whitespace | Tekst | Egen korrekt assignment | Taggkoblinger | Distinkte koblede tags | Tags brukt av flere profiler | Publiserte aktørers taggkoblinger |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Organization | 1 / musikkontoretnord | 121 | 121 | 0 | 0 | 0 | 121 | 57 | 28 | 9 | 56 |
| Organization | 2 / musikkontoretmxst | 3 | 1 | 0 | 0 | 2 | 3 | 8 | 7 | 1 | 8 |
| Organization | 3 / musikkontoretbrak | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 8 |
| Organization | 6 / musikkontoretoks | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Organization | 7 / musikkontoretsorf | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Organization | 8 / musikkontoretstar | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Organization | 9 / musikkontorettempo | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Person | 1 / musikkontoretnord | 147 | 143 | 2 | 0 | 2 | 147 | 23 | 15 | 5 | 0 |
| Person | 2 / musikkontoretmxst | 4 | 1 | 1 | 0 | 2 | 4 | 1 | 1 | 0 | 0 |
| Person | 3 / musikkontoretbrak | 6 | 3 | 3 | 0 | 0 | 6 | 0 | 0 | 0 | 0 |
| Person | 6 / musikkontoretoks | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Person | 7 / musikkontoretsorf | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Person | 8 / musikkontoretstar | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Person | 9 / musikkontorettempo | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Alle rader hadde null NULL-domain, feil domain, manglende egen assignment, ekstra assignments og profiler med feil assignment. Ingen øvrige scope-/domain-/taggavvik ble observert, heller ikke i innkommende koblinger som først ble lest uten gyldighetsfilter. Dette er et datert inventar, ingen tillatelse til opprettelse eller framtidig garanti.

| Tenant ID | Legacytags | Ubrukte tags, begge modeller samlet |
| --- | ---: | ---: |
| 1 | 43 | 11 |
| 2 | 7 | 0 |
| 3 | 10 | 2 |
| 6 | 0 | 0 |
| 7 | 0 | 0 |
| 8 | 0 | 0 |
| 9 | 0 | 0 |

Totalt: 128 Organization (126 NULL / 2 tekst) og 157 Person (147 NULL / 6 tomme / 4 tekst). 285 strukturelt egnede egne assignments i dette snapshotet; null nye overlayrader. 60 legacytags, 97 koblinger (73 aktør / 24 person), 13 ubrukte tags. Dermed 47 tags i bruk totalt; samme tagg kan være brukt på begge modeller, så distinkte modelldelsummer skal ikke summeres som en union. 72 koblinger til publiserte aktører viser dagens eksponering, ikke godkjent framtidig shared/public-klassifisering.

## Bevaring og tekniske lesebevis

Alle eksisterende CRM-tabeller i runtime-modellregisteret, inklusive M2M, ble sammenlignet med deterministiske samlede radfingerprints før/etter schema/deploy/inventar. Innhold, PK-er og tidsstempler var uendret; ingen individuelle profilhashverdier publiseres. Tilleggene var to tomme overlaytabeller, schemaobjekter og migrasjonsregistrering.

Miljøfil var byteidentisk; hele containerens miljø/mounts, åtte eksisterende image-/importflagg og shadowgate var bevart. `TENANT_NOTE_OVERLAYS_ENABLED` var usatt i varig/containerkonfigurasjon og effektivt False. Ingen operatøraktivering av overlaygaten. Media/private (10 filer), artifacts (39), delivery (9) og static hadde uendrede samlede path-/innholdsfingerprints. Safety forble READY med samme ledger-ID og cursor 13; ingen ledger-/deny-write.

Lokal proxy-HTTP før/etter: frontend 200, session 200, PUBLIC API/HTML 200, anonym admin 302 og anonym tenant-API 403. Autorisert teknisk backendkontroll med eksisterende aktiv plattformbruker ga list 200 i alle 14 kombinasjoner og detail 200 der profiler fantes; legacy note var uendret og ingen overlayfelt eksponert. Admin-changelist og legacy notatskjema ble kontrollert for begge modeller; nye modeller var ikke registrert.

Autorisert kontroll brukte én read-only-transaksjon og requestfactory/force-authentication, uten login/sessionwrite. Dette er tekniske API-/adminbevis, ikke ny browser-/ekstern HTTPS-/innloggingstest eller brukertestrunde. Ingen UI-/authendring inngår.

## Anbefalinger og faktiske beslutningsbehov

**Anbefalt, ikke bestilt:** neste avgrensede bestilling bør konkretisere tapsfri, planbundet flytting til egen legacyassignment og samlet autoritetsovergang. Inventaret viser bare seks tekstnotater, men også seks eksplisitt tomme og 273 NULL-verdier; alle tre tilstander og fravær av overlayrad må bevares bevisst. Ikke kopier notatet til andre tenants ved senere multiassignment. Friskt inventar, eksisterende målrad som konflikt, stale-/auditkontroll og rollback må inngå før separat data-apply.

Prosjekteier må før senere notatflytting/aktivering godkjenne konkret flytteplan og opplegg for samlet omlegging av API/Editor/admin/import/direkte writes. Editor/import normaliserer i dag tomverdier; AI kan foreslå noteutdrag som description. Description og relasjonsstatus skal ikke automatisk flyttes eller privatklassifiseres.

For legacytags trengs eksplisitt mapping/policy per tagg og eventuelt kobling: shared editorial, private internal eller fortsatt uavklart. Alternativet er å holde legacytags utenfor senere shared/PUBLIC-cutover til mapping er godkjent; det er anbefalt overgang, ikke automatisk privatklassifisering. 13 ubrukte tags er ikke slettekandidater av den grunn. Ingen navn-/tenant-/publiseringsbasert klassifisering er utført.

Ingen ny produktbeslutning er nødvendig for denne ferdige, inaktive grunnmuren. Kandidatidentiteter og de to telefonavvikene fra 6A.3 er urørt. NULL-profiler eller manglende assignments ved en senere kjøring skal fortsatt bruke legacyflyt inntil separat løsning, uten catch-up her. Global rollefallback gir ingen framtidig overlayrettighet; membership, agreement, capabilities og audit gjenstår.

## Publisering og stoppunkt

Sanitert evidens og gjeldende status leveres i separat dokumentasjons-PR med faktisk separat review, ordinær merge og CI. GitHub viser faktisk publiseringsstatus; docs-only merge utløser ingen deploy eller ny dokumentasjonsrunde om egen merge. Deployet kode/image ovenfor skal skilles fra senere dokumentasjons-main.

Ingen rå note-/taggtekst, profilidentiteter/kontaktdata, credentials eller private detaljpaths publiseres. Avtalt teknisk sluttpunkt er oppfylt; evidensens review/publisering følger leveranseflyten. Ingen dataflytting, runtimeomlegging, fullført trinn 7 eller automatisk neste produktetappe.
