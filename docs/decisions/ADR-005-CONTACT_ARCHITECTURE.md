# ADR-005: Helhetlig kontaktarkitektur

## Status

Godkjent som målarkitektur. Ikke implementert.

**Beslutningsdato:** 2026-07-23

## Forhold til tidligere ADR-er

Denne beslutningen presiserer og viderefører:

- `ADR-001`: all kontaktdata og alle arbeidsflyter skal være tenant-isolerte
- `ADR-002`: `PersonContact` skal brukes for flere kontaktkanaler per person
- `ADR-003`: intern informasjon skal være adskilt fra eksplisitt offentlig informasjon
- `ADR-004`: kontaktendringer gjennom import skal gå gjennom preview, review og eksplisitt commit

ADR-005 erstatter den langsiktige bruken av direkte `Person.email` og `Person.phone` som selvstendige kontaktkilder, og erstatter global kontaktpublisering via `PersonContact.is_public` med publisering per aktør–person-kobling.

Eksisterende kode følger ennå ikke målarkitekturen.

## Bakgrunn

Diagnosen av manglende e-post for kontaktpersoner viste at problemet ikke er en isolert visningsfeil.

Dagens løsning har:

- direkte `Person.email` og `Person.phone`
- normaliserte kontaktposter i `PersonContact`
- personpublisering via `OrganizationPerson.publish_person`
- global kontaktpublisering via `PersonContact.is_public`
- forskjellige fallbackregler i Editor, public API og public HTML
- import som skriver både direktefelt og `PersonContact`, og som kan endre publiseringsflagg ved oppdatering

Editor viser i hovedsak direktefeltene på personen, mens PUBLIC normalt bygger på `PersonContact`. Public HTML har i tillegg en egen e-postfallback til `Person.email` som public API ikke har. Dette kan gi manglende data, duplisering, inkonsistent offentlig visning og utilsiktet eksponering av intern kontaktinformasjon.

Den lokale databasen bekreftet at direktefelt fremdeles inneholder vesentlig kontaktdata som ikke finnes som `PersonContact`. En overgang må derfor være additiv, datakartlagt og reverserbar.

## Beslutning

### 1. Én autoritativ kilde

`PersonContact` skal være eneste autoritative kilde for personers e-postadresser og telefonnumre.

`Person.email` og `Person.phone` skal:

1. beholdes midlertidig for kompatibilitet
2. gjøres read-only i overgangsperioden
3. ikke brukes av PUBLIC
4. ikke skrives av Editor, IMPORT eller nye tjenester etter cutover
5. fjernes i en senere og separat leveranse

Primær e-post og telefon skal avledes fra `PersonContact`.

### 2. Primær er ikke det samme som offentlig

`PersonContact.is_primary` angir foretrukket intern kontakt innen én kontakttype.

Primærstatus skal:

- brukes til standardvisning, matching og enkel intern eksport
- være valgfri, men maksimalt én per person og kontakttype
- aldri medføre publisering
- ikke erstattes av import uten eksplisitt beslutning

### 3. Publisering skjer per aktør–person-kobling

`OrganizationPerson.publish_person` skal fortsatt styre om personen kan vises offentlig for den konkrete aktøren.

En ny relasjonsmodell, foreløpig kalt `OrganizationPersonContactPublication`, skal angi hvilke konkrete `PersonContact` som kan vises på den aktuelle aktørsiden.

Målrelasjonen er:

```text
Organization
    └── OrganizationPerson
            ├── publish_person
            ├── Person
            │     └── PersonContact
            └── OrganizationPersonContactPublication
                    └── valgt PersonContact for denne koblingen
```

En offentlig kontakt krever at:

1. organisasjonen er publisert
2. koblingen er aktiv
3. personen er eksplisitt publisert på koblingen
4. den konkrete kontaktkanalen er eksplisitt valgt på koblingen

`PersonContact.is_public` fases ut etter at relasjonsspesifikk publisering er migrert og verifisert.

### 4. Personvern som standard

All ny kontaktinformasjon skal være intern som standard.

Det innebærer:

- ingen forhåndsaktiverte publiseringsvalg
- ingen implisitt publisering fra primærstatus
- ingen publisering basert på direkte personfelt
- ingen AI-generert eller AI-aktivert publisering
- ingen importpublisering uten eksplisitt input og review
- ingen PUBLIC-fallback til intern informasjon

Et publiseringsvalg dokumenterer en produktbeslutning om offentlig visning. Det skal ikke omtales som juridisk samtykke med mindre virksomheten har en separat, gyldig og dokumenterbar samtykkeflyt.

### 5. Én offentlig projeksjon

Public HTML, public API og Editor-preview skal bruke én felles offentlig projeksjon eller resolver.

Resolveren skal alene avgjøre:

