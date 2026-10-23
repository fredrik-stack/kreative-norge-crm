# Tenantprivate notater – inaktiv lagringsgrunnmur

## Mandat 2026-10-24 og leveransegrense

Prosjekteiers bestilling av ADR-011 migreringstrinn 7 autoriserer additiv
notatgrunnmur → lokal PostgreSQL-test → faktisk separat, skrivebeskyttet review
bundet til base/head → ordinær merge/CI → avgrenset API-deploy og reviewet
schema-apply i staging → ett konsistent read-only notat-/taginventar → separat
reviewet og merget sanitert evidens. Baseline er `2181ceee598965ab4083226443dcce885d44db51`.
Ingen ny generell plan-/ADR-/UX-runde. Dette er ikke fullført trinn 7.

Ingen eksisterende CRM-data flyttes, klassifiseres eller endres. Ingen nye
assignments, domenebindinger, catch-up, deduplisering eller telefonretting.
Ingen brukerinngang, API-felt, adminregistrering, importkobling, signal,
dual-write, overlaylesing/fallback, shared-aktivering eller produksjonssetting.
UX v6 rev. 4/O-24, godkjent 5E og Google Maps-aktørkart i Editor/PUBLIC består.

## Lagringskontrakt

`OrganizationNoteOverlay` og `PersonNoteOverlay` har bare PK, `assignment` og
nullable `note` (TextField). OneToOne/unik FK til tilsvarende eksisterende
TenantAssignment gir ett notat per profil/tenant. Ingen parallelle tenant-,
profil- eller domainfelt. Assignmentenes eksisterende PostgreSQL-vern krever
samme eksplisitte, ikke-NULL domain på begge endpoints og forbyr ombinding og
fjerning. Overlay-FK bruker PROTECT; eksisterende parent-slettevern består.

Migrasjon 0035 oppretter bare de to tabellene, FK-/unikhetsindekser og to
identity-triggere/felles funksjon som avviser endring av overlay-PK/assignment.
Ingen seed eller datakopiering. Forward RunPython er bare noop; reversevakten
avviser tabellfjerning ved én eneste overlayrad, også NULL/tom note. Tom reverse
og fremovermigrering er lokalt testet. Staging skal ikke reverseres destruktivt.
Normal rollback er gate av og eventuelt forrige API-image; behold additive tabeller.

`TENANT_NOTE_OVERLAYS_ENABLED=False` er fail-closed kode-/eksempelstandard via
samme bool-parser som øvrige writegater. Gaten gjelder ordinære ORM-writes på
begge modeller: save/save_base/raw fixtures, create/get_or_create når insert,
update_or_create, update, bulk_create/bulk_update og delete/_raw_delete, også
base manager. Upsert/conflictmoduser avvises. Gate på tillater bare teknisk
lagring, ikke brukerrettigheter. Ingen kobling til backfillens private fullmakt.
Raw SQL/eksplisitt konstruert generisk QuerySet og DB-administrasjon er ikke
featuregate-grenser; FK, unikhet, assignmentvern og identity-triggere består.

NULL, `''` og tekst/whitespace lagres nøyaktig uten trimming/default/fallback.
En fraværende overlayrad er en annen tilstand enn en eksisterende rad med NULL
eller tom streng. Ingen nåværende leser bruker overlay. Senere skal tom/NULL
verdi aldri trigge gjenoppliving av gammel tekst via sannhetsverdi-fallback.

## Faktiske ruter og senere omlegging

Alle radnumre følger versjonen i Git; funksjonsnavnene er varige søkepunkter.

