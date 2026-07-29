# Project Status Current

**Status:** Fase 1 verifisert; fase 2 aktiv

**Teknisk sist verifisert:** 2026-07-29

**Teknisk verifisert mot:** lokal og GitHub `main` på `f6f03d67ba0c5d3afbe258fb356248e7075c4b49`, staging-repo på `ea8b8762aecdff760728139b1659f7d3a43445c7`, kjørende images og containere, frontendbundles over HTTPS, ren frontendbuild, PUBLIC desktop/mobil og autentisert Editor.

**Produkt-roadmap sist oppdatert:** 2026-07-29

**Arbeidsflyt sist kontrollert:** 2026-07-28

**Ansvar:** Prosjekteier + ChatGPT for prioritering og produktretning. Codex for oppdatering etter implementering.

## Aktiv utviklingsfase

Fase 1 i [ROADMAP.md](ROADMAP.md) ble gjennomført 2026-07-29. Den skrivebeskyttede baselinen verifiserte server-, container-, bygg-, proxy-, cache-, PUBLIC- og Editor-tilstanden. Hoveddesignet på forsidene i Editor CRM og PUBLIC er godkjent designreferanse. Øvrige sider, kort og komponenter skal videreutvikles innenfor denne visuelle retningen.

Aktiv produktfase er fase 2: en liten kontaktstabilisering før robust thumbnail- og bildearkitektur. Fasen skal reparere manglende private primære telefonkontakter kontrollert, gjøre nye publiseringsvalg avslått som standard og vise `Person.title` offentlig. Den langsiktige relasjonsspesifikke kontaktmodellen fra [ADR-005](../decisions/ADR-005-CONTACT_ARCHITECTURE.md) kommer fortsatt senere.

## Verifisert fase 1-baseline

- lokal og GitHub `main` var synkronisert på `f6f03d67ba0c5d3afbe258fb356248e7075c4b49`
- staging-repoet var rent på `ea8b8762aecdff760728139b1659f7d3a43445c7`; de åtte nyere commitene på `main` endret ikke kjørende applikasjonskode
- API-koden i imaget kunne knyttes til serverrepo-SHA gjennom innebygd Git-metadata og filhashes
- web-imagets eksakte commit var ikke merket, men JS- og CSS-bundles matchet ren build fra dagens `main`
- HTTPS leverte de samme bundlehashene som web-containeren, også med cache-busting
- nginx og Caddy leverte forventet kjede; proxy og Cloudflare-cache viste ikke gamle frontendfiler
- Django system check og PostgreSQL readiness var grønne, og de kjørende containerne hadde ingen restarter
- PUBLIC desktop/mobil og autentisert Editor ble kontrollert; Editor-forsiden er godkjent designreferanse
- observerte kort-, bilde-, tag- og layoutavvik er lagt til fase 3 eller fase 5 og ble ikke rettet i baselinen
- ingen kode, data, publiseringsflagg, containere, tjenester eller deploy ble endret i fase 1

Detaljert, datert evidens finnes i [FRONTEND_BASELINE_2026-07-29.md](FRONTEND_BASELINE_2026-07-29.md). Dette dokumentet er fortsatt autoritativ nåstatus.

## Fase 2-baseline

Det konkrete undersøkelseseksemplet viste en person med verdi i direkte `Person.phone`, men uten noen `PersonContact` av type `PHONE`. Personen hadde bare en lagret e-postkontakt. Direkte telefon kan derfor ikke få egen offentlig kontroll og skal heller aldri brukes som PUBLIC-fallback.

Kodekartleggingen viser samtidig at dagens person-API synkroniserer direkte `Person.email` og `Person.phone` til private primære kontakter ved ny lagring. Avviket gjelder derfor eksisterende legacy-data som ikke har gått gjennom denne synkroniseringen. `repair_person_contacts` reparerer før fase 2 bare e-post.

Editor-baselinen viste fire utrygge forhåndsvalg i opprettingsflytene:

- offentlig e-post på ny kontaktperson
- offentlig telefon på ny kontaktperson
- publisering av ny kontaktperson
- publisering ved kobling av eksisterende person

Alle fire skal være avslått som standard i fase 2. Dette endrer ikke eksisterende lagrede publiseringsflagg.

## Implementert

