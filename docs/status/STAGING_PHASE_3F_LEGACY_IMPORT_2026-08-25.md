# Staging – fase 3F legacyovergang og typed Import-bildekontrakt 2026-08-25

**Status:** `CLOSED / VERIFIED`

## Kontrollpunkt

- Implementerings-PR: #54
- Endelig reviewet head: `56dae73d5e38e2b020ba1d5bcfdb99dbc46d0d6b`
- Deployet merge: `438a4800ded325fdf1ba99acc3d03812fb9ef1e9`
- PR-CI: run `32786625088`, 6/6 grønn
- Post-merge-CI på `main`: run `32787223617`, 6/6 grønn
- Migrasjon: `0031_import_image_decision_contract`
- Predeploy-backup: `kreative-norge-staging-20260824T230354Z`, full repositoryverifikasjon og isolert restore grønn
- Postdeploy-backup: `kreative-norge-staging-20260824T231112Z`, full repositoryverifikasjon og isolert restore grønn

PR #54 fikk separate frozen-head-reviews. Reviewen fant og lukket idempotent retry uten full scopekontroll, manglende immutable snapshots, en signed-legacyref som ikke revaliderte permanent legacyguard, destruktiv migrasjonsreverse og offentlige ORM-managerveier rundt den typed insert-tjenesten. Endelig fullreview på eksakt head ga `0 BLOCKER`, `0 HIGH`, `0 MEDIUM` og `0 LOW`.

## Deploy og aktiv konfigurasjon

Staging startet rent på `087026e7e8bb43f9619c605e75f538976c6f1566`. Førstaten hadde migrasjoner til `0030`, alle sju 3E-flagg aktive bare i ignorert stagingkonfigurasjon og ingen 3F-innstilling i den eldre koden. Serverrepoet ble fast-forwardet til eksakt merge `438a480`; API- og web-images ble bygget fra denne commiten, og bare API/web ble erstattet. PostgreSQL-containeren og volumes ble ikke rekreert.

Compose 1.29.2 traff den kjente `ContainerConfig`-feilen ved første in-place recreate. Begge images var ferdigbygget, databasen var urørt, og avviket ble håndtert ved eksplisitt stop/remove/recreate av bare API- og web-containerne gjennom `docker-compose.staging.yml`. Django systemcheck var deretter grønn, og migrasjon `0031` var anvendt.

Sluttkonfigurasjonen er:

```text
IMAGE_ASSET_FEATURE_ENABLED=True
PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=True
PUBLIC_IMAGE_SERVING_ENABLED=True
PUBLIC_IMAGE_PROJECTION_ENABLED=True
PUBLIC_IMAGE_API_SCHEMA_ENABLED=True
PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=True
PUBLIC_IMAGE_TAKEDOWN_ENABLED=True
IMPORT_IMAGE_DECISIONS_ENABLED=False
```

3F-gaten ble midlertidig satt `True` bare under den isolerte typed-kontraktgaten og deretter satt tilbake til `False` med kontrollert API-recreate. Shared staging avsluttet med gaten av fordi Import 2.0-review-UX ikke er aktiv. Kode- og eksempelstandarden er også `False`.

## Additiv migrasjon og legacyinventar

Før og etter migrasjonen var eksisterende importstate identisk:

```text
ImportJob=53
ImportRow=1504
ImportDecision=2619
ImportImageDecision=0
typed ImageReviewEvent-binding=0
```

Ingen gammel jobb, rad eller generisk beslutning ble backfillet. Isolerte migrasjonstester beviste både tom reverse før første typed write og `IrreversibleError` før schemaendring etter første typed beslutning.

`audit_legacy_image_sources --json` ble kjørt to ganger med byteidentisk aggregert output og SHA-256 `a050bb8f7d084522487b69c5ff389505ff25b04f28bf8ab0a409900ab452ae22`. Kommandoen gjorde ingen database-, storage- eller ledgerwrite og brukte ingen DNS/HTTP. Den aggregerte førstaten var blant annet:

```text
organizations_total=128
organizations_published=122
organizations_unpublished=6
organizations_with_legacy_url=108
organizations_with_multiple_legacy_urls=53
organizations_with_duplicate_field_urls=39
organizations_blocked_by_legacy_guard=1
organizations_with_active_typed_selection=8
organizations_with_public_release=1
credential_or_signed_url_suspicions=0
favicon_derived_urls=0
syntactically_invalid_legacy_urls=0
```

Ingen detaljmodus ble lagret i deployloggen.

## Gate av og no-network

Med `IMPORT_IMAGE_DECISIONS_ENABLED=False` besto sju målrettede tester i en isolert database på det deployede stagingimaget. De beviste:

- ordinær Organization create/update uten automatisk Open Graph-refresh eller bildefetch
- legacyfeltene som read-only i vanlig API-write
- eksisterende importmodi og update-commit uten implicit bilde-I/O
- lokal, deduplisert og signert legacykandidatlisting uten fetch, preview, processing eller write
- filtrering av sensitiv, ugyldig og favicon-avledet legacykilde
- fail-closed blokkering av typed beslutningsoppretting når gaten er av