- hvilke aktører som er offentlige
- hvilke personkoblinger som er offentlige
- hvilke kontaktkanaler som er offentlige
- sortering og deduplisering

Templates, serializers og frontend skal ikke ha egne kontaktfallbacker eller publiseringsregler.

Den offentlige kontrakten skal ikke returnere interne kontaktverdier, interne publiseringsflagg, kildeopplysninger eller andre interne metadata.

### 6. Editor skal presentere én kontaktfunksjon

Brukeren skal ikke måtte forstå `Person`, `PersonContact`, `OrganizationPerson` eller publiseringsrelasjonen.

Editor skal tilby:

- én samlet kontaktseksjon på personen
- flere e-poster og telefonnumre
- tydelig valg av primærkontakt
- tydelig skille mellom «kun intern» og offentlig bruk
- valg av offentlige kontaktkanaler per aktørkobling
- trygg standard med publisering slått av
- preview bygget fra den felles offentlige resolveren

Oppretting av person, kontakter, aktørkobling og publiseringsvalg fra aktørsiden skal skje atomisk.

### 7. IMPORT skal bevare eksisterende data som standard

`person_email` og `person_phone` skal normaliseres til `PersonContact`.

For nye personer skal første kontakt av en type normalt bli primær og intern.

For eksisterende personer skal import:

- gjenbruke identiske normaliserte kontakter
- foreslå tillegg av nye kontakter
- beholde eksisterende primærstatus og publisering når input mangler
- tolke tomme felt som `KEEP`, ikke `CLEAR`
- kreve eksplisitt review for `REPLACE`, `CLEAR`, primærbytte og publiseringsendring

Publisering skal behandles som tri-state:

- mangler eller blank: behold eksisterende, og bruk intern standard for nye data
- eksplisitt `true`: foreslå publisering
- eksplisitt `false`: foreslå avpublisering

AI skal aldri kunne foreslå eller aktivere publisering.

Langsiktig importformat skal støtte separate personer, kontaktposter, aktørkoblinger og offentlige kontakttildelinger. Eksisterende importformat kan støttes midlertidig gjennom kontrollert kompatibilitet.

### 8. EKSPORT skal ha eksplisitte produkter

Kontaktdata skal kunne eksporteres som:

1. intern arbeidsliste
2. offentlig katalogeksport fra samme resolver som PUBLIC
3. full administrativ og relasjonell eksport

Full eksport skal bevare personer, kontaktposter, aktørkoblinger og offentlige kontakttildelinger som separate relasjoner.

Eksport av intern kontaktinformasjon skal være tenant-isolert, rollebeskyttet, logget og underlagt definert filretensjon.

### 9. Migreringen skal være additiv

Overgangen skal gjennomføres i denne rekkefølgen:

1. kartlegg staging- og produksjonsdata
2. ta backup og lag migreringsmapping
3. legg til nytt skjema og nye constraints
4. backfill direktefelt til interne `PersonContact`
5. migrer eksplisitte `PersonContact.is_public` til relasjonsspesifikke publiseringer
6. verifiser gammel og ny offentlig projeksjon
7. aktiver ny Editor, IMPORT og PUBLIC i kontrollerte leveranser
8. fjern legacy-felt først etter en stabil periode

Direkte e-post som bare har vært offentlig gjennom HTML-fallback, skal ikke automatisk bli offentlig gjennom en teknisk backfill. Endelig behandling av disse radene krever eksplisitt godkjenning før migreringen gjennomføres.

## Datamodellkrav

Målmodellen for `PersonContact` skal minst støtte:

- `person`
- `type`
- `value`
- normalisert sammenligningsverdi
- valgfri etikett
- `is_primary`
- opprettelses- og oppdateringstidspunkt

Målmodellen skal håndheve:

- unik normalisert verdi per person og kontakttype
- maksimalt én primærkontakt per person og kontakttype
- gyldig verdi for kontakttypen
- tenant-konsistens

Publiseringsrelasjonen skal håndheve:

- unik kontakt per aktør–person-kobling
- at kontakten tilhører personen på koblingen
- tenant-konsistens

Eksakte modellnavn og teknisk constraint-utforming bestemmes i implementeringen, men må oppfylle disse invariantene.

## Konsekvenser

### Positive konsekvenser

- én sannhetskilde for personkontakt
- samme offentlige resultat i HTML, API og preview
- eksplisitt og kontekstuell publisering
- tryggere import og migrering
- tydeligere Editor-opplevelse
- bedre grunnlag for eksport, audit og senere integrasjoner

### Kostnader og ulemper

- ny relasjonsmodell og datamigrering
- midlertidig kompatibilitetslag
- større testmatrise
- eksisterende data må kartlegges og delvis vurderes manuelt
- public-kontrakten kan kreve versjonering
- implementeringen berører modeller, API, Editor, IMPORT, PUBLIC og EKSPORT

