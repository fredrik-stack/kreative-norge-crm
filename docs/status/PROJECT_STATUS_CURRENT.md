# Project Status Current

**Status:** Verifisert mot kodebasen

**Sist verifisert:** 2026-07-26

**Verifisert mot:** `crm/models.py`, `crm/views.py`, `crm/views_public_site.py`, `crm/urls_public_site.py`, `crm/serializers_public.py`, importtjenestene, React-editoren, staging-dokumentasjonen, PR #7, PR #8 og staging på commit `ea8b8762aecdff760728139b1659f7d3a43445c7`.

**Ansvar:** Prosjekteier + ChatGPT for prioritering og produktretning. Codex for oppdatering etter implementering.

## Aktiv utviklingsfase

Kontaktproblemet er diagnostisert som et tverrgående produkt- og arkitekturproblem. Fremtidig kontaktarkitektur er godkjent i `ADR-005`, men bare en mellomleveranse er implementert. Dagens kode har nå felles PUBLIC-regel for HTML/API, intern Editor-visning av kontaktkanaler, import-tri-state for kontaktpublisering og reparasjonskommandoer for eksisterende data. Den langsiktige relasjonsspesifikke kontaktmodellen fra ADR-005 er fortsatt ikke implementert. IMPORT er en omfattende, fungerende modul som skal revurderes på produkt- og UX-nivå før større videreutvikling. PUBLIC fungerer som API og staging-visning, men trenger endelig kontrakt mot Musikkontoret.no og en mer robust bilde-/thumbnail-løsning. EKSPORT har teknisk grunnlag, men ikke ferdig motor og brukerflyt.

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

## Neste tre produktområder

### 1. Kontaktpersonenes e-post og publisering

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

### 2. Varig thumbnail- og bildearkitektur

Open Graph-innhenting må erstattes eller suppleres med en robust løsning som sikrer et relevant bilde over tid. Arbeidet må planlegge:

- valg og godkjenning av bilde
- permanent lagring fremfor avhengighet av ekstern URL
- beskjæring og skalering til standardformat
- fallback og manuell overstyring
- opphavsrett, kilde og senere utskifting
- bruk i Editor, PUBLIC og Musikkontoret.no

### 3. Ny IMPORT-opplevelse

Før videre implementering skal IMPORT gjennom en egen produkt- og UX-planfase. Målet er en gamification-inspirert opplevelse som gjør tungt kvalitetsarbeid:

- enkelt å forstå
- raskt og effektivt
- motiverende og oversiktlig
- tydelig på fremdrift og kvalitet
- trygt, uten at brukeren kompromisser på datakvalitet

Eksisterende importmotor skal kartlegges som teknisk fundament, men dagens UX skal ikke låse den nye løsningen.

## Planlagt senere

- Google Sheets som importkilde
- Checkin som importkilde
- Mailmojo som importkilde
- automatisk deploy til staging ved push
- komplett eksportmotor
- auditlogg og sterkere sporbarhet

Google Sheets, Checkin og Mailmojo finnes foreløpig bare som reserverte kildetyper.

## Teknisk workflow-status

- GitHub er felles sannhetskilde mellom lokal kode, Codex og ChatGPT.
- ChatGPT kan lese repoet når prosjekteier ber om oppdatert analyse.
- Fredrik Development System er installert som prosjektets utviklingsplattform.
- Repo-reglene ligger i `AGENTS.md`, og 12 prosjektbaserte Codex-skills ligger i `.agents/skills/`.
- Codex skal lese `docs/README.md`, dette dokumentet og relevant feature-/arkitekturdokument før implementering.
- Større implementeringer krever godkjent ADR.
- Funksjonelle endringer skal ledsages av dokumentasjonsoppdatering eller eksplisitt vurdering av at dokumentasjonen fortsatt er korrekt.
- Automatisk staging-deploy ved push er ønsket, men ikke implementert eller verifisert.

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

Ny dokumentasjonsstruktur er etablert på `docs/project-workflow-baseline`. Den er migrert og kvalitetssikret på overordnet nivå mot dagens kodebase. Eldre dokumenter beholdes som historiske kilder inntil de eventuelt arkiveres i en senere, separat endring.