| Kildefelt / autoritet nå | Aktiv lesing/skriving og tenantkontekst | Nødvendig senere omlegging |
| --- | --- | --- |
| Organization.note / Person.note, profilraden | `crm/serializers.py`: OrganizationSerializer/PersonSerializer, `crm/views.py`: tenantfiltrerte get_queryset/perform_create. API PATCH skiller utelatt felt (behold), NULL og tom streng; DELETE er profilens eksisterende slettelivssyklus | Én samlet autoritetsovergang for alle writes; eget tenant-/assignmentoppslag og autorisasjon. Ingen generell shared serializer for overlay |
| Samme legacyfelter, Editor | `frontend/src/hooks/useEditorData.ts`, `OrganizationsPage.tsx`, `PeoplePage.tsx`: editorutkast normaliserer NULL til tom streng; payload bruker nullableString. Klientsøk bruker også notat/taggtekst. Aktørkort viser description eller note | Skill presentasjon/normalisering fra tapsfri lagring. Tomt overlay må være autoritativt; søk/kort må bruke tillatt privat scope |
| Legacy note/tags, admin | `OrganizationAdmin`/`PersonAdmin` autogenererte forms og save_model; filter_horizontal for tags. TagAdmin endrer tenantbundne tags. Ingen overlaymodell registrert | Admin må følge samme writer og privat autorisasjon før cutover; dagens globale rollefallback er ikke tilstrekkelig bevis |
| Legacy note/tags, import | `normalizers.normalize_import_row` trimmer note og kollapser manglende/NULL/tom til `''`; `commit.commit_import_job` bruker `note or None` på create/update. `_get_or_create_tags` og `.tags.set()` erstatter taggsett i jobbens tenant | Typed behold/sett/tøm/slett-kontrakt, samlet writeromlegging og stale-/auditkontroll. Nåværende import kan ikke brukes som tapsfri kopieringsmotor |
| Tags: tenantbundet Tag + Organization.tags/Person.tags M2M | API `tag_ids`/tags, tenantvalidering i serializer, TagViewSet, admin, import. Direkte M2M add/set/remove/clear og through-modell bulk/SQL er tekniske omveier; gjennom-tabeller har ikke generell cross-tenant domainpolicy | Eksplisitt mapping av hver legacytagg og kobling. Sperr/legg om alle gamle M2M-writes før shared bruk. Category/Subcategory er separat taxonomy |
| Matching og AI-adaptere | `import/matchers.py`: legacytenant, kontakt-/navn-/orgnr.-signaler; kandidatprojeksjon id/label uten note/tags. `ai_suggestions.py`: lokale tekst/taggforslag bruker importnotater; `_suggest_description` kan foreslå noteutdrag. Providergrunnlag bruker normalized_payload og tenantens eksisterende taggnavn | Privat importgrunnlag/AI krever eksplisitt policy; ikke mat nye overlays inn i provider eller shared matchprojeksjon. Review av note→description må inngå før privat cutover |
| PUBLIC | `serializers_public.PublicActorSerializer` bruker legacy Organization.tags; notat er ikke serialisert. PUBLIC HTML bruker samme aktuelle aktørgrunnlag, ikke overlays | Bare eksplisitt shared editorial-mapping kan bli framtidig PUBLIC-taxonomy; dagens publisering klassifiserer ikke legacytags |
| Eksport | ExportJob/ExportJobSerializer/ExportJobViewSet: opprett/list/detail og filmetadata. Ingen implementert generell CRM CSV/XLSX-generator funnet. Import-reporting skriver importresultatrapporter | Senere eksport må velge privat/shared/public scope eksplisitt; ikke omtale planlagt eksport som eksisterende notatleser |
| Direkte lagring | Model.save, QuerySet.update/bulk og M2M-through kan skrive legacyfelter uten API; ingen automatisk overlaykopiering | Avvikle eller beskytte alle aktive skriveruter samlet. SQL-/operatørpolicy må spesifiseres ved senere dataflytting |

`Organization.description` er separat beskrivelsesfelt; `OrganizationPerson.status`
er relasjonsstatus. Ingen av dem flyttes/klassifiseres som private arbeidsfelt her.

## Bestilt staginginventar og bevis

Forventet database er `postgresql:7621672066239828005:crm_db`. Ett snapshot på
samme forbindelse, REPEATABLE READ READ ONLY før første datalesing, statement
30 s/lock 2 s. Revalider domain 1/musikkontoret/Musikkontoret og eksakt tenantsett:
1/musikkontoretnord, 2/musikkontoretmxst, 3/musikkontoretbrak,
6/musikkontoretoks, 7/musikkontoretsorf, 8/musikkontoretstar, 9/musikkontorettempo.
Ingen gjentakelse av duplikatinventar eller shadowmåling.

