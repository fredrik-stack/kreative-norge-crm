# UI-6 førstepakke – profilhandlinger, sann status og lokal reset

**Dato:** 2026-10-24. **Status:** MERGET / FRONTEND DEPLOYET / TEKNISK STAGINGVERIFISERT.
**Visuell eieraksept:** ikke utført; kort kontroll nedenfor. Dette lukker bare den bestilte førstepakken, ikke hele UI-6-PROFIL eller øvrig UI-6.

## Mandat, kode og kontrollgrunnlag

[Spesifikasjonen §8](../features/UI_6_FELLES_SPEC.md#8-første-bestilte-kodepakke--skjemabundet-handlingstatus-og-korrekt-reset)
beskriver det uttrykkelige resetvalget og implementert scope. Profilrad/status,
nyprofilens standardregion/tags/dirty og bevart separat kontaktutkast er levert.
Ingen backend-/API-kontrakt, migrasjon, backfill, shadow, overlaygate, taggpolicy,
6B/6C, PUBLIC-, import- eller kartimplementering er endret.

| Leveranse | Versjon / separat review / nødvendige kontroller |
| --- | --- |
| [Kode-PR #89](https://github.com/fredrik-stack/kreative-norge-crm/pull/89) | Merge `31f3796e0c804dd9f1ea1d38e5262e26797c142f`. [Separat review](https://github.com/fredrik-stack/kreative-norge-crm/pull/89#issuecomment-6382141370) av base `3f0cde54927a039a83edbc86cdb3b9263b4847cd` / head `f0e435a042f691ac676a7631711619664be8f382`, uten blokkerende restfunn. [PR-CI](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/40079177787) og [main-CI](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/40079608334) SUCCESS, 6/6 |
| [Fokusretting #90](https://github.com/fredrik-stack/kreative-norge-crm/pull/90) | Endelig frontendkilde/merge `3ede68fd44b8bda42f99b2a7c8c8f7e37820669b`. [Separat review](https://github.com/fredrik-stack/kreative-norge-crm/pull/90#issuecomment-6382315927) av base `31f3796e0c804dd9f1ea1d38e5262e26797c142f` / head `a7d31b82d985b05133d5b5694fbb49cf06e5532a`, uten kritiske/viktige funn. [PR-CI](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/40080449703) og [main-CI](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/40080751371) SUCCESS, 6/6 før deploy |

52 lokale frontendtester, TypeScript og produksjonsbuild er grønne. Elleve nye
tester kjører faktisk hook/reset eller komponenteffekt/status: standardregion,
tags/feltfeil/state, ren baseline, eksisterende reset, ingen reset-write, sperre
under saving, feil/dirty-prioritet, profilbytte og bevart kontaktutkast/vern.
Fokus-/resize-testen bruker reell komponenteffekt og DOM-fokus med simulert geometri.

13 eksisterende Editor-Playwright-reiser er grønne. En lokal bred kjøring mot
UI6-basen hadde fire PUBLIC-feil fordi egne image-fixtures/flagg manglet; dette
er ikke fersk PUBLIC-verifikasjon. Påkrevde CI-kontroller, inklusive sin dedikerte
PUBLIC-fixture og frontend-e2e, er grønne. Ingen bred lokal backendregresjon eller
ny database-/migreringsleveranse er utført. Isolert lokal PostgreSQL 16/Django/Vite
med syntetiske data og aktiv Chromium ble brukt før kodeendring og etter retting.

## Faktiske funn og rettinger under kontroll

- Ren nyprofil med standardregion NO ble feilaktig dirty i baseline `3f0cde5`. Initiering/reset og dirty-baseline er nå konsistente; reset tømmer taggtekst/feltfeil/state uten API-write. Global feil beholdes.
- Ekte lokal browserkontroll avdekket at Lagre person tømte separat kontaktutkast ved profilreload. Det bevares nå for samme profil og har egen forklaring/navigasjonsvarsel; profilsubmit oppretter ikke kontakten.
- Første staging av `31f3796` viste at samme fokuserte felt kunne skjules etter resize, særlig ved 1366×768. #90 retter bare målt sticky-overlapp i samme hovedform. Den komplette stagingkontrollen er gjentatt på endelig `3ede68f` og er grønn.
- En operatørharness ventet først på `people` i personens POST-URL, mens API-et bruker `persons`. Eksakt syntetisk read-back viste opprettede profiler; de ble ryddet før kontrollert ny kjøring. Dette ble ikke behandlet som «ingenting lagret» eller blind create-retry. Avbrutte testfixtures ble også ryddet før siste kjøring.

## Frontend-only drift og versjonsidentitet

Fulgt [gjeldende stagingrunbook](../../deploy/staging/README.md) og
[stagingarkitekturen](../development/STAGING_AND_DEPLOYMENT.md). Begge frontend-
deployer hadde fersk grønn Borg-backup og full repository-/arkivverifikasjon før
build/recreate. Endelig deploy brukte arkiv `kreative-norge-staging-20261024T091246Z`;
backup fullført 09:12:56 UTC, full verifikasjon fullført 09:13:06 UTC.

Bare `web` ble bygd og kontrollert stoppet/fjernet/opprettet med `--no-deps` og
kommandoavgrenset Compose API 1.44. Ingen API-/database-/volumrecreate, migrasjon,
miljø-/flaggendring, Caddy-endring eller produksjonsdeploy. Servercheckout var ren
og satt til eksakt frontendkilde `3ede68f`; backend-/Compose-/deploy-runtimefiler
var uendret fra forrige serverbaseline `5c39ec5`.

- Aktivt webimage: `sha256:b6c0e8152c3d9f714551843f27d4aa31e24346d4d68e223813a8f256f62816c6`.
- Webcontainer: `8de45d3bd58edadc5e4fcb9c232a0ba5ce23879178f6c866fb0bce3420855af4`.
- API beholdt container `d3be6947c1def8679eb69597025498729e5055267397dc73006103172b65d6e3` og image `sha256:63000cdd2a3e4b25e8a49768466a6eade74407d39a52a6291654b3772c0d0ad5` fra backendkilde `5c39ec5`.
- Database beholdt container `46606f0b5b9794bb7d4698026113d3d018c03dafb06da9a9332a6b44aefa68eb`. Begge tjenester forble running; miljøfilens bytefingerprint er uendret og backup-timeren aktiv.

Ren lokal build, aktivt webimage og faktisk HTTPS-respons var byteidentiske:

| Fil | Byte | SHA-256 |
| --- | ---: | --- |
| `index.html` | 412 | `2cc5a99b6cfcb4d0f3a842d0195e1e185e9379930cadbfa4a2df4f69a1d687c8` |
| `assets/index-Dd2iIXOm.js` | 385192 | `3b2bd9c3cf50c3ce7da0e70fa73a786f24a7ac455b3efcafa64d564586efe0a0` |
| `assets/index-BnG0dypX.css` | 29064 | `eebbe328b4fcc2dad9ee90b73e959a60bc88138b960be24b9e181cbdc98f6830` |

Browserkontrollen brukte ekte `https://staging.northernsound.no` via en midlertidig,
lokalt avgrenset CONNECT-/SSH-transport til Caddy-origin. TLS/SNI, Host, HTTPS,
secure cookies, innlogging og CSRF var uendret; ingen API-mocks eller header-/
authomgåelse. Dette er teknisk originkontroll, ikke en ny kontroll av Cloudflare-
kanten. Innloggingsflaten og statiske filer returnerte 200.

## Kontrollert brukerreise og cleanup

Bare syntetiske, upubliserte profiler og en midlertidig tenantavgrenset testbruker
ble brukt. Ingen provider-/imagehandling, ekte kontaktendring eller dataflytting.

| Kontroll på endelig frontend | Resultat |
| --- | --- |
| Ny aktør og person: tomt → felt/tags → reset | Tags og profilfelt tømt, tenant/standardregion beholdt, ren profil/status; null reset-writes |
| Opprett → lagret → ny profilendring → forkast | Faktisk API-oppretting og read-back; korrekt status, ingen gammel lagringsbekreftelse/tid over ny endring; innlastede felt tilbake |
| Ren personprofil + separat kontaktutkast | Egen banner og faktisk navigasjonsdialog med «Ny kontakt (ikke lagret)». Profilreset og Lagre person bevarer kontaktutkastet; ingen kontakt-POST fra profilknappen |
| Egen kontaktoppretting og eksisterende blur | Egen knapp oppretter kanalen; endret ikke-tom verdi gir egen vellykket PATCH |
| Hovedsubmit og separate områder | Nøyaktig én hovedsubmit per profilform; bilde/preview/koblingsområder har egne handlinger |
| 1440×900, 1366×768, 1024×768, 390×844 | Begge former: fokusert siste felt og Tab gjennom siste kontroller forblir synlige/udekket; samme fokus overlever resize. Radgrensen er hovedformen |
| Faktisk Chromium-zoom 200 % | `chrome.tabs.setZoom(2)` i isolert midlertidig testprofil ga 1440×913 →720×456 CSS-piksler, devicePixelRatio 1→2. Begge former bruker normal flyt; Tab-fokus på siste felt og lagre-/forkastknapper forblir tilgjengelig |

De eksakte syntetiske profilene/kontaktkanalen ble slettet gjennom ordinært API,
med identitetskontroll og 404-read-back. Den eksakte midlertidige brukeren og
medlemskapet ble deretter fjernet. Ingen bred cleanup, slettevernomgåelse eller
sekvensreset. Normale PK-sekvenser/authartefakter kan være påvirket av testtrafikk;
ingenting tilbakerulles som om API-writes aldri skjedde.

Følgende aggregerte antall matchet før siste kjøring og etter cleanup. Dette er
avgrenset bevaringsbevis, ikke nytt inventar/shadow eller bevis for alle individuelle
felt ved samtidig ekstern aktivitet:

| Modell | Før / etter |
| --- | ---: |
| Organization / Person | 128 / 157, uendret |
| PersonContact / OrganizationPerson / Tag | 223 / 176 / 60, uendret |
| OrganizationTenantAssignment / PersonTenantAssignment | 128 / 157, uendret |
| OrganizationNoteOverlay / PersonNoteOverlay | 0 / 0, uendret |

## Eierkontroll, tilbakeføring og stopp

**Teknisk stagingverifikasjon er fullført. Visuell eieraksept er ikke mottatt.**
Prosjekteier kan på [staging](https://staging.northernsound.no/) kontrollere bare:

1. Åpne en tillatt aktør og person: forstås lagre-/forkasthandlingene og skillet mot egne kontakt-/bilde-/koblingshandlinger?
2. Bla gjennom langt skjema, bruk Tab og eventuelt 200 % zoom/smal visning: er felt, status og hovedhandlinger lesbare og tilgjengelige?
3. Ved tillatt syntetisk nyprofilkontroll: endre felt/tags og nullstill uten lagring. Bekreft ønsket lokalt utgangspunkt. Ingen reelle profiler trenger å lagres for denne eierkontrollen.

Bekreft aksept eller oppgi konkret avvik for aktør-/personskjemaet. Dette er ingen
ny formell brukertest eller ny design-/UX-runde.

Siste tidligere verifiserte webimage er bevart som
`kreative-norge-crm-web:ui6-pre-31f3796`, image
`sha256:25fbf4eab4a5402b96d25407aff30c6685dfcf843efb05bb2ffa10fa5b557383`.
Tilbakeføring er frontend-only til dette imaget etter runbook, uten API/DB/schema/
datareversering. Mellomversjonen med fokusavvik skal ikke brukes som verifisert
rollbackmål. Ingen rollback er utført; ingen videre produktetappe startes.

Denne nødvendige stagingevidensen publiseres med separat review/merge/CI. Dens
GitHub-PR er fasit for dokumentasjonsmerge; den utløser ingen ny deploy eller ny
dokumentasjonsrunde bare for å registrere sin egen merge.
