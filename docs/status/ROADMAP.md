# Roadmap

**Status:** Godkjent strategisk arbeidsrekkefølge

**Sist oppdatert:** 2026-07-28

Roadmapen skiller mellom produktfaser og et parallelt infrastrukturløp. En fase beskriver prioritert rekkefølge, ikke at innholdet allerede er implementert. Større implementering krever fortsatt et godkjent ADR når arbeidet innebærer et vesentlig arkitekturvalg.

## Fase 0 – Arbeidsflyt og én varig sannhetskilde

**Status:** Gjennomført med PR #10.

- GitHub og `docs/` er etablert som varig prosjektminne.
- Fredrik Development System består av `AGENTS.md`, dokumentert workflow og 15 repo-baserte Codex-skills.
- [ADR-006](../decisions/ADR-006-SESSION_WORKFLOW.md) beslutter session-flyten og skillet mellom session-laget og de fire faglige arbeidsnivåene.
- `$start-arbeidsokt`, `$avslutt-arbeidsokt` og `$fortsett-prosjekt` gir kontrollert oppstart, avslutning og kontinuitet.
- Gamle rotbaserte handoff-, `REFERENCE`- og `STATUS`-filer ble holdt utenfor den autoritative dokumentasjonen.
- Genererte Playwright-resultater er ignorert.

Sikker automatisk deploy til staging er ikke en gjenstående del av fase 0. Det er et separat infrastrukturløp og blokkerer ikke videre produktarbeid.

## Fase 1 – Verifiser staging- og frontend-baseline

**Status:** Neste aktive produktfase.

Før ny frontendutvikling skal forskjellen mellom lokal `main`, GitHub, staging og det brukeren faktisk ser, diagnostiseres. Arbeidet starter skrivebeskyttet og skal ikke blandes med retting eller deploy.

Kontrollen skal fastslå:

- hvilken repo-commit serveren har sjekket ut
- hvilken commit og hvilket bygg de kjørende containerne faktisk bruker
- om gamle frontend-bundles, statiske filer, bilder eller cache lever videre
- om nginx, Caddy eller nettlesercache påvirker resultatet
- om observerte avvik er reelle regresjoner på `main`
- hvilke forskjeller som finnes mellom lokal kjøring og staging

Hoveddesignet på forsidene i Editor CRM og PUBLIC er godkjent designreferanse. Øvrige sider, kort og komponenter skal videreutvikles innenfor denne visuelle retningen. Fasen avsluttes med en verifisert baseline og en avgrenset liste over eventuelle feil; den innebærer ikke automatisk retting eller deploy.

## Fase 2 – Liten stabilisering av kontaktvisning

**Status:** Planlagt, avgrenset mellomleveranse.

Etter baseline-verifiseringen gjennomføres en liten, generell stabilisering:

- spor offentlig persontelefon gjennom Editor, API og PUBLIC
- bruk Ulla-Stina Wiland som konkret undersøkelseseksempel, men rett den generelle årsaken
- vis `Person.title` offentlig når feltet finnes
- utsett relasjonsspesifikk tittel til den langsiktige kontaktfasen
- legg til regresjonstester for e-post, telefon, personlenke og tittel

Dette er ikke full implementering av [ADR-005](../decisions/ADR-005-CONTACT_ARCHITECTURE.md). Dagens mellomregel for kontaktpublisering beholdes til en senere, kontrollert migrering.

## Fase 3 – Robust thumbnail-, bilde- og kortarkitektur

**Status:** Planlagt hovedområde.

Bildeløsningen skal gå fra ustabile eksterne treff til en varig, redaksjonelt kontrollerbar ressurs:

- Open Graph som mulig kandidat, supplert med Brave eller annen bildesøkekilde
- preferanse for tidløst logo-, profil- eller motivbilde
- manuell godkjenning før varig bruk
- permanent lagring med kilde, proveniens, dato, kreditering og opphavsrett
- bevaring av original og støtte for beskjæring, fokuspunkt, skalering og format
- tydelig fallback og manuell overstyring
- samme valgte bilde i Editor, PUBLIC og senere Musikkontoret.no

Fasen etablerer samtidig et lite, delt frontendgrunnlag for aktørkort og relaterte visningsmønstre:

- aktørkort, bilder, tags, sted, spacing og responsiv overflow
- konsistente farger og kortvarianter
- retting av brune tags i PUBLIC
- robust håndtering av lange stedsnavn
- konsekvent bildeplassering, skalering og sentrering
- mindre avvik mellom Editor- og PUBLIC-kort