## Avviste alternativer

### Beholde både direktefelt og `PersonContact`

Avvist fordi to skrivbare sannhetskilder fortsetter å skape drift, fallbackregler og personvernrisiko.

### Beholde global `PersonContact.is_public` som målmodell

Kan brukes som en kortvarig MVP, men er avvist som langsiktig løsning fordi samme person kan trenge forskjellige kontaktkanaler hos forskjellige aktører.

### Lagre kontaktverdier direkte på `OrganizationPerson`

Avvist fordi det dupliserer kontaktverdier, svekker personidentiteten og gjør oppdatering og deduplisering vanskeligere.

## Implementeringsplan og akseptansekriterier

Ingen leveranse under skal starte før de eksplisitte godkjenningene som gjelder leveransen, er avklart.

### Leveranse 0: beslutningsgater og databaseline

**Omfang:**

- avklare åpne produkt-, personvern- og tilgangsbeslutninger
- kjøre skrivebeskyttet datarapport i staging og produksjon
- dokumentere offentlig før-bilde for HTML og API
- ta backup- og rollbackbeslutning

**Akseptansekriterier:**

- alle blokkerende beslutninger nedenfor er godkjent
- tellinger og konfliktgrupper finnes uten unødvendige personverdier i rapporten
- forskjeller mellom direktefelt, `PersonContact` og offentlig visning er kjent
- backup, migreringsmapping og rollback er godkjent
- ingen data eller kode er endret

### Leveranse 1: kontrakts- og personverntester

**Omfang:**

- legge inn regresjonstester for den diagnostiserte feilen
- definere ønsket publiseringsmatrise som tester
- definere forventet HTML/API/preview-paritet

**Akseptansekriterier:**

- alle kombinasjoner av aktørstatus, koblingsstatus, personpublisering og kontaktvalg er dekket
- negative tester beviser at intern kontakt ikke returneres
- dagens forskjell mellom HTML og API er reprodusert
- testene skiller eksisterende adferd fra ønsket målkontrakt

### Leveranse 2: additiv kontaktmodell

**Omfang:**

- utvide `PersonContact`
- legge til nødvendige constraints
- opprette relasjonsspesifikk publiseringsmodell
- legge til nødvendig auditmetadata

**Akseptansekriterier:**

- eksisterende felter og data er fortsatt tilgjengelige
- maksimalt én primærkontakt per person og type håndheves
- normaliserte duplikater håndteres kontrollert
- publiseringsrelasjonen kan ikke bruke kontakt fra feil person eller tenant
- migrasjonen er testet lokalt på realistisk datakopi og kan reverseres

### Leveranse 3: backfill og migreringsreview

**Omfang:**

- opprette interne `PersonContact` fra direktefelt
- bevare ulike eksisterende verdier
- migrere eksplisitt `is_public` til relasjonsspesifikke tildelinger
- produsere reviewliste for konflikter og tidligere HTML-fallback

**Akseptansekriterier:**

- backfill er idempotent
- ingen direkte kontaktverdi går tapt
- ingen direktefelt blir offentlig som bivirkning
- eksisterende eksplisitte offentlige kontakter er representert i ny modell
- konflikt- og reviewlisten er godkjent før public cutover
- rollback er prøvd på datakopi

### Leveranse 4: felles domenetjeneste og internt API

**Omfang:**

- samle kontaktvalidering og kontaktkommandoer
- tilby atomisk lagring av person, kontakter, kobling og publisering
- tilby deprecated read-only aliaser for legacy-felter ved behov

**Akseptansekriterier:**

- nye skriveruter skriver bare til autoritativ kontaktmodell
- en feil kan ikke etterlate halvferdig person eller kobling
- tenant-isolasjon og rolletilgang er testet
- primærbytte og publiseringsvalg er transaksjonelle
- eksisterende klienter har en dokumentert kompatibilitetsvei

### Leveranse 5: samlet kontaktopplevelse i Editor

**Omfang:**

- samlet kontaktseksjon på person
- flere kontaktkanaler og primærvalg
- offentlig kontaktvalg per aktørkobling
- trygg opprettingsflyt fra aktør
- preview fra offentlig resolver

**Akseptansekriterier:**

- redaktøren trenger ikke forstå intern modell
- alle nye publiseringsvalg er slått av som standard
- intern og offentlig status er tydelig for hver kontakt
- samme person kan ha forskjellige offentlige kontakter hos ulike aktører
- preview viser nøyaktig forventet offentlig resultat
- relevante komponent- og E2E-tester er grønne

### Leveranse 6: kontaktregler i IMPORT

**Omfang:**

- mappe personkontakt til autoritativ modell
- innføre `KEEP`, `ADD`, `SET_PRIMARY`, `REPLACE` og `CLEAR`
- innføre tri-state publisering
- vise kontakt- og publiseringsdiff i review