Rapporter per modell/tenant NULL-, eksakt tom-, whitespace-only- og tekstdekning;
NULL-domain, feil domain, manglende/ekstra/feil assignments og kandidater med
én egen korrekt assignment som forutsetning for senere flytting. Les assignment-
og M2M-koblinger uten å filtrere bort ugyldige endpoints. Rapporter aggregert
taggrad-/koblingsdekning, tenant-/domainavvik, ubrukte/multibrukte legacytags og
PUBLIC-eksponerte aktørtagkoblinger uten taggnavn, profilidentiteter eller tekst.
Historiske tellinger er bare referanser. Ingen automatisk klassifisering.

Før staging: eksakt merget/grønn kode/image, kun 0035 forward i migrasjonsplanen,
backup/verify/isolert restore, bevart miljø/media/static/safety og konkret gammel
API/image-rollback. Bevar imports/exports før recreate dersom de finnes. API-only;
ingen infra-/Compose-oppgradering, prune, live restore eller schema-reverse.
Schema-apply utføres eksplisitt; standard migrate/collectstatic-start brukes ikke
som preflight. Etterpå: tabeller tomme, constraints/triggere til stede, plan tom,
effektiv/varig gate av, legacydata og teknisk API/admin/PUBLIC-lesing bevart.
Publiser faktisk sanitert evidens separat etter kode-merge/main-CI. Ingen rå
notat-/taggtekst, profil-PK/hash, credentials eller rå exceptiontekst i Git/logg.

## Anbefaling – ikke bestilt dataflytting

Senere flytting bør være en separat operatørstyrt, planbundet og auditiert
kopiering til profilens egen eksisterende legacyassignment, uten konvertering av
NULL/tom/tekst. Friskt inventar og eksakt kilde-/målkontroll før apply; preeksisterende
overlayrad skal gi eksplisitt konflikt, aldri blind overskriving. NULL-profiler og
manglende assignments forblir legacy til separat godkjent løsning. Ikke kopier
notatet til andre tenants selv om flere assignments finnes. Ingen sletting av
legacyfelt i første flytting. Autoritetsovergang må bestilles separat med samtlige
aktive writes, private lesere/søk, membership/avtale/capability/audit og rollback.

Legacytags krever eierbeslutning om mappingprosess: (A) eksplisitt redaksjonell
mapping per legacytagg/kobling til shared editorial eller private internal, eller
(B) hold alle legacytags utenfor shared/PUBLIC-cutover inntil mapping er godkjent.
B er en anbefalt sikker overgang, ikke automatisk privatklassifisering. Samme
tekst/tenant/publisering er ikke klassifiseringsbevis; delvise/motstridende
koblinger må kunne deles eller avvises eksplisitt. Ingen privat-tagmodell er bygd.

Inventarkoden ligger i `ops/staging/inventory-tenant-notes.py`, uten ny API eller
managementkommando. Den krever forventet database og eksternt verifisert SHA som
argumenter; kjør som eksplisitt Python-prosess i reviewet API-image med repo-root
som arbeidskatalog/PYTHONPATH. Den importerer bare shadowens scopekonstanter og
identitetsvalidator, aldri målefunksjonen. Notatkategorier beregnes i SQL, slik at
selv operatørprosessen ikke laster rå notattekst. Feil gir bare INCOMPLETE og exit 4;
ingen retry/reparasjon. Manglende assignment på en NULL-profil rapporteres som
forutsetning, ikke automatisk korrupsjon eller tillatelse til opprettelse.

## Lokal validering før PR

18 målrettede tester på isolert Docker/PostgreSQL 16 bestod, inklusive additiv
forward/tom reverse/forward, reverseavvisning ved semantisk state, ORM-omveier,
FK/unikhet/identitetsvern, tapfri notatlagring, legacy API/admin/import/M2M/AI og
inventarets dekning/sanitering/scope/read-only-avvisning. En samlet kjøring med de
første 14 av disse og 165 eksisterende 6A-, shadow-, tenant-, kontakt-/relasjons-,
PUBLIC-, legacyimport-/telefon-/bildekontrakttester bestod (179 totalt). De fire
nye inventartestene bestod deretter sammen med de 14. `makemigrations --check
--dry-run` fant ingen manglende migrasjoner. Eksisterende reverse-test i 6A.2 er
isolert i en ytre transaksjon, slik at dens forventede 0034-avvisning ikke
etterlater nyere tomme tabeller reversert. Ingen backfillruntime er endret.
