# 6A.2 – eksplisitt domenebinding og legacyassignment

**Status:** lokalt implementert 2026-10-13; skrivebeskyttet review 2026-10-14 uten
blokkerende funn. Publisering som draft PR på `feat/phase6a2-legacy-domain-backfill`
er bestilt; faktisk commit/push/PR/CI følger GitHub og SESSION WRAP-UP.
Ikke deployet, schema-applied eller backfillet på reelle data.
Godkjent lokal bestilling og presiseringer fra prosjekteier 2026-10-13 under
ADR-011, ADR-013 og 5E-planen. Dette er operatørstyrt registrering av eksisterende
tilhørighet, ikke deling eller vanlig brukers assignmenthandling.

## Mapping og inngangsgrunnlag

Mappingfilen har eksakt `domain` og `tenants`. Domain har `id`, `slug`, `name`;
`id: null` betyr eksplisitt godkjent opprettelse. Dersom slug/ID allerede finnes (eller navnet finnes ved foreslått opprettelse),
må faktisk domain-ID, eksakt slug og navn godkjennes og oppgis. Ingen gjetning,
default-domain, renaming eller automatisk seed. Hver tenant har ID, eksakt
eksisterende slug og forventet navn. Tomt/duplisert/ukjent utvalg avvises;
valgte tenants uten profiler er gyldige. Utvalget trenger ikke omfatte alle
plattformtenants. ID-er er miljøspesifikke.

Skrivebeskyttet staginginventar **2026-10-13 21:09:13 UTC / 23:09:13 CEST**:

| ID | Eksakt slug | Forventet navn | Organization | Person |
| --- | --- | --- | ---: | ---: |
| 1 | musikkontoretnord | Musikkontoret Nord | 121 | 147 |
| 2 | musikkontoretmxst | Musikkontoret MØST | 3 | 4 |
| 3 | musikkontoretbrak | Musikkontoret Brak | 4 | 6 |
| 6 | musikkontoretoks | Musikkontoret ØKS | 0 | 0 |
| 7 | musikkontoretsorf | Musikkontoret SØRF | 0 | 0 |
| 8 | musikkontoretstar | Musikkontoret STAR | 0 | 0 |
| 9 | musikkontorettempo | Musikkontoret Tempo | 0 | 0 |

Alle bindinger var NULL; domain-/assignmenttabellene tomme. 176 relasjoner,
223 kontakter og kontrollerte tagkoblinger hadde ingen tenant-scopeavvik.
Dette er datert lesebevis, **ikke apply-tillatelse eller senere førmåling**.
Foreslått mål er `Musikkontoret` / `musikkontoret`; reell apply krever ny,
fersk godkjenning av komplett mapping og dry-run. Ingen staginglesing eller
stagingwrite inngår i den lokale implementeringsøkten. Lokal testing bruker
bare syntetiske identities/data.

## Kommando og tilstander

`python manage.py backfill_legacy_domain --mapping /private/path/mapping.json`
leser ett `REPEATABLE READ READ ONLY`-snapshot. Ingen domain, batch eller andre
DB-rader opprettes. Rapporten inneholder eksplisitte identiteter, interne IDs,
antall, forslag til endringer og deterministisk SHA-256-plandigest; rå person-,
kontakt-, notat-, telefon-, fil- og bildedata inngår bare i interne hasher.

`--apply` er separat og krever alle disse argumentene:

- `--mapping`, `--environment`, `--expected-database` fra dry-run;
- `--expected-digest`, `--batch-id`, `--operator-id`;
- `--code-baseline` (40-tegns kodebaseline oppgitt av operatør);
- `--manifest-path` (absolutt privat no-clobber path).

Databaseidentitet er PostgreSQL cluster system identifier og databasenavn,
ikke Docker-IP eller et fritt valgt databasealias. Lesing av `pg_control_system()`
må være tillatt for driftsforbindelsen; manglende tilgang gir ingen fallback.
Operatør-ID må være aktiv staff/platform-superuser. CLI-tilgangen er den
operasjonelle autorisasjonen; ID-argumentet dokumenterer den identifiserte
operatøren og er ikke nettleserinnlogging eller autentisering av en vilkårlig
API-bruker. Faktisk deployet kodebaseline må kontrolleres separat i applyordren.
Ingen ny application-endpoint, agreementgate eller capabilityplattform finnes.

NULL-binding/manglende legacyassignment gir eksplisitte planlagte endringer.
Delvis konsistent tilstand kan fullføres bare gjennom et nytt godkjent dry-run.
Fullt korrekt tilstand gir en **ny no-op-plan**. Feil domain, feil/ekstra
assignment, ukjent domainidentitet eller inbound relasjons-/kontakt-/tag-scopeavvik
stopper hele operasjonen uten automatisk reparasjon eller fjerning.