- tenant-basert CRM for aktører og personer
- koblinger mellom aktører og personer
- flere kontaktkanaler per person
- kategorier, underkategorier og tenant-spesifikke tags
- roller via `TenantMembership`
- intern React-editor med rollebasert tilgang
- public API for publiserte aktører
- public HTML-visning, foreløpig kun brukt i staging
- PUBLIC HTML-detaljsider med kanonisk ID-rute og legacy orgnummer-redirect
- felles PUBLIC-regel for personkontakt i HTML og API: aktiv kobling med `publish_person=True` og kontaktkanal med `PersonContact.is_public=True`
- synkronisering mellom `Person.email`/`Person.phone` og primær intern `PersonContact`
- importjobber med opplasting, parsing, normalisering, preview, validering, matching, AI-forslag, review, beslutninger, commit, commit-logg og feilrapport
- grunnmodell og grunn-API for eksportjobber
- Docker-basert lokal kjøring og stagingoppsett

## Delvis implementert

### EXPORT

`ExportJob`, eksporttyper, CSV/XLSX-formatvalg, filtre, feltvalg og grunnleggende API finnes. Faktisk filgenerering, nedlasting og komplett brukerflyt er ikke bekreftet ferdig.

### PUBLIC

Public API og HTML-visning fungerer. HTML-visningen brukes foreløpig bare i staging. Endelig API-kontrakt og integrasjon mot Musikkontoret.no er ikke ferdigstilt.

### Roller og tilgang

Kjerne-rollene og tenant-scope håndheves i backend. Invitasjonsflyt, full administrasjon av medlemmer og den langsiktige modellen for eksterne tenant-rom må videreutvikles.

## Prioritert produktrekkefølge

### 1. Staging- og frontend-baseline – gjennomført 2026-07-29

Før det endres kode eller deployes, skal en skrivebeskyttet diagnose fastslå:

- repo-commit på serveren
- faktisk commit og bygg i kjørende containere
- om frontend-bundles, statiske filer, bilder eller cache er utdaterte
- påvirkning fra nginx, Caddy og nettlesercache
- forskjeller mellom lokal `main` og staging
- hvilke observerte avvik som er reelle regresjoner på `main`

### 2. Liten kontaktstabilisering – aktiv

Den avgrensede mellomleveransen skal spore offentlig telefon gjennom Editor, API og PUBLIC, vise `Person.title` offentlig når den finnes og legge til regresjonstester for e-post, telefon, personlenke og tittel. Ulla-Stina Wiland brukes som undersøkelseseksempel, men en eventuell retting skal være generell. Dette er ikke full implementering av [ADR-005](../decisions/ADR-005-CONTACT_ARCHITECTURE.md).

### 3. Thumbnail/bilder og Import 2.0

Robust thumbnail- og bildearkitektur er neste store implementeringsområde etter kontaktstabiliseringen. Deretter skal Import 2.0 gjennom en egen produkt- og UX-designfase før større kodeendringer. Dagens importmotor skal gjenbrukes der den er solid, men skal ikke låse den nye brukeropplevelsen.

Detaljert faseinndeling, AI-prinsipp og senere produktområder finnes i [ROADMAP.md](ROADMAP.md).

## Verifisert kontaktstatus

### Implementert mellomregel

Første mellomleveranse er implementert og deployet til staging. Problemet skyldte en todelt kontaktarkitektur og forskjellige regler i Editor, import og PUBLIC:

- `Person.email` og `Person.phone` er parallelle med `PersonContact`
- Editor viste og lagret i hovedsak direktefeltene
- enkelte opprettingsflyter skriver både direktefelt og `PersonContact`
- public API brukte eksplisitte `PersonContact`
- public HTML kunne falle tilbake til direkte person-e-post
- import kunne oppdatere begge kilder og endre publiseringsflagg

Implementert mellomregel:

- `OrganizationPerson.publish_person` bestemmer om personen vises som kontaktperson offentlig
- `PersonContact.is_public` bestemmer om hver e-post eller telefon vises offentlig
- `Person.email` og `Person.phone` brukes ikke som PUBLIC-fallback
- Editor CRM er intern og viser kontaktkanaler også når de ikke er offentlige
- import støtter `person_email_public` og `person_phone_public` som tri-state publiseringsfelt
- `repair_person_contacts` kan opprette manglende private primære e-postkontakter fra `Person.email`
- `publish_existing_email_contacts` ble kjørt på staging 2026-07-26 etter backup og gjorde eksisterende e-postkontakter offentlige, med tre relasjonsspesifikke unntak på `publish_person=False`

Staging etter datakjøringen:

- `email_contacts_total=164`
- `email_contacts_public=164`
- `email_contacts_private=0`
- `active_links_total=170`
- `active_links_publish_true=167`
- `active_links_publish_false=3`