Dette er ikke en generell redesign. Øvrige kort og komponenter videreutvikles innenfor den godkjente visuelle retningen fra forsidene.

## Fase 4 – Produkt- og UX-design for Import 2.0

**Status:** Planlegging før større kodeendringer.

Den eksisterende importmotoren skal kartlegges og gjenbrukes der den er solid, men dagens brukeropplevelse skal ikke begrense det nye konseptet. Ingen større implementering starter før produkt- og UX-planen er godkjent.

Leveranser:

- kart over dagens import- og mappingmotor og tekniske begrensninger
- brukerreise og tydelig problemdefinisjon
- prioriterte brukerhistorier
- informasjonsarkitektur
- wireframes og klikkbar prototype
- review- og konfliktflyt
- kvalitetsmål og trygg håndtering av usikre data
- synlig fremdrift og hensiktsmessige gamification-mekanismer
- akseptansekriterier og testplan
- faseinndelt implementeringsplan

## Fase 5 – Personer, kontaktarkitektur og Editor-UX

**Status:** Planlagt langsiktig kontaktfase.

Denne fasen realiserer målarkitekturen i [ADR-005](../decisions/ADR-005-CONTACT_ARCHITECTURE.md) i kontrollerte, reversible leveranser:

- én samlet kontaktseksjon
- flere e-postadresser og telefonnumre
- én primær intern kontakt per type
- offentlige kontaktvalg per aktør–person-kobling
- offentlig preview fra samme projeksjon som API og PUBLIC
- tydelig skille mellom intern og offentlig status
- sticky lagreknapp og lagringsstatus nær handlingen
- mindre unødvendig scrolling og bedre utnyttelse av desktopbredde
- hensiktsmessig modal- eller redigeringsflyt
- støtte for relasjonsspesifikk offentlig tittel når produktvalget er avklart

Alle personvern-, migrerings-, rollback-, API- og datakrav i ADR-005 gjelder fortsatt.

## Fase 6 – Implementer Import 2.0

**Status:** Planlagt etter godkjent prototype og stabil kontaktmodell.

- gjenbruk den eksisterende importmotoren som teknisk fundament
- implementer den godkjente brukerreisen i avgrensede etapper
- integrer matching, berikelse og AI-forslag uten å skjule usikkerhet
- gjør trygge rader raske og konflikter tydelige
- behold menneskelig kontroll over irreversible eller publiserende valg
- test med representative, reelle filer
- gjennomfør brukertest med prosjekteier og minst én kollega

## Fase 7 – Eksport som ferdig produkt

**Status:** Delvis teknisk grunnlag, produktet er ikke ferdig.

- CSV- og XLSX-generering
- valg av felter, filtre og segmenter
- kontaktbevisst eksport
- intern arbeidsliste
- offentlig katalog basert på samme PUBLIC-projeksjon
- e-postlister
- sikker generering og nedlasting
- jobbhistorikk og tydelig status
- grunnlag for senere integrasjoner

## AI som gjennomgående produktprinsipp

AI er ikke en egen sprint. Det brukes der det gir målbar hjelp og alltid innen tydelige regler:

- bilde- og logokandidater i fase 3
- matching, manglende verdier, berikelse, kategoriforslag og prioritering av usikre rader i Import 2.0
- ingen automatisk overskriving uten eksplisitt regel eller menneskelig godkjenning
- AI kan peke ut informasjon eller publiseringsvalg som bør vurderes, men skal aldri aktivere, endre eller utvide offentlig publisering automatisk. Publisering krever en eksplisitt regel eller menneskelig godkjenning.

## Parallelt infrastrukturløp – Sikker automatisk staging-deploy

**Status:** Planlagt; ikke implementert eller verifisert.

Manuell og kontrollert deploy beholdes til denne kjeden er spesifisert, testet og godkjent:

- egen minst privilegert deploy-bruker
- GitHub Environment for staging
- secrets som ikke eksponerer serverens root-nøkkel
- deploy fra `main` først etter grønn obligatorisk CI
- deploy-lås mot samtidige kjøringer
- databasebackup før risikofylte steg
- health check og målrettede smoke-tester
- dokumentert rollback
- logging og gradvis hardening

Infrastrukturløpet følger [Staging and Deployment](../development/STAGING_AND_DEPLOYMENT.md), men ligger utenfor produktfasene og blokkerer ikke fase 1–7.

## Senere muligheter

- Google Sheets-import
- Checkin-import
- Mailmojo-import
- skjemaer og automatisk opprettelse av kontakter
- geografisk visning
- eksterne integrasjoner
- nettdugnad og samtykkebasert redigering
