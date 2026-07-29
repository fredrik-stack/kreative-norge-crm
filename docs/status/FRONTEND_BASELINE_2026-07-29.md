# Frontend- og stagingbaseline 2026-07-29

**Status:** Fase 1 gjennomført

**Autoritativ nåstatus:** [PROJECT_STATUS_CURRENT.md](PROJECT_STATUS_CURRENT.md)

Denne rapporten lagrer den daterte evidensen fra den skrivebeskyttede fase 1-kontrollen. Den inneholder ikke direkte servermål, kontaktverdier eller skjermbilder.

## Git og serverrepo

- GitHub og lokal `main`: `f6f03d67ba0c5d3afbe258fb356248e7075c4b49`
- lokal arbeidsmappe: ren og 0 foran / 0 bak
- staging-repo: rent på `ea8b8762aecdff760728139b1659f7d3a43445c7`
- staging-repoets lokale `origin/main`: samme eldre SHA, fordi kontrollen med hensikt ikke kjørte fetch eller pull på serveren
- forskjellen fra staging-repo til dagens `main` bestod av dokumentasjon, skills og prosjektstyringsfiler; kontrollerte runtimefiler hadde samme innhold

## Images og containere

- API-koden var bakt inn i imaget, ikke bind-mounted
- innebygd Git-metadata og målrettede filhashes knyttet API-imaget til staging-repoets SHA
- frontend og nginx-konfigurasjon var bakt inn i web-imaget
- web-imaget manglet commitlabel, så eksakt Git-commit kunne ikke bevises fra metadata alene
- alle tre containere kjørte uten registrerte restarter
- Django system check rapporterte ingen problemer
- PostgreSQL readiness var grønn

## Frontend og leveransekjede

| Ressurs | SHA-256 |
|---|---|
| JavaScript-bundle | `d57b7e1c140bca5145488a9a1306c13bbc139022c3e02f75bbc523ecf1a74f2b` |
| CSS-bundle | `57ee324612daffdd58749f028ce7c7115368c378554db424edb54c2af16e35bf` |

Hashene var identiske i:

1. en isolert ren build fra dagens `main`
2. kjørende web-container
3. HTTPS-responsen fra staging

Cache-busting ga de samme filene. Lastet nginx-konfigurasjon matchet repoet, Caddy var aktiv, og Cloudflare leverte gjeldende bundleinnhold. Det ble ikke funnet tegn på gammel proxy- eller edge-cache.

## Visuell baseline

- PUBLIC ble kontrollert på desktop og mobil
- autentisert Editor ble kontrollert
- Editor-forsiden er godkjent designreferanse
- observerte avvik i aktørkort, lange stedsnavn, thumbnails og PUBLIC-tagfarger finnes også i dagens `main` og er lagt til fase 3
- generell formtetthet, sticky lagring, personkoblingsdesign og persontabell er lagt til fase 5
- ingen av disse avvikene ble rettet i fase 1

## Datagrunnlag for fase 2

Det konkrete undersøkelseseksemplet hadde verdi i direkte `Person.phone`, men manglet en `PersonContact` av type `PHONE`. Bare en e-postkontakt var lagret. Ingen kontaktverdi er gjengitt her.

Editor-baselinen viste at offentlig e-post, offentlig telefon, publisering av ny person og publisering ved kobling av eksisterende person var forhåndsvalgt. Dette er fase 2-avvik mot personvernstandarden i ADR-005.

## Endringstilstand

Fase 1 endret ikke:

- kode eller dokumentasjon under selve kontrollen
- staging- eller produksjonsdata
- publiseringsflagg
- images, containere eller tjenester
- cache, DNS eller Cloudflare
- deployoppsett

Automatisk staging-deploy er fortsatt planlagt og ikke implementert.
