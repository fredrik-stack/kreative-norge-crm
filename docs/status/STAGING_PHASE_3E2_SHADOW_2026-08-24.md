# Fase 3E.2 – staging projection/API shadow 2026-08-24

**Status:** `CLOSED / SHADOW VERIFIED`; `PUBLIC_IMAGE_PROJECTION_ENABLED=True` bare i ignorert stagingkonfigurasjon; `PUBLIC_IMAGE_API_SCHEMA_ENABLED=False`; PUBLIC HTML/API bruker fortsatt legacybilder; 3E.3 er ikke startet

## Leveransegrunnlag

- start-`main`: `f155d6fd2b643e556616aa746186d96b1e2f9edb`
- implementerings-PR: #47
- separat reviewet PR-head: `415a51be1e949fdc94b5d0c8889e7ea627866581`
- implementeringsmerge og eksakt deployet SHA: `90ff5e96f5370c22546d378234cc0ac219b71ec1`
- siste PR-CI: run `32702012873`, alle åtte jobber grønne
- post-merge CI: run `32702322719`, alle seks jobber grønne
- post-merge image-workflows: runs `32702322707` og `32702322742`, begge grønne
- ingen database-migrasjon; staging forble på `crm.0029_release_selection_revision_gate`

PR-reviewen hadde `0 BLOCKER`, `0 HIGH` og ett rettet `MEDIUM`: list-endepunktet prefetch-et først projectiongrafen i shadow selv om schema var av og listen ikke beregnet projection. Prefetch skjer nå bare når target-schemaet er eksplisitt aktivert; fullkatalog-shadow går gjennom auditkommandoen. Den eldre image-spike-workflowen ble samtidig oppdatert til faktisk produksjonsstatus: Pillow er en legitim 3C-runtimeavhengighet, mens spike-moduler og pyvips fortsatt ikke lekker inn.

## Backup og deploy

Før deploy ble backup `kreative-norge-staging-20260824T074240Z` tatt. Jobben hadde `Result=success` og `ExecMainStatus=0`; full repository-/arkivverifikasjon og isolert restore-smoke av samme arkiv var grønne. Stagingrepoet var clean på `38663b532de64eb15b5ec6579dbb7d66a0eb18fe` og ble fast-forwardet til eksakt merge `90ff5e9`. API-imaget ble bygget før bare API-containeren ble stoppet, fjernet og opprettet på nytt. Database, web, volumer, ledger og media ble ikke rekreert eller slettet.

Begge nye gater var først eksplisitt av. Django-check var grønn, migrasjonsnivået uendret, og `collectstatic` la de tre tekniske fallbackfilene i shared static-volum med repositoryhashene:

| Variant | SHA-256 |
| --- | --- |
| square | `25c2487570c3ab1e3d84d80eda894329171028c8a608f3e5f64f44d1243d325e` |
| landscape | `3cc8c5d08b473d2e114a9d01324f5a422ca9665dd336fd3f29f231d370598df8` |
| share | `1afe1d0624a9e374ab0deb749a65b8852a227c8423848a5579dea516c799d958` |

## Baseline med projection og schema av

Før og etter deploy var public API-listen og representativ detail byte-identiske:

- list: `83770235b9aa5ba256ab3433d1935697615698e28aad3111f6bda5c2b02575ca`
- detail: `8b574e22c88fab8e2c6c5e9794a79b528e04f4ccbda21ca313b7898f3ac44179`
- publisert antall: `122`
- `image` manglet i både list og detail
- legacyfeltsettet var uendret

PUBLIC HTML var semantisk identisk. Råhashen varierer fordi den eksisterende viewen eksplisitt bruker `random.shuffle(tags)` for tag-pille-rekkefølgen; kontrollen sammenlignet samme tagmengde og resten av normalisert HTML eksakt. Ingen bilde- eller markup-cutover fant sted. Editor-session, PUBLIC og API svarte `200`. Controlled media svarte fortsatt `200` på HEAD.

Aktivt OpenAPI-schema beholdt `image` av og hadde én canonical list-/detail-operasjon. Den tilsiktede routekonsolideringen endret detail-parameteren fra den gamle interne `{pk}`-beskrivelsen til `{org_number}` uten å endre URL-en eller responsekontrakten.

Før aktivering var safety-ledgeren `READY` med event/read/anchor cursor `7`. PostgreSQL hadde `122` publiserte organisasjoner, `8` selections, `2` releases og `6` release-mappinger. Delivery-rooten hadde `6` filer med samlet manifest-hash `fb94a3023614361f4157b0a5a82a145ef81c983f3e05ac1e4cf1afb0fa07c7a9`.

## Fullkatalog-shadow

