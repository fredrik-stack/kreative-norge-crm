# Changelog

Dette dokumentet samler større brukermerkbare og arkitekturelle endringer. Små kosmetiske justeringer trenger ikke registreres.

## 2026-07-29

### Verifisert staging- og frontendbaseline

- fullført fase 1 med skrivebeskyttet kontroll av lokal/GitHub `main`, staging-repo, kjørende Docker-images og containere, nginx, Caddy, frontendbundles og HTTPS-/cachekjeden
- bekreftet at kjørende JavaScript- og CSS-bundles matchet en ren build fra dagens `main`, og at proxy eller Cloudflare-cache ikke var årsak til observerte frontendavvik
- kontrollert PUBLIC på desktop/mobil og en autentisert Editor-visning; Editor-forsiden er godkjent designreferanse
- fordelt gjenstående kort-, bilde-, tag-, overflow- og formavvik til fase 3 og fase 5
- bekreftet at ingen kode, data, publiseringsflagg eller deploy ble endret under fase 1

### Fase 2: telefon, publiseringsstandarder og offentlig tittel

- utvidet `repair_person_contacts` bakoverkompatibelt med eksplisitt telefonmodus, tenant-filter, trygg dry-run og privat oppretting; konflikter rapporteres og den berørte posten hoppes over uten automatisk endring
- beholdt eksisterende e-postmodus som standard og lot eksisterende kontakt- og publiseringsflagg være urørt
- gjort publisering av ny e-post, ny telefon, ny kontaktperson og ny eksisterende personkobling avslått som standard i Editor og nullstilt ved faktisk aktør- eller tenantbytte
- tydeliggjort forskjellen mellom offentlig personvisning og offentliggjøring av en konkret kontaktkanal
- lagt `Person.title` additivt til aktivt public API og PUBLIC HTML når feltet har verdi
- utvidet backend-, frontend- og Playwright-regresjonstester uten schema-migrasjon eller data-apply utenfor testdatabasen

## 2026-07-28

### Arbeidsflyt og produkt-roadmap

- merged PR #10 og fullført den repo-baserte session-workflowen med `ADR-006`, `$start-arbeidsokt`, `$avslutt-arbeidsokt`, `$fortsett-prosjekt` og totalt 15 validerte skills
- ryddet autoritativ dokumentasjon ved å holde gamle rotbaserte handoff-, `REFERENCE`- og `STATUS`-filer utenfor repoet og ignorere genererte Playwright-resultater
- godkjent revidert produkt-roadmap med staging/frontend-baseline først, deretter liten kontaktstabilisering, robust bildearkitektur, Import 2.0-design, langsiktig kontaktarkitektur, Import 2.0-implementering og eksport
- integrert AI som et gjennomgående produktprinsipp for bildevalg og importstøtte, uten automatisk overskriving eller publisering uten eksplisitt regel eller menneskelig godkjenning
- skilt sikker automatisk staging-deploy ut som et parallelt infrastrukturløp; det er fortsatt planlagt og ikke implementert eller verifisert

## 2026-07-26

### PUBLIC og kontaktpublisering

- rettet PUBLIC HTML slik at aktørkort bruker kanonisk ID-basert detaljrute (`/public/actors/id/<actor_id>/`) og ikke lenger lager ødelagte lenker for publiserte aktører uten organisasjonsnummer
- beholdt legacy-rute for organisasjonsnummer som redirect når den identifiserer én publisert aktør entydig
- lagt til skrivebeskyttet `check_public_actor_links` for å kontrollere alle PUBLIC-kortlenker
- lagt til `publish_existing_email_contacts` som dry-run først, transaksjonell og idempotent staging-/datakommando for godkjent publisering av eksisterende e-postkontakter
- korrigert relasjonsspesifikt unntak fra `Kathrine Schem` til `Kathrine Schjem`
- kjørt staging-datakjøring etter backup: `164` av `164` eksisterende e-postkontakter er offentlige, og tre aktive aktør-person-koblinger er satt til `publish_person=False`
- bekreftet at telefonpublisering og `Organization.is_published` ikke ble endret

## 2026-07-24

### Utviklingsarbeidsflyt

- godkjent og implementert `ADR-006` for session-flyt og varig prosjektminne
- lagt til `$start-arbeidsokt` og `$avslutt-arbeidsokt`
- standardisert Git-baseline, project health, SESSION WRAP-UP og neste Codex-session-prompt
- utvidet ADR-006 med `$fortsett-prosjekt` som strategisk ChatGPT-rutine og tynn Codex-bro
- lagt til fast `CHATGPT SESSION SUMMARY` og dokumentert kontinuitet mellom nye ChatGPT-samtaler og Codex-sessioner
- validert alle 15 skills og bekreftet `$fortsett-prosjekt` i en separat skrivebeskyttet Codex-session

## 2026-07-23

### Dokumentasjon

- etablert ny dokumentasjonsstruktur på egen branch
- kartlagt at IMPORT er langt mer utviklet enn eldre prosjektfiler beskriver
- registrert at EKSPORT har datamodell og API-grunnlag, men ikke komplett motor
- registrert at public HTML foreløpig kun brukes i staging
- registrert ønsket om automatisk staging-deploy ved push
- godkjent `ADR-005` som målarkitektur for helhetlig personkontakt og relasjonsspesifikk publisering; implementering er ikke startet
