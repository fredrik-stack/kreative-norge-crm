# Operatørbasert PK-leseshadow

**Mandat:** Eiergodkjent 2026-10-23. ADR-011 migreringstrinn 6 konkretiseres etter
fullført 6A.3. Ett sammenhengende mandat omfatter separat arbeidsflyt-PR, separat
kode-PR, nødvendige tester, draft PR, faktisk separat skrivebeskyttet review,
retting/retest/re-review, ordinær merge, main-CI, betinget stagingdeploy og
operatørmåling, samt separat reviewet/merget sanitert evidens. WORKFLOW.md styrer
leveransen. Ingen ny produkt-ADR eller neste produktetappe inngår.

**Leveransestatus:** Kode-/review-/merge-/CI-status følger leveranse-PR-en.
Stagingdeploy og faktisk måleresultat skal dokumenteres separat; lokal test er
ikke stagingbevis. Gaten er default-off og skal være av i varig sluttstate.

## Scope og målekontrakt

Domain er eksakt `1 / musikkontoret / Musikkontoret`. Eksakte tenants:

| ID | Slug | Navn |
| ---: | --- | --- |
| 1 | musikkontoretnord | Musikkontoret Nord |
| 2 | musikkontoretmxst | Musikkontoret MØST |
| 3 | musikkontoretbrak | Musikkontoret Brak |
| 6 | musikkontoretoks | Musikkontoret ØKS |
| 7 | musikkontoretsorf | Musikkontoret SØRF |
| 8 | musikkontoretstar | Musikkontoret STAR |
| 9 | musikkontorettempo | Musikkontoret Tempo |

Identiteter, bindinger og hele domainets tenantsett må stemme. Ingen navnegjetting,
scopeutvidelse eller global fallback. For hver tenant og hver av Organization og
Person beregnes distinkte eksisterende profil-PK-sett:

- L: alle profiler med legacy `tenant_id=t`, uansett domainbinding.
- U: profiler i L med NULL-domain.
- B: profiler i L med eksakt domain d.
- A: selvstendig profilutvalg med domain d og assignment til t, der assignmentens
  tenant også har domain d. A begrenses aldri til L eller profilens legacytenant.

Eksakte settdifferanser beregnes i minnet. Lik telling alene er ikke likhet.
Begge profiler i uavklarte kandidatpar bevares; ingen signalbasert deduplisering.
128 aktører / 157 personer er historiske 6A.3-observasjoner, ikke nye testgrenser.

Profilpoolen er alle profiler med legacytenant i tenantsettet ELLER domain d.
Alle assignments til en godkjent tenant ELLER til profilpoolen undersøkes med
endpointopplysninger før ugyldige rader filtreres bort. Hver bundet profil skal
ha nøyaktig én assignment til egen legacytenant. NULL-profiler skal ikke ha
assignments. Feil ikke-NULL domain er et strukturavvik. Ekstra/manglende/feil
assignments og scopeavvik kan aldri forklares som NULL-dekning.

## Status og exitkoder

| Status | Exit | Betydning |
| --- | ---: | --- |
| FULL_EQUAL | 0 | Alle 14 sammenligninger fullført; L=A, U tomt, ingen avvik |
| EXPLAINED_PARTIAL | 2 | Alle fullført; minst én U ikke tom; L−A=U, A−L tomt og B=A overalt; ingen andre avvik |
| FAILED | 3 | Fullført måling med andre PK-/strukturavvik |
| INCOMPLETE | 4 | Gate av, feil scope/database/kontekst, avvist transaksjon/backend, avbrudd, timeout eller annen målefeil |

EXPLAINED_PARTIAL er uttrykkelig tillatt som korrekt delresultat av prosjekteier.
Det er ikke full dekning eller cutovergodkjenning. Ingen catch-up kjøres eller
bestilles automatisk. FULL_EQUAL krever ikke null duplikatkandidater eller
retting av de to historiske telefonavvikene.

Maskinlesbar JSON kommer på stdout. Ved ikke-null status kommer bare en fast
status på stderr. Argumentfeil gir fast `INVALID_ARGUMENTS` og exit 4 uten å
ekko argumentverdier. `--traceback` ignoreres av CLI-wrapperen slik at både sanitering og faste exitkoder bevares.
Faste reason codes omfatter `GATE_DISABLED`, `INVALID_CONTEXT`,
`POSTGRESQL_REQUIRED`, `OUTER_TRANSACTION`, `DATABASE_MISMATCH`, `SCOPE_MISMATCH`,
`SNAPSHOT_MISMATCH`, `INTERRUPTED`, `MEASUREMENT_ERROR` og PK-/strukturkodene i
rapporten. Antall avvik per kode er kontrollbrudd, ikke nødvendigvis distinkte profiler.

## Snapshot, sanitering og begrensninger

Hele datalesingen bruker samme forbindelse og ett `REPEATABLE READ READ ONLY`
PostgreSQL-snapshot. Avvis ytre transaksjon og avslått autocommit. Statement
timeout er 30 s, lock timeout 2 s, transaksjonslokalt. Start/slutt verifiserer
samme snapshot, isolation og read-only. Alle resultater materialiseres innen
transaksjonen; en sen feil publiserer INCOMPLETE med null fullførte sammenligninger.
Ingen eksplisitte rad-/tabellåser, midlertidige tabeller, sekvens-/data-/schemawrites,
skriverstans, automatisk retry eller reparasjon inngår.

Bare målingsversjon, kodereferanse, miljø/database/snapshot/tid, godkjent
domain-/tenantscope, modell, aggregater og faste avvikskoder rapporteres. Ingen
profil-PK-er/-hashverdier, profilnavn, kontaktdata, notater, SQL-parametre eller
rå exceptiontekst lagres i rapport/logger. Tjenesten logger ikke rå feil.