De tre unntakene er:

- `Nordland fylkeskommune` / `Kathrine Schjem`
- `Nordland fylkeskommune` / `Ole-Thomas Kolberg`
- `Bådin` / `Jonas Jørgensen Moe`

Målarkitekturen er godkjent i `docs/decisions/ADR-005-CONTACT_ARCHITECTURE.md`:

- `PersonContact` blir eneste autoritative kilde
- primærkontakt og offentlig kontakt holdes adskilt
- offentlige kontaktkanaler velges per aktør–person-kobling
- HTML, API og Editor-preview bruker én offentlig projeksjon
- migreringen gjennomføres additivt og reverserbart

Den langsiktige ADR-005-modellen er ikke implementert. Direktefelt finnes fortsatt av kompatibilitetshensyn, og dagens `PersonContact.is_public` er fortsatt globalt for kontaktkanalen, ikke relasjonsspesifikt.

## Planlagt senere

- Google Sheets som importkilde
- Checkin som importkilde
- Mailmojo som importkilde
- komplett eksportmotor
- auditlogg og sterkere sporbarhet

Google Sheets, Checkin og Mailmojo finnes foreløpig bare som reserverte kildetyper.

## Separat infrastrukturløp

Sikker automatisk staging-deploy er planlagt utenfor produktfasene og blokkerer ikke fase 1. Manuell og kontrollert deploy gjelder inntil det finnes en testet kjede med minst privilegert deploy-bruker, GitHub Environment og secrets, grønn obligatorisk CI på `main`, deploy-lås, databasebackup, health/smoke-kontroll, rollback og tilstrekkelig logging/hardening. Serverens root-nøkkel skal ikke lagres som GitHub-secret.

## Teknisk workflow-status

- GitHub er felles sannhetskilde mellom lokal kode, Codex og ChatGPT.
- ChatGPT kan lese repoet når prosjekteier ber om oppdatert analyse.
- Fredrik Development System er installert som prosjektets utviklingsplattform.
- Repo-reglene ligger i `AGENTS.md`, og 15 prosjektbaserte Codex-skills ligger i `.agents/skills/`.
- `$fortsett-prosjekt` er installert som en tynn Codex-bro fra ChatGPT-handoff til `$start-arbeidsokt`; ChatGPT-rutinen med samme navn er dokumentert separat.
- `$start-arbeidsokt` og `$avslutt-arbeidsokt` danner et skrivebeskyttet SESSION-lag rundt de fire arbeidsnivåene, i tråd med `ADR-006`.
- Alle 15 skills er strukturelt validert. `$fortsett-prosjekt` er eksplisitt runtime-testet i en ny skrivebeskyttet Codex-session med konfliktmerking, full delegering til `$start-arbeidsokt` og uendret arbeidsmappe.
- Fredrik Skill Pack, ChatGPT og Codex er prosjektets valgte arbeidsverktøy. Claude eller Superpowers er ikke valgt som en parallell arbeidsflyt; nyttige prinsipper fra andre rammeverk kan innarbeides i det eksisterende systemet når de gir konkret verdi.
- Codex skal lese `docs/README.md`, dette dokumentet og relevant feature-/arkitekturdokument før implementering.
- Større implementeringer krever godkjent ADR.
- Funksjonelle endringer skal ledsages av dokumentasjonsoppdatering eller eksplisitt vurdering av at dokumentasjonen fortsatt er korrekt.
- Automatisk staging-deploy er et separat infrastrukturløp og er ikke implementert eller verifisert.

## Åpne avklaringer

- valgt mekanisme for automatisk staging-deploy
- obligatoriske tester og CI-gates før deploy
- endelig kontrakt mellom CRM-public og Musikkontoret.no
- endelig lagringsarkitektur for bilder
- eksplisitt publiseringsfelt for organisasjonens e-post
- roller for kontaktpublisering, bulkpublisering og full kontakt-eksport
- behandlingsgrunnlag og retensjon for kontakt-, import-, eksport- og auditdata
- versjonering av ny public kontaktkontrakt
- om personens offentlige tittel senere skal være koblingsspesifikk

## Dokumentasjonsstatus

`docs/` er autoritativ dokumentasjonsstruktur og er kvalitetssikret på overordnet nivå mot dagens kodebase. PR #10 fullførte session-workflowen og holdt gamle rotbaserte handoff-, `REFERENCE`- og `STATUS`-filer utenfor repoets parallelle sannhetskilder. Den godkjente produktrekkefølgen er dokumentert i [ROADMAP.md](ROADMAP.md).