`LegacyDomainBackfillBatch` har unik `(environment, database_identity, batch_id)`.
PREPARED registreres separat før data-apply; en ny manifeststi kan ikke omgå
registeret. Samme batch med annen request/operatør/kodebaseline/digest/path avvises.
Gjentatt identisk batch gjør **kun read-back**, aldri automatisk apply igjen.
En ny no-op-plan krever ny batch-ID og riktig eksisterende domainidentitet.

`--read-batch --environment ... --expected-database ... --batch-id ...
--operator-id ...` er egen read-only-modus. PREPARED er ikke commitbevis.
COMMITTED_VERIFIED betyr at endringer og verifisert DB-kvittering ble committet
i samme transaksjon. Read-back oppgir også om dagens snapshot fortsatt matcher;
senere legitim profilredigering kan gi `current_state_matches_receipt=false`
uten å gjøre historisk commit usann. Ved ukjent batch gis kontrollert feil.

## Transaksjon, konkrete låser og samtidighet

Apply krever en ytre, egen PostgreSQL-transaksjon; den kan ikke kalles inne i
en eksisterende Django-transaksjon. Muterende arbeid er én `atomic(durable=True)`
med **READ COMMITTED**, slik at planen beregnes fra et nytt snapshot **etter** at
alle tabellåsene er ervervet. Den godkjente digest kontrolleres deretter.
Dry-run-snapshotet gjenbrukes aldri som applyens database-snapshot.

Alle tabeller nedenfor låses én etter én i denne sorterte rekkefølgen med
**SHARE ROW EXCLUSIVE**, `lock_timeout=5s` per låserverv. Lesere kan fortsette;
vanlig DML og annen apply må vente. Hele CRM-grunnlaget inngår i global
bevaringsfingerprint, også data utenfor utvalget; derfor er låsen kortvarig
plattformvid for CRM-writes, ikke bare en tenant-radlås. `auth_user` låses for
stabil operatørstatus. Batchregisteret er separat og omfattes ikke av
CRM-bevaringshashen. Tabellenes liste genereres fra dagens konkrete CRM-modeller,
inkludert auto-created M2M; den er ikke en allowlist for å migrere flere objekter.

```text
auth_user
crm_category
crm_exportjob
crm_imageasset
crm_imagerendition
crm_imagerenditionset
crm_imagereviewevent
crm_importcommitlog
crm_importdecision
crm_importimagedecision
crm_importjob
crm_importrow
crm_organization
crm_organization_categories
crm_organization_subcategories
crm_organization_tags
crm_organizationimagerelease
crm_organizationimagereleaserendition
crm_organizationimageselection
crm_organizationperson
crm_organizationtenantassignment
crm_person
crm_person_categories
crm_person_subcategories
crm_person_tags
crm_personcontact
crm_persontenantassignment
crm_sharingdomain
crm_subcategory
crm_tag
crm_tenant
crm_tenantmembership
```

Før-/etterhash dekker alle eksisterende CRM-kolonner og M2M-rader, unntatt de
nye domain-kolonnene som må endres og de tre nye strukturtabellene som må fylles.
Disse strukturtabellene måles separat. PK, legacytenant, tidsstempler, råverdier,
telefon, publication og bilde-/importhistorikk bevares. Etterplan må ha null
restendringer, én assignment til hver profils egen legacytenant og uendret
bevaringshash. Feil før commit ruller hele semantiske transaksjonen tilbake;
PREPARED-register/privat forsøksmanifest kan bestå.

PostgreSQL-triggerne låser assignmentens tenant og deretter profil med
**FOR SHARE**, som konflikter med domain-/tenantoppdatering. FOR KEY SHARE er
ikke tilstrekkelig for disse ikke-nøkkelfeltene. Profilbinding kontrollerer og
låser legacytenant med FOR SHARE. Etablert ikke-NULL binding kan ikke rebindinges;
bound profil kan ikke bytte legacytenant. UPDATE/DELETE av assignments avvises.
Databasevern gjelder også bulk/raw SQL og avviser feil/manglende domain.
Migrasjonen avviser inkonsistent eksisterende struktur før triggerinstallasjon.
Separate PostgreSQL-forbindelser tester både vente- og motsatt skriveorden,
concurrent legacy insert/edit, apply, lock timeout og avbrudd. Databaseadministrasjon
som deaktiverer triggere er ikke en støttet writer og er ikke gjort WORM-sikker.

ORM-vernet omfatter domainfelt og assignmentmodellene, inklusive default/base/
reverse-manager, bulk, upsert og private insert/deleteveier. Tjenestens private
insertadgang er avgrenset til eksakte modell/profil/tenant-tupler i transaksjonen
og nullstilles i `finally`, også ved feil. Den autoriserer aldri update/removal.

## Legacyadferd og slettebegrensning

