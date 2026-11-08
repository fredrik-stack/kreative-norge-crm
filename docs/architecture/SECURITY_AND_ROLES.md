# Security and Roles

## Streng tenantmodus – stagingverifisert med gaten av, 2026-11-08

PR [#107](https://github.com/fredrik-stack/kreative-norge-crm/pull/107), eksakt
merge/API-kode `276592cf0ad77960dd83187b3e002afcc2edd3ab`, er teknisk
stagingverifisert **2026-11-08 15:48:30 UTC / 16:48:30 CET**.
[Sanitert bevarings- og driftsevidens](../status/evidence/strict-tenant-staging-2026-11-08/checks.json).

Kodeleveransen har separat skrivebeskyttet review/re-review på base
`e10566c7ae20eb92b04eeba9413902ac1f5f53ca` → head
`4669359c33c35540517382197fed51164016a2d2`, uten gjenværende blokkere.
PUBLIC-testfunnet ble rettet til faktisk anonym actors-rute med publisert
syntetisk aktør/bilde/lenke og HTTP200. Lokal PostgreSQL16-regresjon bestod
750 tester; 18 målrettede grensetester og siste skjerpede PUBLIC-test bestod.
PR-CI [42495335446](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/42495335446)
og main-CI [42495870458](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/42495870458)
er SUCCESS6/6; endelig CI-head har752 backendtester og bestått Editor API-smoke.

### Runtime, gater og lesekontroll

Bare API er byttet fra `8cc160e` til `276592c`, med image
`sha256:9f524dec2b106a423e07ab0547d7d7ddbd2ffc48a6d0a71dc347c14ea7485d0e`.
172 relevante kildefiler matcher eksakt Git-arkiv. Eksisterende immutable base
bevarer interpreter/pakker; ingen dependencyinstallasjon eller oppgradering.
API starter direkte Gunicorn, uten migrate/seed/collectstatic. Skjema er fortsatt
0039 med tom migrasjonsplan; ingen schema- eller data-apply er utført.

Frontend/container er identisk med PR #105 / `8cc160e`, image
`sha256:19f408668d9a637083ff2bf3ef303ff3c36b89c48e900f32999690835e9ce169`.
Bundle-, image- og originbytes er bevart. Eksisterende nginxkonfigurasjon er
testet og reloadet etter API-bytte for å fornye upstream-DNS; web er ikke
rekreert. Databasecontainer/image/starttid/restarttall, mounts, miljø,
Docker/Compose, Caddy/prosess/konfigurasjon og media/static er uendret.

Alle fem gater er **effektivt og varig False**: `STRICT_TENANT_ACCESS_ENABLED`,
`ACCESS_MANAGEMENT_ENABLED`, `SHARING_ACCESS_ENABLED`, `CANONICAL_WRITER_ENABLED`
og `TENANT_NOTE_OVERLAYS_ENABLED`. Alle er unset i uendret miljø og bruker
verifisert default False; øvrige featureflagg er bevart. Streng modus er ikke
forsøkt aktivert, heller ikke midlertidig mot reelle data.

Eksisterende autorisert operatør er gjenbrukt i server-side lesekontroller,
innen REPEATABLE READ READ ONLY:14 modellister, seks detaljer, to Admin-lister,
to gamle notatfeltformer og autentisert session består. Disabled management-
context er tom, fem syntetiske negative prober avvises før skrivergrensen under
både SQL-write-avvisning og DB READ ONLY. Medlemskaps-Admin er fortsatt read-only
også for superuser. PUBLIC API/HTML/lenker og seks bilde-/fallbackvarianter er
bevart. Ingen ny login/session, credentialeksport eller generell browser-/UX-runde.

### Bevaring og driftsporter

Full før-/etterkontroll av **alle56 tabeller** viser samme gamle feltverdier,
relasjoner, PK-er, tidsstempler, publiseringsvalg og auth/session/roller.
Schema-/constraint-/trigger-/funksjonsmetadata er uendret; ingen kolonner eller
migrasjonsrader normaliseres bort. Canonical UUID-stamps på128 Organization og
157 Person er bevart. Medlemskap0→0; forvaltnings- og avtalehistorikk,
SharingAccessAudit, CanonicalWriteAudit, overlays og notatkopibatch har fortsatt0 rader.
Ingen individuelle profilhashverdier, UUID-stamps eller rå notater publiseres.

Ferske pre- og postcheckpoints bestod backup, full repository/archive-data verify
og isolert PostgreSQL16-restore. Kvitteringene er bundet til eksakt arkiv-ID og
dumpchecksum, med ny arkividentitetsread-back. Begge restores kontrollerte også
0039-strukturen og tom historikk. Installerte driftsscripts er uendret; private
kopier fjernet prune/compact og skjerpet arkiv-/schemakontroll. Ingen retention-
sletting eller live restore. Restorecontainere og tilhørende volumer er ryddet.

Safety er READY på samme ledger/repository og cursor13; ledgerbytes/historikk,
image-state og deny-state er uendret. Alle tre timere er active/enabled,
backup-/verifyservices er inactive. Separat review av private deploy-/read-back-
/evidensverktøy fant ingen gjenværende blokkere; nginx-reloadfunnet ble rettet
før runtimeendring. Kun godkjent TARGET-binding endret helperen etter review.

**Leveranseskille:** Den strenge grunnmuren er teknisk stagingverifisert med
gaten av. Gammel tilgang er fortsatt aktiv og legacydata autoritative. Ingen
reelle brukere/medlemmer/roller/fullmakter/avtaler/aksepter/tilbakekallinger,
notatkopi/-plan, canonical testwrites eller aktivering er utført. Neste avgrensede
steg krever separat eiergodkjent bruker-/tenant-/rollemapping og oppstartsmandat,
deretter kontrollert medlemskapsetablering og særskilt aktiveringsbeslutning.
Shared/writer/notat krever fortsatt egne porter. Dokumentasjonsmerge deployes ikke.


## Streng legacytenanttilgang – implementasjonskontrakt 2026-11-08

`STRICT_TENANT_ACCESS_ENABLED` er en egen **default False** innstilling, uavhengig
av forvaltnings-, shared-, writer- og notatgatene. Ugyldig konfigurert boolverdi
stopper oppstart; den skal ikke stille gjenåpne gammel rollefallback. Dette er
kodegrunnlag for en senere separat godkjent overgang, ikke aktivert tilgang.
Ingen migrasjon, medlemskap, rolle eller avtale endres av leveransen.

| Flate | Streng modus | Avslått modus |
| --- | --- | --- |
| Session og tenantvalg | Bare aktive, gyldige medlemskap for aktiv DB-bruker; ingen global rolle; Admin-lenke skjult | Eksisterende fallback og medlemsliste bevart |
| Tenant-API: Organization/Person, relasjoner, kontakter, tags | Eksakt aktivt medlemskap; alle fire roller leser, tre redigerer, superadmin/gruppeadmin sletter | Eksisterende policy bevart |
| Import/eksport og alle jobbhandlinger | Superadmin/gruppeadmin/redigerer, også ved GET; jobben må tilhøre URL-tenanten | Eksisterende kontrakt bevart |
| Bilder, kandidater, previews og utvalg | Tenant-API og samme autoriserte operasjon; takedown krever superadmin/gruppeadmin | Eksisterende bilde-/safetykontrakt bevart |
| Django Admin, inklusive User/Group og actions | Hele Admin-namespace er sperret, også for staff/superuser med medlemskap | Dagens Admin uendret, medlemskaps-Admin fortsatt read-only |
| Direkte bilde-/import-/OG-operasjoner | Ingen varig rett fra actor eller jobbens created_by; avvises uten allerede autorisert tenantforespørsel | Eksisterende operatørkall bevart |
| Legacy CLI for reparasjon/backfill/inventar/cleanup/publisering | Eksplisitt sperret; egen scoped operatørkontrakt må godkjennes før bruk i streng runtime | Eksisterende kommandoer bevart |
| PUBLIC og globale kategorier | Uendret PUBLIC; kategorier er global lesetaksonomi, ikke tenantdata | Uendret |
| PR #105 forvaltning/egenaksept og offline utpekning | Egen eksplisitt fullmakt og egen gate; ingen ny medlems-/akseptavhengighet for forvalter | Uendret |

`get_user_tenant_role()` leser aktivstatus fra databasen, ikke et gammelt user-
eller medlemskapsobjekt. Verken Django-grupper, staff eller superuser gir en
streng tenantrolle. Medlemskap i en annen tenant/domain gir ingen tilgang til
målet. Ren legacytenanttilgang krever **ikke** avtaleaksept, SharingDomain-
assignment eller shared capability. Fremtidig shared tilgang beholder alle
krav i ADR-011; et positivt legacytilgangssvar er aldri et shared grant.

### Transaksjonsgrense og direkte operasjoner

Middleware omslutter tenant-API-operasjonen i én transaksjon. Før tilgang gis,
låses aktuell domain (hvis bundet), aktiv bruker, eksakt tenant og aktivt
medlemskap med PostgreSQL FOR SHARE i samme rekkefølge som forvaltningen.
Tenantens domain kontrolleres igjen etter låsing. Låsene varer gjennom hele
operasjonen og hindrer samtidig deaktivering, rolleendring og sletting.
Forespørsel som venter på tilbakekalling, reautoriserer etter ventingen; allerede
godkjent operasjon fullføres før tilbakekallingen kan committe. Neste forespørsel
avvises. 2s lock-/30s statement-timeout; autorisasjonslåsefeil gir sanitert503,
og feilrespons ruller tilbake transaksjonen. Ingen blind automatisk retry.

Bildevalidatorer gjenbruker kun den kortlivede, låste actor/tenant/rolle-grensen.
Actorløse import-, rapport-, OG- og ingestfunksjoner krever samme grense i
streng modus. Jobbens created_by og tidligere positiv policyvurdering er ikke
rettighet. Direkte kall uten slik grense er sperret; lavnivå ORM/SQL, filsystem
og root/DB-administrasjon er privilegerte driftsflater, ikke autoriserte
brukerruter. De kan aldri presenteres som medlemskapssikrede API-er.

Sperrede CLI-er: audit_legacy_image_sources, audit_public_image_projection,
backfill_phone_identity, backfill_legacy_domain, compare_domain_reads,
copy_legacy_tenant_notes, cleanup_image_storage_orphans,
verify_image_storage_persistence, publish_existing_email_contacts,
repair_person_contacts og refresh_organization_previews. Relevante direkte
backfill-, shadow-, ingest-, release- og cleanupinnganger er også sperret eller
krever operasjonsgrensen. `check_public_actor_links` leser bare PUBLIC og
`appoint_access_manager` beholder sin særskilte mandat-/database-/auditkontrakt.
Eksterne safety-ledger-/backup-/restoreverktøy endres ikke eller kobles til
Django-roller; deres privilegerte driftskontrakt består.

### Senere kontrollert oppstart og rollback

1. Prosjekteier godkjenner separat eksakte eksisterende brukere, tenants og
   roller, samt sentrale forvaltere og oppstartsmandat. Ingen mapping utledes
   automatisk fra grupper/superuser; ingen avtaleaksept seedes.
2. Sperr ordinær legacytrafikk/Admin i et kontrollert driftsvindu **før** reelle
   medlemskapsendringer. Etabler fullmakter gjennom eksisterende sporbar,
   separat godkjent utpekning; bruk PR #105s scoped operasjoner med audit.
   Isolert forvaltningsprosess kan ha egen teknisk gate uten å åpne runtime.
3. Kontrollert etablering skjer uten global fallback som alternativ brukerinngang.
   Sett streng modus på alle API-workers før trafikk åpnes; verifiser eksakt
   bruker-/tenant-/rolle-scope og negative forsøk. Forvaltningsgate vurderes
   separat. Shared/writer/notat forblir av inntil egne porter er oppfylt.
4. Før reell overgang kan kode rulles tilbake med alle data/skjema bevart og
   flagget av. **Etter reell tilbakekalling/overgang er flagg av ikke en trygg
   rollback:** gamle grupper/superuser kan gjenopplive tilgang. Behold streng
   kontroll eller steng trafikken til kompatibel kode/deny-state er verifisert.
   Ingen schema-reverse, medlemskapsrekonstruksjon eller gammel snapshotrestore
   skal automatisk gjenåpne tilgang eller gjenopplive slettede private notater.
   Eksisterende safety-ledger, deny-state og historisk image-state består.

Stagingdelen er gjennomført med streng modus effektivt/varig av,0 medlemskap
og øvrige gater av; se datert stagingevidens øverst. Ingen aktivering eller reelle
tester av positive forvaltningsreiser inngikk. Oppstartsprosedyren ovenfor er
fortsatt planlagt og krever separat godkjenning.

### Verifikasjon

Syntetiske PostgreSQL16-tester dekker rolle-/handlingsmatrise, superuser/grupper,
inaktiv/stale bruker, ugyldig/inaktivt medlemskap, feil tenant/domain, neste
forespørsel etter tilbakekalling, alle private routerflater, Admin, direkte
operatør-/serviceforsøk, scopeopprydding, begge låserekkefølger, lock timeout,
uavhengige gater og uendret avslått modus/PUBLIC. Full backendregresjon dekker
import, images, revisjon, audit og safety; faktisk test-/CI-resultat følger PR.


## Stagingverifisering av første tilgangsreise – 2026-11-08

**Gjeldende stagingstatus:** PR #105 / eksakt kode
`8cc160e84162e94c11069e1ab52683496753e71a` er teknisk stagingverifisert med bare
`0039_access_management_journey`. Full read-back etter browserlesingen er datert
**2026-11-08 14:45:07 UTC / 15:45:07 CET**. Kodeleveransens tidligere «ingen staging»
nedenfor gjelder det opprinnelige mandatet; denne særskilt godkjente driftsetappen
overstyrer ikke legacyautoritet eller gir tillatelse til aktivering.
[Sanitert teknisk evidens](../status/evidence/access-journey-staging-2026-11-08/checks.json).

### Eksakt runtime og additivt skjema

- API før: `06e6594`, image
  `sha256:8cf42afc8e15e0377f307119bde69b2c05b5b9d824598c05ec130f19ca2c84b9`.
- API etter: godkjent `8cc160e`, image
  `sha256:b2900af8533a6f51b9699b4825bc4993a7b02a93dfe853a3de410dfb308ba703`.
  170 relevante kildefiler matcher eksakt Git-arkiv. Interpreter/pakker er bevart
  gjennom samme immutable base og kontrollert dependencyfingerprint.
- Frontend før matcher den tidligere godkjente `a49b9d1`-bundlen byte-for-byte.
  Den er reprodusert lokalt med samme eksisterende avhengigheter. Ny frontend er
  bygget fra rent `8cc160e`-arkiv uten npm install/oppgradering, og levert i image
  `sha256:19f408668d9a637083ff2bf3ef303ff3c36b89c48e900f32999690835e9ce169`.
  Index, JS og CSS matcher build, image og origin. Eksisterende nginxbase,
  pakkefingerprint, konfigurasjon og `50x.html` er bevart.
- Bare API/web er gjenskapt. PostgreSQL-containerens identitet, image, starttid,
  restarttall, konfigurasjon og mounts er bevart. Docker/Compose, Caddy/prosess/
  konfigurasjon, miljø, øvrige flagg og media/static er uendret. API starter direkte
  Gunicorn, uten automatisk migrate/collectstatic eller dependencyoppgradering.
- Én pending migrasjon ble verifisert og eksplisitt anvendt via MigrationExecutor:
  bare0039, READ COMMITTED, 2s lock-/30s statement-timeout. Tom sluttplan; ingen
  generell migrate, post_migrate/contenttype-/permissionseed, data-apply eller reverse.

0039 har tre nye tabeller: AccessManagementGrant, AccessManagementGrantRevocation
og MembershipManagementAudit, alle **0 rader**. 17 validerte constraints, fem
aktive triggere og kildeidentisk `crm_management_grant_guard` er kontrollert.
`SharingAgreement.legal_approval_reference` er NOT NULL varchar(200), uten
vedvarende DB-default; den nye kolonnen er kontrollert separat fra gamle data.
Det finnes ingen avtaler eller juridiske referanser. Isolert post-restore
bekrefter den nye strukturen, tom historikk og migrasjonsregistreringen.

### Avslått tilgang og faktiske lesebevis

Alle fire gater er effektivt og varig False:
`ACCESS_MANAGEMENT_ENABLED`, `SHARING_ACCESS_ENABLED`, `CANONICAL_WRITER_ENABLED`
og `TENANT_NOTE_OVERLAYS_ENABLED`. De er unset i uendret environmentfil/container
og bruker verifisert default False. Ingen annen gate er endret.

Eksisterende aktiv operatør fra tidligere autorisert backfill er gjenbrukt i
server-side APIRequestFactory/force_authenticate-/Admin-lesekontroller innen
REPEATABLE READ READ ONLY. 14 tenant-/modellister, seks detaljer, to gamle
Admin-lister, to legacy-notatfeltformer og autentisert sessionlesing bestod.
Ingen ny bruker, login, session eller last_login ble skrevet av kontrollene.

Ny autentisert context gir HTTP200, `enabled=false` og bare tomme lister.
Fem negative forvaltningsprober (én GET og fire POST i viewlaget) med syntetiske
verdier avvises med DISABLED før skrivergrensen. De kjøres under ekstra
SQL-write-avvisning og DB READ ONLY; ingen positiv forvaltningsreise er forsøkt.
De ni shared-capabilityvurderingene gir DISABLED. For eksisterende superuser
avvises add/change/delete på TenantMembership-Admin, mens changelist kan leses.
Nye historikkmodeller er ikke Admin-registrert; gammel Organization-/Person-
Admin og notatfelt består. Ingen canonical writer-funksjon er kalt.

**Faktisk HTTPS/browser:** En ny, senere lukket kontrollfane i eksisterende
Chrome-profil gjenbrukte browserens egen innlogging, uten ny login eller
credentialflytting. Aktører og Personer åpnet, og Tilgang og avtale var skjult i
menyen. Direkte `/access` viste «Tilgangsforvaltning er ikke aktivert».
`/api/auth/access-management/` viste HTTP200 med enabled=false og tomme lister.
Medlemskaps-Admin viste «Select tenant membership to view», uten opprettingsvalg.
Bare GET/navigasjon og synlig UI ble brukt; ingen profilskjema eller positiv
forvaltningshandling ble utført. Brukerens eksisterende faner/utkast er bevart.
Dette er avgrenset teknisk lesebevis, ikke ny generell UX-/visuell eieraksept.

Et forsøk på å eksportere en eksisterende server-session til privat lokal fil
ble avvist av automatisk godkjenningsreview. Eksporten ble ikke utført eller
omgått. Den ubrukte root-only kontrollkopien ble fjernet uten å endre
sessionsdatabasen. Den faktiske browserkontrollen brukte i stedet browserens
allerede eksisterende innlogging. Ingen credential er publisert eller flyttet.

### Bevaring, backup og driftsstatus

Alle gamle feltverdier, relasjoner, PK-er, tidsstempler, publiseringsvalg og
rader i **53 tidligere tabeller** matcher før-/etterkontrollene. Bare ny juridisk
kolonne normaliseres bort i sammenligningen, og bare én0039-migrasjonsrad tillates
som tillegg. Gamle constraints/triggere/funksjoner/kolonnedefinisjoner er bevart.
Canonical-stamps inngår nå fullt i gammel data og er også separat sammenlignet:
128 Organization og157 Person har samme ikke-null UUID-metadata som før0039.
Ingen individuelle profilhashverdier, UUID-verdier eller rå notater publiseres.

Medlemskap er0→0; avtale-/aksept-/revokasjons-/tilgangshistorikk, canonical audit,
begge overlays og notatkopibatch er fortsatt tomme. Auth/session/roller, notater,
tags, import, imagehistorikk og historiske identiteter er bevart. PUBLIC API,
HTML/lenkevalg og seks asset/fallback-bildevarianter er uendret. Source for gammel
rolleoppløsning, views og legacy-/PUBLIC-serializers matcher tidligere kode.

Ferske pre- og postcheckpoints bestod backup, full repository/archive-data verify
og isolert PostgreSQL16-restore. Begge kvitteringer er bundet til forventet arkiv,
eksakt arkiv-ID og dumpchecksum, med ny identitetsread-back. Installerte scripts
er uendret; private kopier fjernet prune/compact og skjerpet arkiv-/schemakontroll
og cleanup. Ingen prune/compact er kjørt. Egne restorecontainere/volumer er borte,
og eksisterende volumsett er bevart. Backup/verify-services er inactive, og
backup-/verify-/safety-health-timere er active/enabled. Safety er READY på samme
ledger/repository/cursor13; ledgerbytes, deny-state og historikk er uendret.

Private buildkontroller ble før schema/runtime rettet for kjent nginx50x.html,
macOS-arkivmetadata og kort/full Docker-ID, inklusive pre-schema recovery.
Kontrollene stoppet uten database-/runtimeendring. Den rene byggefortsettelsen
revaliderte API/kilde/deps/data og bygget bare det ennå ubygde webimaget.
Siste helperversjoner fikk separat skrivebeskyttet review uten blokkere før
stagingmutasjon. Ingen schema-/dataretry eller recovery var nødvendig.
Ved feil etter mulig0039-commit skal gammel skrivbar medlemskaps-Admin aldri
åpnes automatisk; behold additivt skjema og stopp/fens tilgang ved ukjent utfall.

### Sluttpunkt og gjenværende aktivering

Ingen reelle forvaltningsfullmakter, brukere, medlemskap, avtaler, aksepter eller
tilbakekallinger er opprettet/endret. Ingen appoint_access_manager --apply,
notatkopikommando/-plan, canonical testwrites, shared tilgang eller produksjon.
Kilde-PR/main-CI var grønne6/6 før drift; denne etappen gjenbrukte eksisterende
lokale testbevis og etablerte tekniske kontroller. Ingen ny generell testfase.
Dokumentasjonsleveransen følger separat review/PR/ordinær merge/CI og deployes ikke.

Teknisk stagingverifisert kode er fortsatt inaktiv. Legacyfallback og samlet
håndtering av gammel tilgang, reell oppstartsfullmakt, juridisk godkjenning/
aksept, restore-reconciliation, writer-/notat-/assignmentovergang og øvrige
ADR-011-porter gjenstår før faktisk deling. Ingen ny produktetappe er startet.


## Forvaltningsfullmakter og første tilgangsreise – 2026-11-08

**Mandat:** Eiergodkjent presisering i ADR-011 §9a etter main `6843192`.
Lokal implementering, syntetiske PostgreSQL 16-tester, dokumentasjon, separat
review, PR/ordinær merge og main-CI. Ingen staging, reelle medlemmer/avtaler/
aksepter, datakopiering eller aktivering. Dette avløser den tidligere uavklarte
forvaltningsmyndigheten i daterte trinn-8-avsnitt nedenfor; legacyautoritet består.

### Smal forvaltningsgrense

`crm/services/access_management.py` og `crm/access_management_views.py` har to
uavhengige fullmakter i immutable `AccessManagementGrant`. Hver sentral
utpekning binder bruker, handling, eksakt domain, eventuell eksakt tenant,
operatør-ID, mandat, request-UUID og tidspunkt. `AccessManagementGrantRevocation`
er en separat immutable tilbakekalling. Ingen eksisterende rolle, Django-gruppe,
staff eller superuser utsteder eller erstatter disse fullmaktene. En forvalter
kan ikke endre eget medlemskap, egen rolle, utstede nye fullmakter eller delegere
videre. Ingen runtime-API eller Admin registrerer/utsteder grants.

Medlemskapsfullmakt gir liste/endre/opprette medlemskap for eksisterende aktive
kontoer i angitt tenant, inklusive rolle og aktivstatus. En inaktiv målbruker kan
fortsatt få sitt eksisterende medlemskap avsluttet med uendret rolle, men får
ikke nytt medlemskap, ny rolle eller reaktivering. Aktiv forvalter kreves alltid.
Målbrukerens eksakte brukernavn revalideres fra låst rad etter venting; endret
binding gir STALE_TARGET uten write/audit. Ingen nye brukerkontoer,
brukerregistersøk, tenants eller domainbindinger opprettes. Nytt medlemskap krever
`expected_updated_at=null`; eksisterende medlemskap krever eksakt lest
`updated_at`. Stale endringer avvises; uendret replay er no-op bare ved samme
snapshot. Hver faktisk endring og `MembershipManagementAudit` er atomiske.
Auditen lagrer bare actor-/target-/grant-/tenant-/domain-ID, før/etter rolle og
aktivstatus og tidspunkt. Ingen notater, kontakter eller brukerprofiler kopieres.
Django Admins gamle medlemskapsflate er nå skrivebeskyttet, også for superuser;
modellene for nye fullmakter og historikk er ikke Admin-registrert.

Publisering krever egen domainfullmakt, eksplisitt godkjenningsbekreftelse og en
ikke-tom `legal_approval_reference` til faktisk juridisk godkjenning. Referansen
bevares på immutable SharingAgreement; den gir ingen teknisk bruker juridisk
myndighet. Eksakt tekst beholdes uten trimming. Eksisterende monotont stigende
versjon/virkningstid og DB-generert SharingAccessAudit gjenbrukes atomisk.
Serveren kan ikke avgjøre juridisk godkjenningens gyldighet; operatør må kontrollere
beviset. Ingen reell tekst seedes eller publiseres av denne leveransen.

Alle writes har egen outer/durable READ COMMITTED-transaksjon, 2s låse- og
30s statement-timeout. Domain låses før brukere (stigende PK ved flere), så
fullmakt og nødvendig medlemskap. Brukeraktivitet, scope og tilbakekalling
revalueres etter låseventing. Forvaltningsoperasjoner og offline tilbakekalling
serialiseres på samme domain. DB-feil/tapt svar gir fast
`OUTCOME_REQUIRES_READBACK`, uten rå SQL-/feltverdier eller automatisk retry.
Dette beviser ikke rollback ved ukjent commitutfall. Hent ferskt medlemskap,
avtale-/akseptstatus eller oppstartsrecord før nytt forsøk.

### Egen avtale og liten Editor-flate

`/access` gjenbruker Editorens paneler, skjemafelt og knapper. Navigasjonslenken
vises bare når ny forvaltning er aktivert. Brukeren ser gjeldende eksakte tekst
og versjon for egne aktive, gyldige medlemskap, merker selv en tom checkbox og
utfører eksplisitt aksept. Actor utledes bare fra session; request kan ikke velge
annen bruker. Aksept krever ikke allerede akseptert avtale eller shared gate.
Eksisterende DB-trigger avviser en versjon som ble erstattet før INSERT.

Aksept gjelder bruker/domain. Et annet aktivt medlemskap i samme domain kan
bruke samme aksept; det opprettes ingen andre medlemskap av aksept. Ny versjon
krever ny aksept fra effective_at uten grace. Tidligere aksepter vises separat;
egen tilbakekalling er mulig etter medlemskapsopphør, uten å slette historikk.
API-et krever aktiv autentisert bruker; DB-grunnmuren beholder også støtte for
å bevare tilbakekalling etter inaktivering gjennom privilegert drift. Ingen
administrativ tilbakekalling på andres vegne er innført.

Forvalter ser bare tildelte tenants/domains, med enkel medlemskapsliste/skjema
og publiseringsskjema. En gruppeadmin kan senere utpekes eksplisitt gjennom
samme scopede lagring; tenantrollen alene gir ingen slik rett nå.

API-er under `/api/auth/access-management/` (session-auth og CSRF):

- GET roten: egen status, gyldige medlemskap, nåværende tekst, egne aksepter og
  egne fullmaktsscope. Avtalepublisister får i tillegg eksakt publisert tekst og
  metadata i eget tildelt domain for kontroll/read-back. Ingen CRM-profiler eller andre brukeres aksepter.
- GET/POST `domains/<domain>/tenants/<tenant>/memberships/`: scoped medlemskap.
- POST `domains/<domain>/agreements/`: publisering med juridisk referanse.
- POST `domains/<domain>/acceptances/`: eksplisitt egenaksept av eksakt versjon.
- POST `acceptances/<acceptance>/revoke/`: bare egen tilbakekalling, idempotent.

Ingen av disse rutene bruker legacyrollefallback eller gir shared capabilities.
`assess_access()` er uendret og leser de samme faktiske medlems-/akseptradene.
Positive policytester aktiverer shared bare isolert med syntetiske fixtures;
ingen runtimegate endres. Endepunktene returnerer ikke et gjenbrukbart grant.

### Kontrollert oppstart og separat aktivering

`ACCESS_MANAGEMENT_ENABLED=False` er ny fail-closed standard; context gir bare
`enabled=false` og tomme lister når av. Andre operasjoner stopper før dataendring.
Writer/shared/notatgater forblir av. Før senere reell oppstart kreves eget mandat
med operatør, annen navngitt mottaker, eksakt handling og tenant/domain, samt
kontroll av databaseidentitet og juridisk referanse der relevant.

`appoint_access_manager` er bare privilegert offline drift. Det utpeker ikke en
administrator fordi vedkommende er Django-superuser. Operatørens eksisterende
aktive ID er sporbar identitet; kontrollert OS-/DB-tilgang og separat mandat er
det operative autorisasjonsgrunnlaget. Selvutpekning avvises. Ingen slik kommando
er kjørt mot reelle data i denne leveransen.

1. Innhent separat, konkret godkjenning og verifiser miljø/database/backup etter
   etablerte driftsporter. Skriv bare en mandat-ID, aldri hemmeligheter, i referansen.
2. Uten `--apply` skriver kommandoen bare PLAN_ONLY; dette er **ikke** en verifisert
   DB-plan, og ingen forbindelse eller brukersjekk utføres.
3. Ved senere godkjent kjøring: begrens teknisk aktivering til kontrollert prosess,
   angi `--apply --operator-id --user-id --domain-id --action --request-id
   --mandate-reference --expected-database` og `--tenant-id` bare for medlemskap.
   Databasenavnet må matche verifisert forbindelse; navnet alene beviser ikke miljø.
4. Kontroller record-ID og alle scope-/mandatfelter i privat read-back. Samme
   request-UUID med identiske parametere gjenbruker historisk record, mens endret
   innhold avvises. Replay gjenoppliver aldri en tilbakekalt fullmakt.
5. Opphør av fullmakt bruker samme kommando med separat mandat og
   `--revoke-grant-id`, operatør, databasereferanse og `--apply`. Ingen rolle kan
   selv delegere eller utstede fullmakter i runtime.

Medlemskapsopprettelse/rolleendring kan påvirke **dagens legacytilgang**.
`is_active=False` stanser bare ny policy; gammel fallback og medlemslesing ignorerer
fortsatt dette feltet. Før reell aktivering må gamle API-/Admin-/importinnganger
samordnes eller avvises, og opphør må ha en faktisk tilgangsstengingskontrakt.
Aksept oppretter ikke nye CRM-lesere, canonical writes, overlays eller PUBLIC-endring.

### Skjema, rollback og bevisgrenser

Additiv0039 legger til tre tomme tabeller, immutable PostgreSQL-vern og juridisk
referanse med tom default på eksisterende avtaler; ingen seed eller gammel
medlemskaps-/rolle-/dataendring. Eksisterende avtaler endres ikke semantisk.
Reverse stopper ved enhver ny historikk eller juridisk referanse. Etter første
semantiske endring beholdes schema/historikk og det rettes framover. API-rollback
må ikke gjenåpne den gamle skrivbare medlemskaps-Adminen eller miste ny deny-state.

Restore kan ellers gjenopplive medlemskap, fullmakter eller aksepter. Hold ny
forvaltning og shared/writer/notat av etter restore til nyere tilbakekallinger og
tilgangstap er reconciliert fra autoritativt bevis; manglende bevis gir fortsatt
stengt tilgang. Ingen ny ekstern ledger er etablert. Eksisterende image-safety,
deny-state, historiske identiteter og backup-/restoreprosedyrer er uendret.
DB-/ORM-tilgang med driftsprivilegier er ingen brukerautorisasjon; WORM-vern
lover ikke motstand mot privilegert DDL/TRUNCATE eller deaktivering av triggere.


### Lokal verifikasjon

Isolert PostgreSQL 16 og bare syntetiske brukere/medlemskap/avtaler. Full backend
regresjonssuite: 730 grønne før siste read-back-/schemaannotering; senere endringer
er revalidert med 60 grønne målrettede PostgreSQL-tester (23 nye + 37 eksisterende),
inklusive reviewretting for opphør av inaktiv konto og fersk målidentitet. Frontend: 70 tester og TypeScript/produksjonsbygg
grønne. Fire Playwright-reiser bruker syntetiske API-svar, ikke staging eller
ekte avtaler. Desktop-/mobil-/forvalter-/publisistbilder er visuelt kontrollert:
[egenaksept](../status/evidence/access-journey-2026-11-08/member.png),
[mobil](../status/evidence/access-journey-2026-11-08/mobile.png),
[medlemskap](../status/evidence/access-journey-2026-11-08/manager.png),
[publisering](../status/evidence/access-journey-2026-11-08/publisher.png).

Negative tester omfatter selvendring/selvutpekning, global rolle-/superuserbypass,
feil tenant/domain/fullmakt, tilbakekalt fullmakt, inaktiv bruker/medlemskap,
manglende og erstattet aksept, CSRF og forsøk på å velge annen actor. PostgreSQL
samtidighetsprøver dekker reautorisering etter tilbakekalling, stale samtidige
medlemswrites og låsetimeout; auditfeil ruller kildeendring tilbake. Additiv
migrasjon bevarer gammel medlemsstate, seed er tom og reverse stanser ved ny
historikk/juridisk bevis. Separate 64 image-safety-tester er grønne. Ingen rå
notater, reelle persondata eller individuelle profilhashverdier er publisert.

## Stagingverifisering av trinn 9 – 2026-11-08

**STAGING VERIFIED / WRITER INACTIVE** innen uttrykkelig mandat: eksakt PR #103-
API og kun0038, etablerte backup-/restoreporter, uendrede gamle felt og separat
UUID-metadata. Ingen canonical-/legacy-testwrites mot stagingprofiler,
medlemskap/aksepter, notatkopiering/-plan, aktivering eller produksjon. Ingen ny
generell test-/analyse-/UX-etappe. Dokumentasjon leveres med separat
review/PR/ordinær merge/CI og utløser ingen ny deploy.

[Sanitert maskinevidens](../status/evidence/phase6a9-writer-staging-2026-11-08/checks.json)
er kontrollert **2026-11-08 kl.11:26:23 CET** / `10:26:23Z`. Private før-/etter-
radfingeravtrykk, UUID-vektorer, container-/miljømetadata, arkiv-ID-er,
dumpchecksums og driftslogger beholdes operatørbeskyttet utenfor Git. Ingen rå
notater/kontaktdata, individuelle profilhashverdier eller UUID-stamps publiseres.

### Eksakt kode, migrasjon og metadata

- Før: rent stagingrepo/API `d410e8e2e5e4a671edbd755f527d7eb52fe8103a`, image
  `sha256:4a0356cc23af52a96433fa3b7db44c6a3d85d7a7263f12b5a2c962677ba10630`,
  0037 anvendt og52 eksisterende tabeller. Ingen0038-kolonner/audittabell.
  Databaseidentiteten ble kontrollert eksakt og er uendret.
- Etter: rent stagingrepo/API **`06e65947b90483ec242e1cdd657a7835debe60ec`**,
  image **`sha256:8cf42afc8e15e0377f307119bde69b2c05b5b9d824598c05ec130f19ca2c84b9`**.
  Alle165 relevante kildefiler matcher godkjent Git. Image bygger på den gamle
  immutable API-basen med eksakt Git-kilde lagt over; dependencyfingeravtrykk,
  Dockerfile, requirements og Composekontrakt er uendret. Ingen pakke-/infraupgrade.
- Eksakt én pending migrasjon ble verifisert før apply. Bare
  `0038_canonical_writer_foundation` er anvendt, eksplisitt med MigrationExecutor,
  prosessavgrenset READ COMMITTED, lock_timeout2s og statement_timeout30s.
  Ingen generell migrate/post_migrate, seed eller contenttype-/permissionrader.
  Gammel migrasjonshistorikk er bevart med bare én ny0038-rad; sluttplanen er tom.
  Ingen schema-retry, schema-reverse eller API-rollback var nødvendig.
- `CanonicalWriteAudit` er tom. Alle13 constraints er validerte; de tre
  forventede triggerne er enabled. Funksjonskroppen `crm_canonical_core_stamp`
  matcher0038-kilden. Alle tidligere constraints/triggere/funksjoner består.
- Nye profilkolonner har typen uuid og NOT NULL.128 Organization- og157
  Person-rader har gyldige ikke-NULL-stamps. Stamps er separat tillatt metadata,
  ikke nye profilverdier, canonical authority eller handlingsaudit. De ble
  fingeravtrykksfestet ved første read-back etter0038 og er identiske gjennom
  API-start, post-checkpoint og siste fulle bevaringskontroll.

### Bevaring og uendrede legacyreiser

Alle52 tidligere tabeller sammenlignes med private deterministiske
radfingeravtrykk. **Bare canonical_write_stamp utelates på Organization/Person**;
alle gamle felter, NULL/tom/tekst, PK-er, tidsstempler, relasjoner/M2M, publication,
notater/tags, importdata, auth/session/grupper/roller og bildehistorikk er fortsatt
med i sammenligningen. Eksisterende medlemskapsfelt, inklusive is_active,
sammenlignes uendret; medlemskapstall er0→0 og ingen er opprettet/deaktivert.

Frontend/web- og databasecontainer har samme identitet/image/start/restart,
Config/HostConfig og mounts. API-miljø, restartpolicy og mounts, miljøfil,
private originals, renditions, delivery og static er bevart. Ingen import-/
eksportfiler fantes i API-laget før eller etter graceful stopp. Bare API ble
rekreert, direkte med Gunicorn uten migrate/collectstatic. Nginx fikk nødvendig
configtest/reload uten web-recreate. Ingen ny frontend-/database-/Composeleveranse.

Eksisterende aktiv staff/plattformoperatør fra tidligere backfillbevis ble
brukt til etablerte **read-only** backendkontroller:14 tenant-/modell-lister,
6 detaljer,2 Adminlister,2 legacy-notatskjemaer og autentisert session.
RequestFactory/force_authenticate gav ingen ny login/session/last_login eller
rettighet. Ny audit er ikke Adminregistrert, og stamps er skjult i Admin/API/
PUBLIC-serializers. PUBLIC-katalog, HTML og HTTP-grenser svarte som forventet;
hele PUBLIC-API-responsen og seks representative asset-/fallback-varianter har
uendrede bytes. Dette er teknisk lesebevis, ingen ny browser-/UX-/eieraksept.

**Legacywrite-kompatibilitetens bevisgrense:** Det er ikke utført write-smoke mot
reelle stagingprofiler eller kalt noen canonical writerfunksjon, heller ikke
som et gate-off-forsøk. Grunnlaget er PR #103s allerede grønne syntetiske
PostgreSQL16.14-tester og CI, kombinert med eksakt kilde-/trigger-readback og
staginglesing. Lokal fullregresjon710 bestod før siste avgrensede feilkontrakt-
retting;23 relevante tester etter rettingen og64 separate safety-tester er
grønne. PR-CI42469037763/main-CI42469412699 var SUCCESS6/6 på godkjent kode.
Ingen ny generell testetappe er gjennomført for stagingmandatet.

Gamle permissions/views/urls/serializers har ingen kildedelta. Den tilsiktede
DB-endringen er bare vedlikehold av metadata når legacy endrer writerens smale
core-felt eller aktørens publication; den oppretter ingen audit og endrer ikke
gamle feltverdier/normaliseringer. Legacy API/Editor/Admin/import er fortsatt
autoritative. Nye triggeres konkrete write-/ABA-/rollbacksemantikk er testet
lokalt, ikke utøvd mot stagingdata. Samlet writer-/rolle-/autoritetsovergang
før aktivering gjenstår etter kontrakten nedenfor.

### Gates, backup, restore og driftsstatus

`CANONICAL_WRITER_ENABLED`, `SHARING_ACCESS_ENABLED` og
`TENANT_NOTE_OVERLAYS_ENABLED` er effektive/varige False. Alle tre er unset i
uendret `.env.staging` og containerkonfigurasjon og bruker False-default.
Ni shared-capabilityvurderinger returnerer DISABLED. Ny canonical audit,
SharingAgreement/Acceptance/Revocation/AccessAudit, begge notatoverlays og
kopibatchregisteret har0 rader. Ingen avtale, aksept, notatkopi/-plan eller
aktivering er opprettet/kjørt.

Graceful API-stopp gav kontrollert skrivefrys. Fersk pre- og post-backup,
full Borg repository-/archive-data-verifikasjon og arkivbundet isolert
PostgreSQL16-restore bestod. Begge receipts er bundet til eksakt arkiv-ID og
dumpchecksum og arkividentitetene er lest tilbake etterpå. Post-restore
bekrefter0038, tom audit/avtalehistorikk/overlays/batch,13 constraints/tre triggere
og begge profilkolonner som uuid/NOT NULL med null manglende stamps.
Dette inkluderer ingen testwrites eller gjenoppretting til live DB.

Installerte backupskript er byteuendret. Private operatørkopier brukte etablerte
arkivbindinger og ingen prune/compact. Egne restorecontainere inklusive anonyme
volumer er fjernet, og volumsettet er bevart. Backup-, verify- og safety-health-
timere er active/enabled; backup-/verify-services er inactive i sluttkontrollen.
Safety forblir READY med samme ledger-/repositoryidentitet og
event/read/anchor-cursor13; ledgerfil og historikk er byteuendret. Ingen deny-
write eller reassosiering av historisk image-state.

De tre muterende/lesende operatørhelperne fikk separat skrivebeskyttet statisk
review før driftsmutasjon, bundet til hashene i JSON. En variabelkollisjon i
stamp-leseskriptet ble rettet før schema/runtime ble endret; DB-identiteten
sammenlignes også eksplisitt mot førbeviset. Ingen blokkere stod igjen på
endelige hashes. Sluttmålingen viser faktisk stagingbevis fra gjennomfører;
revieweren kjørte ikke SSH/DB eller leste private metadata.

Ved et eventuelt API-rollback skulle gammel API gjenopprettes med0038 og alle
data beholdt; ingen destruktiv schema-reverse eller live restore var del av
sekvensen. Ingen slik rollback ble nødvendig. Fullført stagingverifisering er
ikke shared-aktivering, ferdigmelding av hele trinn7/8/9/6A eller tillatelse til
neste produktetappe, reell notatkopiering eller produksjon.


## ADR-011 trinn 9 – inaktiv canonical writer, 2026-11-08

**Mandat:** Én liten, additiv implementeringsleveranse etter `8283431`, med lokal
isolert PostgreSQL16 og syntetiske data, dokumentasjon, commit/push/draft PR,
separat review/re-review, ordinær merge ved grønn CI og kontroll av main-CI.
Ingen stagingdeploy/schema-apply, reelle medlemskap/avtaler/aksepter,
notatkopiering, shared-aktivering eller produksjon. Godkjent ADR-011 §5/9 og
migreringstrinn9 er arkitekturgrunnlaget; ingen ny generell rettighetsplattform.

### Begrenset feltkontrakt og innganger

`crm/services/canonical_writer.py` har to interne innganger: `get_revision()` og
`write_core(expected_revision, values, ...)`. Bare eksisterende canonical core:

| Objekt | Tillatt patch | Utenfor kontrakten |
| --- | --- | --- |
| Organization | `name`, `description` | Alle andre felt, inklusive kontakt, org.nr., bilde, sted og publication |
| Person | `full_name` | Alle andre felt, inklusive tittel/kontakt/sted og relasjoner |

Modellenes gjeldende type, lengde, blank/null og validering gjenbrukes uten
trimming eller normalisering. Description bevarer NULL/tom streng/whitespace/
tekst. Navn er strenger med modellens påkrevde verdi og maks255. Patchen må ha
minst én faktisk endring; ukjente felt, ugyldige verdier og no-op avvises før
oppdatering/audit. Ingen generell serializer-/feltmotor eller importsammenfletting.
Organisasjonsnummer/telefon normaliseres ikke som sideeffekt. Importkonflikter
og typed review inngår ikke her; dagens importruter består.

Handling må eksplisitt være `EDIT_SHARED_CORE` eller `EDIT_PUBLISHED_CORE`.
En publisert Organization avvises med vanlig core-capability, også etter venting
på en samtidig publiseringsendring. PUBLISH-capability gir ikke core-write.
Person har ingen global published-state og kan ikke bruke published-core-action.
Ingen publiseringsflagg, notater, tags, kontakter, relasjoner, steder, bilder
eller assignments skrives. Eksisterende PUBLIC-lesing er autoritativ; en senere
UI-/writeraktivering må vise den delte/offentlige effekten av core-endringer.

Ingen aktive ruter importerer eller kaller tjenesten. Ny auditmodell er ikke
Adminregistrert. Ny stamp er skjult i Admin og eksisterende API/PUBLIC-serializers.
Det finnes ingen snapshot-/write-API eller ny Editor-/Import-UX.

### Atomisk autorisasjon og samtidighet

Begge fail-closed gates må være True: `CANONICAL_WRITER_ENABLED` og
`SHARING_ACCESS_ENABLED`; begge default False. Gaten sjekkes ved inngang og
før oppdatering. Caller må binde user-ID og aktiv tenant til autentisert request;
caller-supplied AccessDecision/grant aksepteres aldri. Staging har fortsatt0
medlemskap; tjenesten lager ingen brukere, roller, medlemskap eller aksepter.

Tjenesten krever PostgreSQL og egen ytterste durable transaksjon, med autocommit
på ved kall. Nestet/manuelt åpen callertransaksjon avvises. Inne i grensen settes
READ COMMITTED eksplisitt, lock_timeout2s og statement_timeout30s. Ingen check
før lås anses som autorisasjonsbevis.

Låserekkefølge: SharingDomain FOR UPDATE → bruker FOR UPDATE → tenant FOR SHARE →
TenantMembership FOR UPDATE → profil FOR UPDATE → eksakt assignment FOR UPDATE.
Domain/bruker følger avtale-/aksept-/revokasjonstriggernes orden. Tenant SHARE er
kompatibel med legacyprofilvernets SHARE. Dette låser også relevante endringer
av brukerstatus, medlemsrolle/-aktivitet, scope og publisering. Tilgang vurderes
**på nytt etter venting** med trinn8-policyen: aktiv bruker, eksplisitt aktivt
medlemskap, eksakt domain, gjeldende ikke-tilbakekalt aksept, relevant capability
og egen eksakt objektassignment. Ingen global gruppe- eller superuserfallback.

Revokasjon/ny avtaleversjon følger samme domainlås; medlems-/brukerendringer
konflikter med sine radlåser. En allerede committet endring leses ferskt etter
venting; en senere konkurrerende endring må vente til writerens commit. En
framtidig avtales effective_at kan passere uten radendring: derfor kontrollerer
selve UPDATE-statementet også gjeldende agreement ved sitt statement_timestamp.
Ingen skjult grace fra tidligere policyvurdering. Audit får samme tidspunkt som
oppdateringen. PostgreSQL-låsene gir serialisert rekkefølge, ikke tilbakevirkende
annullering av en allerede autorisert og committet handling.

Database-/InterfaceError, inklusive lock timeout/deadlock/connectionfeil,
sanitiseres til fast feilkode uten rå radverdier/serverdetaljer eller blind retry. Ved tapt
COMMIT-svar kan utfallet være ukjent; koden returnerer
`WRITE_OUTCOME_REQUIRES_READBACK`, ikke et løfte om rollback eller idempotent
replay. Caller må hente fersk tilstand/audit og avklare utfallet før nytt forsøk.
Ingen generell batch-/idempotensplattform er innført.

### Expected revision og eksplisitt legacygrense

`Revision` binder entity_type, PK og SharingDomain til to verdier:

- **Canonical counter:** maks immutable audit-revisjon for objektet, startet på0.
  Økes med nøyaktig1 ved hver vellykket servicewrite. Telleren er aldri en
  komplett legacy-/profilrevisjon eller en autorisasjon.
- **UUID-stamp:** DB-generert endringsmarkør for akkurat dette feltsettet og
  Organization.is_published. Gamle ORM/save/update/bulk og direkte SQL som endrer
  disse verdiene fornyer stamp, også ved endring→tilbake til samme verdi (ABA).
  En gammel ORM-instans kan ikke sette stamp tilbake; andre feltoppdateringer
  beholder gjeldende DB-stamp. Stamp er metadata, ikke audithistorikk.

Eksakt kombinasjon må fortsatt matche under profillås. Feil scope, foreldet
counter/stamp eller publiseringskontekst gir ingen delvis lagring. To samtidige
writers med samme snapshot kan ikke begge committe. Canonical core-patch,
updated_at, DB-stamp og immutable audit commit/rollback samlet; en auditfeil
ruller også profil/stamp/tid tilbake. Audit inneholder actor, tenant, assignment,
domain, agreement, objekttype/-ID, handling, tidspunkt, forrige/neste revisjon,
stamp og endrede **feltnavn**. Ingen navn/beskrivelse, private notater, rå kontakt-
eller andre feltverdier lagres i audit eller logges av tjenesten.

UUID-metadata legges til i0038 og triggerne vedlikeholder den også når writer er
av. Dette er den nødvendige stale-garantien mot fortsatt aktive legacywrites,
ikke aktivering av delt redigering. Alle tidligere feltverdier og gamle
normaliserings-/publiserings-/slette-/import-/image-/safetykontrakter består.
Tjenestens SQL-patch endrer bare de eksplisitte feltene og updated_at; den kjører
ikke Model.save-sideeffekter for felter utenfor kontrakten.

**Bevisgrense:** Private felt, tags/M2M, kontakter, relasjoner, sted, bilder,
andre core-felt, authoritets-/rollehistorikk og urelaterte writes inngår ikke i
stamp/teller. De valgte feltene overskriver aldri disse dataene. En positiv
snapshotvurdering er ingen grant; reautorisering kreves alltid. DB-/ORM-tilgang
er privilegert drift og kan omgå application-writer; denne leveransen lover ikke
sikkerhet mot DB-administrator som deaktiverer triggere, forfalsker audit eller
bruker DDL/TRUNCATE. Ingen slik adgang gis til sluttbrukere.

### Migrasjon, rollback og senere aktivering

0038 legger bare til metadatafeltene, auditens tomme tabell/constraints og smale
triggere; ingen legacyfelt eller reelle avtaler/medlemskap/data flyttes. Additiv
API-kode kan rulles tilbake med nytt schema beholdt. Reverse tillates bare uten
canonical audit og med READ COMMITTED/profil- og auditlåser; før semantisk bruk
kan schema testes reverse/forward uten tap av gamle felt. Etter første write
bevares audit, profil, assignments og avtaler; slå av writer og rett framover.

Restore/rollback kan ikke gjenbruke gamle snapshots som godkjente grants eller
la gammel DB overstyre nyere tilbakekalling/deny. Writers holdes av, aksept- og
tilgangstap reconcileres og ferske revisionsnapshots kreves før senere åpning.
Bildeledger/deny og historisk image-state beholdes etter ADR-009; ingen ny ekstern
canonical-ledger eller restoregaranti utenfor eksisterende kontrakt er påstått.

Før faktisk shared redigering må alle gamle skrivbare innganger overføres
samlet: API, Editor, Admin, import og privilegerte ORM/SQL-jobber skal bruke samme
handlingsautorisasjon/revision/audit eller være eksplisitt stengt. Legacyfallback
må da være fjernet/avgrenset fra de aktiverte reisene. UI må beskrive delt og
PUBLIC-effekt; nye felt utover første kontrakt trenger eksplisitt scope og
stale-/auditdekning. Nåværende smale trigger er **ikke** en slik samlet cutover.
Avtale-/akseptflyt, reelle medlemskap/rollemapping, privat notatovergang,
image-home, tags og øvrige ADR-011-porter gjenstår. Denne leveransen aktiverer
eller ferdigmelder ikke hele trinn7/8/9/6A.

### Lokal validering

Syntetisk PostgreSQL16 dekker positive Organization-/Personpatcher, nøyaktige
verdier og begrenset audit, gate-off, feil tenant/domain/assignment, inaktiv
bruker/medlemskap, reader/superuser-/gruppeavvisning, manglende/tilbakekalt aksept,
publisert actor-capability, stale snapshots, legacy-API/ORM/SQL/ABA og uendret
counter for gamle writes. Separate forbindelser tester samtidige writes,
medlems-/brukerendring, revokasjon i begge rekkefølger, legacyendring under venting,
lock timeout og effective_at som passeres mellom policy og UPDATE. Python- og
reell DB-auditfeil ruller tilbake profilen; DB-/forbindelsesfeil sanitiseres både
før og inne i transaksjonen. Audit er immutable i ORM/SQL.
Migrasjonstest bevarer alle gamle felt gjennom forward/reverse/forward og
stopper reverse ved audit. To eldre migrasjonstestoppsett er tilpasset den nye metadata-kolonnen og
gjenoppretting av gjeldende migrasjonsleaf; gamle felter kontrolleres fortsatt
eksakt. Modell-/migrasjons-
samsvar og separat image-safety-regresjon inngår. Faktisk siste test/review/CI
publiseres i PR-en; ingen nye staging-/browser-/eierbevis er påstått.


## Stagingverifisering av trinn 8 – 2026-11-07

**STAGING VERIFIED, INACTIVE** innen det uttrykkelige mandatet: lever eksakt API
fra PR #101 og bare0037, med pre/post-backup, fullverify/isolert restore og
bevaring av eksisterende drift. Ingen avtale-/akseptopprettelse, medlemskaps-
deaktivering, shared-aktivering, canonical writer, notatkopi/-plan eller
produksjonssetting. Dokumentasjonsleveransen følger separat review/PR/ordinær
merge/CI; dokumentasjonsmerge deployes ikke. Dette er en senere bestilt
driftsvidereføring av den opprinnelige kodeleveransen nedenfor.

[Sanitert maskinevidens](../status/evidence/phase6a8-access-staging-2026-11-07/checks.json)
er kontrollert `2026-11-07T22:59:01Z` / **23:59:01 CET**. Private før-/etter-
fingeravtrykk, metadata, driftslogger og eksakte arkiv-/dumpkvitteringer beholdes
operatørbeskyttet utenfor Git. Ingen rå notater, personverdier, individuelle
profilhashverdier, credentials eller private manifest publiseres.

### Faktisk kode, skjema og inaktiv tilgang

- Før: rent stagingrepo/API `48ac5976bb6cf396b12335e8a108370f3b57af8d`, image
  `sha256:b9e76c4b0d3686f2462d27e259fd2a2a403264d98fe002dec5d0f559f3b119c1`,
  0036 anvendt, ingen0037-tabeller, 48 eksisterende DB-tabeller. Databaseidentitet
  ble kontrollert eksakt og var uendret gjennom hele etappen.
- Etter: rent stagingrepo/API **`d410e8e2e5e4a671edbd755f527d7eb52fe8103a`**,
  image **`sha256:4a0356cc23af52a96433fa3b7db44c6a3d85d7a7263f12b5a2c962677ba10630`**.
  Alle162 relevante kildefiler matcher Git. Image bygger på den tidligere
  immutable API-basen med eksakt Git-kilde lagt over; dependencyfingeravtrykk,
  Dockerfile, requirements og Composekontrakt er uendret. Ingen pip-/infraupgrade.
- Eksakt én pending migrasjon ble verifisert før apply. Bare
  `0037_sharing_access_foundation` ble anvendt med eksplisitt MigrationExecutor,
  prosessavgrenset READ COMMITTED, lock_timeout2s og statement_timeout30s.
  Ingen generell migrate/post_migrate, contenttypes/permissions/seed eller retry.
  Ny migrasjonsrad er eneste tillegg til `django_migrations`; gammel historikk
  er bevart. Sluttplanen er tom. Ingen schema-reverse eller API-rollback var nødvendig.
- `SharingAgreement`, `SharingAgreementAcceptance`, `SharingAgreementRevocation`
  og `SharingAccessAudit` har **0 rader hver**. Alle22 constraints er validerte,
  alle11 forventede triggere er enabled, og alle fire funksjonskropper matcher
  den godkjente migrasjonen. Eksisterende schema-/assignment-/overlayvern består.
- `TenantMembership.is_active` finnes som NOT NULL. Det var **0 medlemskap før
  og etter**. Ingen medlemskap er opprettet, deaktivert eller remappet. Kravet
  om True på eksisterende rader har dermed ingen reelle rader i staging; lokal
  syntetisk migrasjonstest i PR #101 dekker den befolkede tilstanden. Dette er
  ikke bevis for at virkelige brukere har ADR-011-medlemskap.
- `SHARING_ACCESS_ENABLED=False` og `TENANT_NOTE_OVERLAYS_ENABLED=False` er
  effektive og varige. Begge er unset i uendret `.env.staging` og bruker
  fail-closed False-default; de er heller ikke aktivert i containerens miljø.
  Alle ni nye capabilityvurderinger returnerer DISABLED. Ingen nye funksjonelle
  shared lesere/skrivere eller Adminmodeller er tilgjengelige. Medlemskapets
  nye active-felt er skjult i eksisterende Adminskjema.
- Begge notatoverlays og kopibatchregisteret har0 rader. Ingen kopikommando,
  kopiplan eller reell notat-/avtale-/aksept-/revokasjons-/audithendelse er kjørt/opprettet.

### Bevaring og teknisk lesebevis

Alle48 tidligere tabeller er sammenlignet med private, deterministiske
radfingeravtrykk, inklusive PK-er, tidsstempler, auth/session/grupper/rettigheter,
M2M, notater/tags, import, bildehistorikk og publication. Medlemskap sammenlignes
uten den ene nye active-kolonnen; alle tidligere felt er bevart. Det nye
skjemaet og én migrasjonsregistrering er de eneste DB-deltaene.

Frontend/web- og DB-container har samme identitet, image, start/restart,
Config/HostConfig og mounts. API-miljø/mounts/restartpolicy, miljøfil,
private originals, renditions, delivery og static er bevart. Ingen import-/
eksportfiler fantes i API-laget ved førkontroll eller etter graceful stopp.
Bare API ble rekreert, direkte med Gunicorn uten migrate/collectstatic;
nginx fikk nødvendig configtest/reload, uten web-recreate. Ingen ny Compose-/
Docker-/database-/frontendleveranse.

Eksisterende aktiv staff/plattformoperatør, tidligere dokumentert i backfill-
batch, ble gjenbrukt for teknisk **read-only** backendlesing:14 tenant-/modell-
lister,6 tilgjengelige detaljer,2 Adminlister,2 legacy-notatskjemaer og autentisert
session. Ingen konto, medlemskap, rettighet, login, session eller last_login ble
skrevet. Dette er RequestFactory/force_authenticate-bevis, ikke ny ekte
browserlogin/UX-runde eller manuell eieraksept. Legacy permissions/views/serializers/
ruter har ingen kildedelta og bruker fortsatt eksisterende rollefallback.

PUBLIC-katalog, HTML, frontend og HTTP-grenser svarte som forventet. Hele PUBLIC-
API-responsen og seks representative asset-/fallback-varianter har uendrede
bytes; PUBLIC/legacytags og image-/denyhistorikk er ikke lagt om. Safety forble
READY med samme ledger-/repositoryidentitet og event/read/anchor-cursor13;
ledgerfil og historikk er byteuendret. Ingen ledgerwrite, reassosiering eller
ny offentlig tilgang.

### Backup, driftsvindu og kontrollgrunnlag

Skrivefrys ble gjennomført ved graceful API-stopp. Backup-/verify-timere var
midlertidig pausede; ingen backupservice løp samtidig. Fersk pre- og post-backup,
full Borg repository-/archive-data-verifikasjon og isolert PostgreSQL16-restore
bestod. Hvert restorebevis er bundet til forventet arkiv, eksakt arkiv-ID og
dumpchecksum; begge arkividentiteter er lest tilbake etterpå. Post-restore
bekreftet0037, fire tomme historikktabeller,22 validerte constraints,11 aktive
triggere, null inaktive medlemskap og fortsatt tomme note-/batchtabeller.

Installerte backupskript er uendret. Private kopier fulgte eksisterende
kontrollert prosedyre uten prune/compact, med arkivbinding og eksplisitt cleanup
av isolerte restorecontainere inklusive anonyme volumer. Volumsettet er bevart;
ingen restorecontainere står igjen. Backup-, verify- og safety-health-timere er
active/enabled; backup-/verify-services er inactive i sluttkontrollen.

Operatørskriptene fikk separat skrivebeskyttet statisk review før driftsmutasjon,
bundet til de tre helperhashene i JSON-evidensen, uten blokkerende funn.
En innledende **read-only** target-image-kontroll forsøkte SessionView før den
nye is_active-kolonnen fantes. Kontrollskriptet ble rettet før schema/runtime-
endring: pending-mode verifiserer identitet/plan/data/flags/struktur, mens
før-/etter-runtime gir lesebeviset. Samme bygde image ble revalidert uten nybuild;
ingen migrasjon, backup eller datahandling måtte gjentas som følge av dette.

### Gjenstående tilgangs- og autoritetsovergang

Ingen teknisk drifts-/restoreblokker står igjen for en **separat bestilt**
trinn9-leveranse. Det er ikke en godkjenning av shared writes. Før virkelig
bruk kreves eksplisitte aktive medlemskap/rollemapping, gjeldende juridisk
avtaletekst og autorisert aksept-/tilbakekallingsflyt. Ingen tilgang kan åpnes på
dagens tomme medlemskaps-/akseptgrunnlag.

Canonical writer skal fortsatt leveres med atomisk reautorisering, expected
revision/stale-kontroll og handlingsaudit. Gamle API-/Editor-/Admin-/import-/ORM-
innganger må overføres samlet før autoritetsovergang, slik at legacyfallback
eller gammel writer ikke omgår kontrakten. Image-home, tags, PUBLIC og øvrige
ADR-011-porter består. Reell notatkopiering utsettes til nødvendig tilgangs-/
writergrunnlag, med fersk plan og separat godkjenning. Ingen ny notatinventar-,
diagnose- eller reparasjonsrunde er utført. Trinn7 og hele trinn8/6A er fortsatt åpne.


**Visuell rettingsrunde 2, 25.10.2026:** Slett aktør er gjenopprettet i Editor med
eksisterende superadmin/gruppeadmin, eksplisitt confirm og serverens tenant-/
DELETE-beskyttelse. Tildelt/beskyttet profil gir fortsatt 409 og beholdes. Ingen
ny rolle eller livssyklus; redigerer kan ikke slette. Se [UI-6 §11](../features/UI_6_FELLES_SPEC.md#11-andre-visuelle-retting-av-pr-92--2026-10-25).

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

## Godkjent sharing-domain-sikkerhet – delvis grunnmur, ingen aktivering

[ADR-011](../decisions/ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md)
godkjenner målarkitekturen for deling innen eksakt SharingDomain. Dagens direkte
tenantroller og gruppefallback er fortsatt aktiv nåtilstand; den inaktive trinn-8-grunnmuren nedenfor er implementert, men ingen shared
funksjoner eller aktive agreementgater er koblet til brukerreisene.

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

## ADR-011 trinn 8 – inaktiv tilgangsgrunnmur, 2026-11-07

**Mandat:** Første avgrensede additive kodeleveranse etter `c05dc87`. Lokal
PostgreSQL-validering, dokumentasjon, separat review, PR/ordinær merge og CI;
ingen staging/schema-apply, reelle avtaler/aksepter, shared-aktivering eller
notatkopiering. Juridisk tekst, aksept-UI, canonical writer og revisjonskontroll
leveres senere. Trinn 7 og hele trinn 8/6A er fortsatt åpne.

### Gjenbruk og konkrete mangler

Eksisterende `TenantMembership` og de fire tenantrollene gjenbrukes, sammen med
SharingDomain, domainbindinger og assignments. Additiv0037 legger til
`TenantMembership.is_active=True` for eksisterende medlemskap; bare den nye
policyen bruker feltet. Gamle views/permissions beholder nøyaktig sin eksisterende
rolleoppløsning og brukerreiser. Ingen medlemskap opprettes.

`crm/services/sharing_access.py` bruker **aldri** `get_user_tenant_role`, globale
Django-grupper, `is_staff` eller `is_superuser` som tilgangsgrunnlag. En
plattform-superuser trenger samme eksplisitte aktive medlemskap, avtale og
capability som andre. Rollen tas fra dette medlemskapet, også for superuser.
Dermed er global fallback avgrenset bort fra den nye kontrakten. Eksisterende
fallback i legacy API/image-ruter består; de må overføres samlet før shared
aktivering, slik at gamle ruter ikke omgår nye regler. Den endringen gjøres
ikke i denne leveransen.

Eksisterende 0034-/assignmentvern avviser sletting av tildelte profiler/tenants
og assignmentfjerning, også via bulk/SQL. Dette bevarer dagens godkjente
midlertidige slettebegrensning. Ingen ny deletion-workflow er nødvendig for
inaktiv grunnmur. Før framtidig assignment-/multiassignment-write kreves fortsatt
egen kontrollert livssyklus; tenant-CASCADE må aldri slette et objekt med en
annen assignment. Ingen gammel tillatt slettereise er endret her.

### Immutable avtale- og aksepthistorikk

- `SharingAgreement`: eksakt tekst, domain, positiv versjon, `effective_at`,
  forfatter og DB-stemplet opprettelsestid. Versjon og virkningstid må øke per
  domain; begge er unike innen domain. En framtidig versjon erstatter den gamle
  nøyaktig fra `effective_at`, uten grace. Det finnes ingen defaultavtale.
- `SharingAgreementAcceptance`: bruker, eksakt avtaleversjon/domain (via FK),
  aksepttenant og DB-stemplet tidspunkt. Innsetting krever aktiv bruker og
  eksplisitt aktivt, gyldig medlemskap i en tenant i avtaledomainet, samt den
  gjeldende versjonen. Aksept gjelder bruker/domain, også i andre tenants i
  samme domain når brukeren der har eget aktivt medlemskap.
- `SharingAgreementRevocation`: separat, immutable hendelse med én referanse
  til aksept, samme bruker som actor og DB-stemplet tidspunkt. Aksept slettes
  eller oppdateres ikke. Status avledes som gjeldende, erstattet eller
  tilbakekalt. Ny eksplisitt aksept etter tilbakekalling er mulig uten å
  gjenopplive den gamle. Bare én ikke-tilbakekalt aksept per bruker/versjon
  tillates. Tilbakekalling krever ikke fortsatt aktivt medlemskap eller bruker;
  den kan dermed bevares også etter tilbaketrekking av tilgang.
- `SharingAccessAudit`: DB-generert hendelse for hver avtale, aksept og
  tilbakekalling i **samme transaksjon** som kilderaden. Bare hendelsestype,
  kilderad-ID, actor-ID, domain-ID, eventuell tenant-ID og tidspunkt lagres;
  ingen notater, kontaktdata, avtaletekst eller frie metadata. Historiske ID-er
  er snapshots og reassosieres aldri ved senere sletting.

ORM avviser endring/sletting; PostgreSQL-triggere avviser UPDATE/DELETE og
upsert-oppdatering også gjennom direkte SQL/bulk. Audit kan ikke skrives
uavhengig gjennom vanlig INSERT. Triggere låser domain/bruker/medlemskap for å
serialisere avtaleplanlegging og aksept; en mislykket audit ruller kilden tilbake.
Historikkinnsetting krever READ COMMITTED i databasen. REPEATABLE READ og
SERIALIZABLE avvises eksplisitt: en låseventing må etterfølges av et ferskt
snapshot, ellers kan duplicate-/rekkefølgekontrollen bruke gammel state.
Dette er ikke beskyttelse mot DB-administrator med DDL-/TRUNCATE-/triggerkontroll.
Direkte DB-/ORM-tilgang er privilegert drift, aldri en brukerautorisasjon.

Modellene er **ikke registrert i Admin, API eller frontend**. Ingen støttet
avtalepubliserings-, aksept- eller tilbakekallingsrute er innført; ingen slik
state opprettes automatisk. Teknisk lagring bestemmer ikke hvem som skal få
publisere juridisk avtaletekst eller utføre delegert tilbakekalling. Disse
brukerhandlingene trenger eksplisitt autorisert servergrense ved senere levering.

### Handlingsspesifikk policy, default-off

`SHARING_ACCESS_ENABLED=False` leses fail-closed fra miljø; ukjente verdier gir
False. Ingen eksisterende runtimekall bruker den nye policyen. Selv aktivering
av dette ene flagget oppretter ingen funksjonelle shared lesere/skrivere.

`assess_access()` kontrollerer fersk DB-state og DB-tid: aktiv bruker,
aktivt eksplisitt medlemskap, eksakt tenant/domain, kjent rolle, handlingscapability
og gjeldende ikke-tilbakekalt aksept. Disse grunnvilkårene evalueres i ett
PostgreSQL-statement-snapshot. Den returnerer bare en avgrenset beslutningskode
og interne avtale-/assignmentreferanser; ingen profil-/notatdata eller serializer.

| Capability | Første rollemapping og ytterligere scope |
| --- | --- |
| `SHARED_MATCH` | Alle fire medlemskapsroller; bare domain, ingen objektpayload |
| `ADD_TO_OWN_TENANT` | Superadmin/gruppeadmin/redigerer; eksisterende objekt i eksakt domain, bare angitt aktiv membershiptenant |
| `EDIT_SHARED_CORE` | Samme skrivende roller; eksakt egen assignment; publisert aktør avvises og krever egen capability |
| `EDIT_PUBLISHED_CORE` | Samme skrivende roller; Organization og egen assignment |
| `PUBLISH` | Samme skrivende roller; Organization og egen assignment |
| `READ_PRIVATE_OVERLAY` | Alle fire roller; eksakt egen objekt-/tenantassignment |
| `WRITE_PRIVATE_OVERLAY` | Skrivende roller; eksakt egen objekt-/tenantassignment |
| `WRITE_IMAGE_HOME`, `TRANSFER_IMAGE_HOME` | Navngitt, men **ingen tildeling** før separat image-home bridge |

Private kontroller gir aldri andre tenanters assignment tilgang. Assignment til
ny tenant opprettes ikke av en positiv vurdering. Caller må binde `tenant_id` til
den autentiserte requestens eksplisitte aktive tenant; det er ingen parameter for
å velge en annen måltenant innenfor samme handling.

En positiv vurdering er et **øyeblikksbilde, ikke et gjenbrukbart grant/token**.
Senere writer skal kontrollere tilgang på nytt under sin atomiske låse-,
expected-revision-/auditgrense, også ved endret medlemskap, avtale eller
publiseringsstatus. Denne leveransen lover ingen ferdig shared-write-kontrakt
eller canonical audit/revisjon. Det finnes ingen nye shared dataqueries,
matchingprojeksjon, overlaylesere/-skrivere eller aktivering.

### Migrasjon, bevaring og neste gate

0037 er kun additivt skjema og standardverdien True på eksisterende medlemskap;
ingen seed eller dataflytting. Eksisterende serializers/Admin-feltlister, API,
Editor, import, PUBLIC, tags, imagehistorikk, safety-ledger og deny-state er
uendret. Nye tabeller skal være tomme etter en senere separat godkjent
schema-apply. Backup/fullverify/isolert restore og eksakt migrasjonsplan kreves
etter gjeldende driftsrunbooks før slik stagingbestilling.

Reverse krever READ COMMITTED, tomme nye tabeller og ingen `is_active=False`-state;
snapshot-isolasjon avvises også her før kontroll/låsing.
Etter første semantiske avtale-/akseptstate beholdes historikken; slå av ny
funksjon og rett framover. Restore av eldre DB kan gjenopplive gammel aksept eller
medlemskap: før framtidig aktivering må gjeldende tilbakekallinger/tilgangstap
reconcileres fra autoritativt bevis, ellers forblir ny tilgang av. Denne
leveransen etablerer ingen ekstern restore-sikker avtaleledger og endrer aldri
ADR-009s eksisterende image-safety-/deny- og historiske identitetskontrakt.

Prosjekteiers avklaring 2026-11-07: Endringen fra 12 til 13 notatkandidater er en
ordinær redigering av et internt personnotat, ikke migreringsavvik. Ingen ekstra
inventar/diagnose/reparasjon gjennomføres. Legacydata forblir autoritative;
faktisk kopiering utsettes til nødvendig tilgangs-/writergrunnlag er på plass,
med fersk plan og separat godkjenning.

### Lokal verifikasjon for denne leveransen

Første validering ga 687 grønne backendtester, inklusive 13 nye, på syntetisk
PostgreSQL 16.14, samt 64 grønne separate image-safety-tester. Separat review
identifiserte snapshot-isolasjonsrisiko i innsettingstriggerne; rettingen krever
READ COMMITTED. Etter rettingen er 93 berørte tester (14 nye + 79 eksisterende)
grønne, inklusive negative RR/SERIALIZABLE- og reverse-kontroller og beholdt
RC-samtidighet. Relevant separat re-review og CI følger GitHub før merge.
Sikkerhetstestene dekker positiv rollemapping og negative kontroller for
cross-tenant/-domain, feil eller manglende assignment, manglende/erstattet/
framtidig/tilbakekalt aksept, eksakt effective-at uten grace, inaktiv bruker,
inaktivt/slettet/ukjent medlemskap og manglende capability. Superuser og global
Django-gruppe alene avvises. Publisert aktør krever sin separate capability;
image-home-handlinger er fortsatt avvist. Policyen skriver ingen data.

Migrasjonstest dekker eksisterende medlemskap, ingen seed, tom reverse/forward
og reverse-stopp ved ny historikk eller deaktivert medlemskap. SQL-/ORM-vern,
duplikataksept og samtidige aksepter, auditfeil/atomisk rollback og eksisterende
assigned-delete-beskyttelse testes. Et eksisterende0036-migrasjonstestoppsett er
tilpasset senere additive tabeller; kopitjenesten er uendret.

Reproduser med lokal, isolert testdatabase og `python manage.py test crm` samt
`python manage.py makemigrations --check --dry-run`. Eksisterende separate
image-safety-tester kjøres med `python3 -m unittest discover -s ops/image_safety/tests`.
Dette er teknisk lokal/CI-validering, ingen ny Editor-/Import-UX-runde,
eieraksept, stagingevidens eller bevis for en ferdig shared writer.