Legacyutvalget svarer til tenantpredikatet i OrganizationViewSet.get_queryset og
PersonViewSet.get_queryset. Aktive views er urørt. Editor-filtre ligger i
frontend. PK-samsvar beviser ikke API-respons, relasjoner, kontaktpublisering,
sortering, paginering, PUBLIC eller framtidig shared autorisasjon. Ingen
request-hook, signal, startupjobb eller ny brukeradgang er innført. Legacylesing
er autoritativ uansett operatørgate. UX v6 revisjon 4/O-24, godkjent 5E og
Google Maps-aktørkart i Editor og PUBLIC videreføres.

## Kjøring og kodebinding

Standard API-start kjører migrate/collectstatic og skal ikke brukes som
skrivebeskyttet preflight. Bruk eksplisitt kommando i eksisterende verifisert
runtime. Før kjøring kontrollerer operatøren miljø, faktisk image/kode og at
kodereferansen er reviewet, merget og CI-grønn. `--code-baseline` er denne
eksternt verifiserte SHA-en; kommandoen kontrollerer format, ikke Git-/imageproveniens.
Databaseidentiteten kontrolleres derimot i selve målesnapshotet.

```bash
SHARING_DOMAIN_SHADOW_ENABLED=True python manage.py compare_domain_reads \
  --environment staging \
  --expected-database postgresql:7621672066239828005:crm_db \
  --code-baseline <verifisert-40-tegns-merge-SHA>
```

I Docker gis gaten bare med `docker exec -e SHARING_DOMAIN_SHADOW_ENABLED=True`
til den avgrensede operatørprosessen. Ikke skriv den til `.env.staging`, og ikke
aktiver den i Gunicorn/API. Gate av avviser før shadowlesing. Ukjent boolverdi
gir False via eksisterende fail-closed parser. `local` og `test` er også tillatte
miljøetiketter, med deres egne ferskt kontrollerte databaseidentiteter.

Stopp ved å avbryte/lukke operatørprosessen og dens lesetransaksjon. Ingen
data-/schema-rollback eller assignmentendring er nødvendig. Ingen blind retry;
ny måling etter en feil krever dokumentert årsak og korrigert grunnlag.

## Betinget stagingmandat og sluttpunkt

Kode-PR-en skal være separat reviewet, ordinært merget og ha grønn nødvendig
main-CI før staging. Kontroller hele runtimeforskjellen fra faktisk staging,
eksakt databaseidentitet ovenfor, tom migrasjonsplan, backup-/bevaringsporter og
konkret API/image-/konfigurasjonstilbakeføring. Sikre eventuelle import-/eksportfiler
i containerlaget før recreate. Bevar mounts, media, static og aktive bilde-/safetyflagg,
ledger og deny-state. Bare nødvendig API-deploy/recreate er autorisert; ingen
infrastruktur-/Compose-oppgradering, prune, live restore eller schema-reverse.

Etter deploy: verifiser målimage/kode og relevant API/PUBLIC/driftshelse;
bevis gate av; kjør fullmåling med prosessavgrenset gate; bevis fortsatt gate av
i ordinær API og varig konfigurasjon. Publiser sanitert evidens i separat
dokumentasjons-PR med samme review-/merge-/CI-krav. Denne dokumentasjonsmergen
utløser ingen ny deploy. Rapporter kode-PR/deployimage separat fra dokumentasjons-PR/main.

Reelle data-/scopeavvik avslutter målingen trygt, med avslått sluttstate og
eskalering uten dataretting. Konkret feil i ny målekode kan rettes gjennom samme
test-/review-/mergeflyt innen mandatet. Nødvendig menneskelig innlogging eller
produktvurdering som ikke kan erstattes teknisk er en reell stoppgrunn.

Sluttpunkt: arbeidsflyt varig oppdatert, kode reviewet/merget, staging teknisk
kontrollert, måling korrekt klassifisert, gate av og evidens reviewet/merget.
Ingen deduplisering, telefonretting, assignment, backfill/catch-up, shared
reader/writer, overlays, PUBLIC-/image-home-cutover eller neste etappe inngår.
Hele 6A og framtidig delt tilgang erklæres ikke ferdig.

## Lokal kodeverifikasjon 2026-10-23

Isolert lokal PostgreSQL 16 i egen Docker-container: 21 nye målrettede tester
bestod, inklusive alle 14 kombinasjoner/tomme sett, like antall/ulike PK-er,
manglende/ekstra assignments, syntetiske umulige domainbrudd uten svekket DB-vern,
NULL-deldekning uten writes, ekte samtidig profiloppretting, read-only-avvisning,
ytre transaksjon/autocommit av, ekte statement-timeout, gate av/på, sanitering
og uendret API uten shadowstart. 130 relevante eksisterende regresjoner for
tenantgrenser, kontakter/relasjoner, PUBLIC, import/telefon og bildeprojection/
serving bestod. `makemigrations --check --dry-run` ga ingen endringer.
Relative dokumentlenker og `git diff --check` bestod. Eksisterende OpenAPI-
serializeradvarsler opptrådte i regresjonssuiten; testene bestod. Dette er
syntetisk lokal test, ikke en stagingmåling eller ny datagodkjenning.

Separat review av første kodehead fant at Djangos globale `--traceback` kunne
endre ikke-null CLI-exitkoder til 1. CLI-wrapperen er rettet, og faktisk
subprocess-kjøring bekrefter exit 2/3/4 og fast stderr også med dette flagget.
Alle 21 målrettede tester bestod etter rettingen. De 130 uendrede eksisterende
regresjonene ble ikke gjentatt for denne isolerte wrapperrettingen.