Vanlig tillatt profilredigering, legacylesere/import og PUBLIC består. Nye
legacyprofiler opprettes med NULL-domain og uten skjult assignment. Admin skjuler
fortsatt domain og låser tenantfeltet på bound profiler, også ved forged POST.
API returnerer kontrollert `409/profile_delete_protected` ved ProtectedError;
Django admin viser eksisterende protected-delete-avvisning.

Prosjekteier har akseptert at **assigned profiler og berørte tenants ikke kan
slettes gjennom vanlige handlinger**, også med bare egen legacyassignment.
Assignment må aldri slettes først for å omgå parent-PROTECT/FK-vern. Siste
assignment/canonical delete og ombinding er senere autoriserte livssykluser.
Dette er en faktisk slettebegrensning etter backfill, ikke uendret sletteadferd.

Nye legacyprofiler tas igjen gjennom separat, fersk scope/dry-run/catch-up før
senere duplicate inventory/migration manifest og shadow/cutover. Denne
førkontrollen eller kvitteringen erstatter ikke ADR-011s senere trinn.
Ingen multiassignment-brukerhandling, shared reader/writer, privat overlay,
PUBLIC-cutover, image-home, kontakter/Places eller Import 2.0 er aktivert.

## Kvittering, tilbakeføring og senere driftsport

Privat PREPARED-manifest inneholder request, godkjent låst plan, førtilstand,
interne IDs, mapping og digest. Filen er ikke commitkvittering. DB-recorden
COMMITTED_VERIFIED har request, faktisk domain-/assignment-ID, endrede felt/IDs,
før-/etterfingerprints og låsekontrakt. En separat `.verified.json` skrives
etter DB-commit. No-clobber paths må oppfylle eksisterende phone-backfill-verns
krav til operatøreierskap, privat parent, symlink-/pathkontroll og 0600-fil.

Filskriving og DB-commit er ikke én atomisk transaksjon. Ved nettverksfeil/tapt
commit-svar eller manglende filkvittering: les tilbake batchregister og snapshot.
Ikke blind retry, bruk ny path eller erklær rollback fra et feilsvar. En PREPARED
batch må avklares operasjonelt; den gjenkjøres ikke automatisk. Etter committet
semantisk state bevares bindinger/assignments/audit og feil rettes fremover.
0034-forward låser de seks strukturtabellene i sortert rekkefølge med SHARE ROW
EXCLUSIVE før konsistent preflight/triggerinstallasjon. Reverse låser samme utvalg
og `crm_legacydomainbackfillbatch` i sortert rekkefølge før tomhetskontroll; begge
har 5s lock timeout. 0034-reverse avvises når bindinger, domain, assignments eller
batchbevis finnes.
0033 endres ikke og har ingen ny seed/datamigrering.

Reell deploy/schema-apply/backfill krever senere egen bestilling, reviewed kode,
grønn CI, fersk godkjent mapping/digest/inventar, vernet driftsvindu, checkpoint
som ikke kan prunes av vanlig sammedagsretensjon, og restorebevis fra samme arkiv.
API-start kjører migrate/collectstatic og er ingen tillatelse til data-apply.
**Docker-images/image layers og staticfiles inngår ikke i normal Borg-backup.**
Konfigurerte **bildemediaområder** private/public/public-delivery inngår derimot
i backupdekningen; dette må kontrolleres mot faktisk konfigurasjon.
Ingen Borg-/stagingoperasjon utføres av kommandoens lokale tester.

## Lokal verifikasjon

`crm.test_phase6a2_backfill` og oppdaterte `crm.test_phase6a1_foundation` bruker
isolert PostgreSQL og syntetiske fixtures. Den standalone lokale testen
`python3 crm/test_phase6a2_restore.py` bruker eksisterende Docker-images og en
ny privat nettverks-/PostgreSQL-container uten eksisterende CRM-volumer. Den
backfiller syntetiske data, tar pg_dump, restaurerer til en annen syntetisk DB,
sammenligner state/batchbevis og tester aktive triggere, SQL-/ORM- og parentvern.
Original databaseidentitet bevares i den restaurerte historiske batchen; den
forveksles ikke med ny databaseidentitet. Testen rydder egne containere/nettverk.
Dette er ingen restore mot eksisterende lokal CRM, staging eller produksjon.

Verifisert lokalt: samlet CRM-kjøring 605/605 bestått; siste målrettede 6A.1/6A.2-kjøring
37/37 bestått etter siste endringer (inkludert to nye samtidighets-/lesetester).
Django system check er grønn og `makemigrations --check --dry-run` finner ingen endringer.
Standalone dump/restore har identisk state og fem aktive/verifiserte triggere.
Ingen ny CI er kjørt for den lokale, upubliserte diffen; baseline-CI er ikke dens CI-bevis.