Bare `PUBLIC_IMAGE_PROJECTION_ENABLED=True` ble aktivert i den ignorerte stagingfilen. `PUBLIC_IMAGE_API_SCHEMA_ENABLED=False`, materialisering og controlled serving forble i sine tidligere verifiserte states. `audit_public_image_projection` ga:

```json
{"asset":1,"authorize_count":3,"legacy_preview_different":122,"legacy_preview_equal":0,"legacy_thumbnail_different":122,"legacy_thumbnail_equal":0,"no_release":5,"published_organizations":122,"query_count":5,"reasons":{"asset":1,"no_active_selection":116,"release_missing":5},"runtime_ms":227.799,"safety_unavailable":0,"scope_mismatch":0,"system_fallback":121}
```

Forskjellene mot legacy er forventet i shadow: projection bruker enten controlled release eller teknisk systemfallback, aldri legacybilde. Audit gjorde fem faste DB-queries og tre safety-authorizations for den ene asset-releasen; den skrev ingen identiteter, URLs eller keys.

Den publiserte ACTIVE releasen `df8efd43-027c-434b-9b0b-5633bb9bea78` ga `kind=asset`, tre authorize-kall, nullable credit `null` og den godkjente altteksten. Variantene var:

- square: `512 × 512`
- landscape: `800 × 450`
- share: `1200 × 630`

Alle tre projected URL-er brukte `https://staging.northernsound.no/media/releases/<release-id>/...` og svarte `200` på HEAD gjennom 3E.1C-controlled serving.

En publisert aktør uten aktiv selection ga `kind=system_fallback`, `reason=no_active_selection`, blank teknisk alttekst og nullable credit `null`. Alle tre versjonerte static fallback-URL-er svarte `200` på HEAD. Den eksisterende upubliserte 3E.1B-aktøren ga `kind=system_fallback`, `reason=organization_unpublished` og inngikk ikke i public queryset. Safety-unavailable og alle negative authorizationkategorier ble brukt fra automatiserte integrationtester; broen ble ikke stoppet bare for kosmetisk livebevis.

## Uendret respons, state og ytelse

Med shadow på og schema av var API list, representativ detail og OpenAPI byte-identiske med off-baselinen. `image` kom ikke med, og `thumbnail_image_url`/`preview_image_url` beholdt legacyverdiene. PUBLIC var igjen eksakt lik etter normalisering av den tilsiktet tilfeldige tagrekkefølgen. Editor-session svarte `200`, og shadowloggen var til stede uten URL, release-ID, filesystempath, repository, credential eller secret.

Representative målinger:

- detail: `39,804 ms` med projection av og `40,216 ms` med shadow på
- list: målinger mellom `0,630` og `1,479 s` både før og etter; list-requesten gjør ingen projection-prefetch eller bridgekall når schema er av
- fullkatalog-audit: `227,799 ms`

Request-shadowen ble derfor stående på. Fullkatalogmåling forblir en eksplisitt auditkommando.

Etter GET/audit var safety fortsatt `READY` på cursor `7`; radantallene var fortsatt `122/8/2/6`; delivery hadde fortsatt seks filer og samme manifest-hash. Ingen database-, ledger-, release-, selection-, delivery- eller backupstate ble mutert.

## Rollbackbevis

Første samlede gatekjøring traff et operatørverktøyavvik: serverens Docker Compose 1.29.2 støtter ikke `logs --since`. Dette var ikke en applikasjons- eller shadowregresjon. Gate-trapen satte umiddelbart begge nye flagg av og rekreerte bare API. Den første automatiske curlen kom før Gunicorn var klar og fikk `502`; etter readiness var API grønn og list-responsen byte-identisk med off-baselinen. Gateverktøyet ble deretter korrigert til `logs --tail` og robust HTTP-ready-retry, projection ble aktivert på nytt, og hele gaten bestod.

Dette beviser at primær rollback er projection/schema av og API-only recreate uten å endre 3E.1A–3E.1C, releases, ledger eller media.

## Sluttilstand

```text
3E.1A ACTIVE
3E.1B ACTIVE
3E.1C ACTIVE
3E.2 CLOSED / SHADOW VERIFIED
PUBLIC_IMAGE_PROJECTION_ENABLED=True   # bare ignorert stagingverdi
PUBLIC_IMAGE_API_SCHEMA_ENABLED=False
PUBLIC HTML/API image contract=legacy
3E.3=NOT STARTED
```

Kode- og eksempelstandard for begge 3E.2-flagg forblir `False`. Target-`image`-schema, projectionbaserte aliaser i live response, PUBLIC cards/detail, Open Graph/Twitter, canonical image metadata, endelig fallbackgrafikk/-alttekst og formell takedown er ikke aktivert.