**Akseptansekriterier:**

- blank input endrer ikke eksisterende data
- identiske normaliserte kontakter gjenbrukes
- primærstatus og publisering endres bare eksplisitt
- AI kan ikke påvirke publisering
- flere e-poster blir separate kontaktposter
- publiseringsendringer behandles som høyrisiko-review
- commit og rollback er tenant-isolert og sporbar

### Leveranse 7: felles PUBLIC-projeksjon

**Omfang:**

- innføre én offentlig resolver
- konsolidere public serializers og ruter
- koble HTML, API og Editor-preview til samme projeksjon
- fjerne direktefeltfallback

**Akseptansekriterier:**

- HTML, API og preview viser samme personer og kontakter
- ingen intern kontaktverdi finnes i respons eller HTML-kilde
- ingen fallback fra direktefelt finnes
- offentlig diff er gjennomgått og godkjent før aktivering
- ekstern API-kompatibilitet eller versjonering er avklart
- feature flag eller annen trygg rollback er verifisert

### Leveranse 8: kontaktbevisst EKSPORT

**Omfang:**

- intern arbeidsliste
- offentlig katalogeksport
- full relasjonell eksport
- tilgang, logging og filretensjon

**Akseptansekriterier:**

- public eksport samsvarer med public API
- full eksport bevarer alle kontakt- og publiseringsrelasjoner
- intern kontaktdata er rolle- og tenant-beskyttet
- eksport og nedlasting er logget
- CSV-formelinjektering og filretensjon er håndtert

### Leveranse 9: legacy-opprydding

**Omfang:**

- stoppe legacy-lesing
- fjerne gamle API-felter
- fjerne `Person.email`, `Person.phone` og `PersonContact.is_public`

**Akseptansekriterier:**

- ingen aktiv kode eller integrasjon bruker legacy-feltene
- stabiliseringsperioden er fullført uten ukjente avvik
- databasebackup og separat rollbackplan er godkjent
- feltdropp skjer i en egen release
- dokumentasjon og prosjektstatus beskriver faktisk implementert løsning

## Rollbackprinsipper

- skjemaendringer skal være additive frem til siste leveranse
- backfill skal være idempotent og kunne spores til en migreringsbatch eller mapping
- legacy-felter skal beholdes gjennom public cutover
- ny intern og offentlig lesing skal kunne deaktiveres kontrollert før feltdropp
- rollback skal aldri automatisk gjenaktivere personvernsvak fallback fra `Person.email`
- fysisk feltdropp skal ha egen backup, deploy og rollbackbeslutning

## Beslutninger som fortsatt krever eksplisitt godkjenning

Følgende er ikke avgjort av ADR-005 og blokkerer relevante implementeringsleveranser:

1. **Tidligere HTML-fallback:** om direkte e-poster som tidligere har vært synlige uten eksplisitt kontaktflagg, skal avpubliseres frem til manuell godkjenning. ADR-et anbefaler dette.
2. **Person uten offentlig kontakt:** om en eksplisitt publisert person kan vises med navn og tittel uten e-post eller telefon. ADR-et anbefaler dette.
3. **Organisasjonens e-post:** om `Organization.email` skal få et eget eksplisitt `publish_email`. ADR-et anbefaler dette.
4. **Publiseringsrettighet:** hvilke roller som kan publisere enkeltkontakter, og om bulk- og importpublisering krever gruppeadmin eller superadmin.
5. **Eksportrettighet:** hvilke roller som kan laste ned intern arbeidsliste og full administrativ eksport.
6. **Behandlingsgrunnlag:** hvilket behandlingsgrunnlag virksomheten bruker for intern lagring og offentlig publisering, og hvordan dette dokumenteres organisatorisk.
7. **Retensjon:** lagringstid for importfiler, eksportfiler, migreringsrapporter og publiseringshistorikk.
8. **Public API-versjonering:** om kontaktkontrakten endres i eksisterende API eller lanseres som en ny versjon.
9. **Personrolle:** om offentlig tittel fortsatt skal ligge globalt på `Person`, eller senere flyttes til `OrganizationPerson`.

Eksakte modellnavn, endepunktnavn og UI-komponentnavn er implementeringsdetaljer og krever ikke ny arkitekturbeslutning så lenge invariantene i ADR-et oppfylles.

## Ferdigkriterium

ADR-005 regnes som implementert først når:

- `PersonContact` er eneste skrivbare kilde for personkontakt
- relasjonsspesifikk kontaktpublisering er aktiv
- Editor, IMPORT, PUBLIC og EKSPORT følger samme kontaktregler
- HTML, API og preview bruker samme offentlige projeksjon
- legacy-fallback er fjernet
- migrering og rollback er verifisert
- tester og dokumentasjon beskriver faktisk adferd