Den separate legacygruppen kan dermed lese dedupliserte DB-kandidater, mens bare et eksplisitt brukerklikk går videre til den eksisterende kontrollerte previewruten. Ingen vanlig CRUD-, listing- eller importbane gjorde Brave-, Open Graph-, DNS-, HTTP-, decode-, render-, materialiserings-, release-, publish- eller legacyfield-write.

## Typed kontrakt med gaten på

Bare 3F-gaten ble midlertidig aktivert; `IMAGE_ASSET_FEATURE_ENABLED` og `PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED` var fortsatt `True`. Hele `Phase3FImportImageDecisionTests` besto 18/18 mot en isolert stagingdatabase. Gaten beviste:

- implicit og eksplisitt `KEEP_LOCKED_IMAGE`
- `SET_APPROVED_IMAGE`
- `USE_APPROVED_FALLBACK`
- canonical actor-snapshot og revalidering av lagret snapshot
- eksakt expected selection/revisjon og fail-closed stale actor/selection
- tenant-/capabilityscope og wrong-tenant-avvisning også ved retry
- fryst approvaltekst, full renditionoppskrift og konkrete artifact-snapshots
- checksum-deny og utilgjengelig safety som fail-closed
- append-only én-til-én-binding til anvendt `ImageReviewEvent`
- idempotent retry uten duplikat selection/event
- ORM-immutability gjennom base/default manager og instance writer-ruter
- import-commit uten fetch/decode/render/materialisering/release-I/O eller endret publiseringsstate

De syntetiske radene levde bare i testdatabasen, som ble fjernet etter testen. Live staging fikk derfor ingen kunstig ImportImageDecision; dette samsvarer med den avsluttende default-off-gaten og fraværet av Import 2.0-review-UX.

## 3E-, PUBLIC- og denyregresjon

Etter at 3F-gaten var satt tilbake til `False`, var live database- og runtime-state uendret:

```text
assets=10
rendition_sets=13
renditions=39
selections=11
review_events=11
formal_takedowns=1
releases=4
release_mappings=12
ImportImageDecision=0
typed ImageReviewEvent-binding=0
```

Fullkatalogauditen var før og etter:

```text
published=122
asset=1
system_fallback=121
query_count=5
authorize_count=3
safety_unavailable=0
scope_mismatch=0
```

Faktiske stagingforespørsler ga `200` for public API list, asset-detail, PUBLIC list og canonical asset-detail. Tre target-/PUBLIC-/denyregresjoner var grønne i isolert testprosess. Første testkommando fikk forventet `301` fra stagingens globale HTTPS-redirect; den ble kjørt på nytt med redirect deaktivert bare i testprosessen, uten shared configendring. Den permanent denied gamle release-URL-en ga fortsatt `404` med `Cache-Control: no-store`.

Safety-ledgeren forble `READY` med ledger-ID `934fa373-111f-4192-9e13-6483041232d5`, cursor `13` og uendret ankret 3E.4-head. Delivery besto av de samme ni filene med manifest:

```text
ac91c567897bee1a79bf6146811c98ea550f3c2776c42cd52376aa7be2b475dc
```

3F endret dermed ikke aktiv API/PUBLIC/head-projection, release-/deliverystate eller permanent denyhistorikk og reaktiverte ingen blokkert legacykilde.

## Restore, orphan og backup

Den isolerte older-DB/media-testen brukte en ekte schema-v2 safety-ledger gjennom Django. Den beviste at nyere checksum-/release-deny fortsatt vinner over en eldre PostgreSQL-selection og en fysisk restaurert originfil, at deny-retry fjerner den restaurerte filen uten å flytte ledger-head, og at sikker republisering krever ny source checksum, selection, release-UUID og keys.

Postdeploy-backupen `kreative-norge-staging-20260824T231112Z` omfatter den migrerte `0031`-staten og de aktive mediaområdene. Full repository-/archive-data-verifikasjon og isolert PostgreSQL/media-restore fullførte grønt. Den tidligere predeploy-backupen `kreative-norge-staging-20260824T230354Z` var også fullverifisert og isolert restore-verifisert.

`cleanup_image_storage_orphans` ble kjørt bare i dry-run med 24 timers minstealder:

```text
image_originals_private: referenced=10, storage=10, eligible=0, young=0
image_renditions_public: referenced=39, storage=39, eligible=0, young=0
deleted_files=0
```

Ingen fysisk cleanup, generell retensjon eller provider-/CDN-purge ble kjørt.

## Sluttstatus og stoppunkt

Fase 3F er `CLOSED / VERIFIED`, og dette avslutter fase 3. De additive legacyfeltene og API-aliasene beholdes gjennom stabiliseringsperioden; 3F-gaten forblir av i shared staging til en senere Import 2.0-review-UX har en egen godkjent leveranse.

Arbeidet stopper før Import 2.0-produkt-/review-UX, telefon-ADR og fase 4, fysisk legacyfeltdropp, generell release-retensjon og providerpurge. Disse områdene er ikke aktivert eller implementert av 3F-gaten.
