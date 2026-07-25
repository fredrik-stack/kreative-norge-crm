# Kapittel 10 – Databasen og migrasjoner: hvor CRM-dataene faktisk bor

Jeg trodde først at hele CRM-et lå i kodebasen. Men VS Code og GitHub inneholder bare oppskriften: modeller, API-er, frontend og konfigurasjon. Aktørene, personene, kontaktopplysningene, taggene og koblingene ligger i PostgreSQL.

Kode kan hentes på nytt fra GitHub. Hvis databasen forsvinner uten en brukbar backup, kan prosjektets virkelige innhold være borte.

## Kode og data er forskjellige

Koden bestemmer hvilke felter som finnes, hvilke regler som gjelder, hvordan brukere får tilgang, og hvordan data vises. Git versjonerer denne koden.

Dataene er innholdet brukerne og importjobbene oppretter:

- «Riddu Riđđu Festivála»
- organisasjonsnummer og kommune
- personer og kontaktkanaler
- publiseringsstatus
- kategorier og tags
- interne notater og koblinger

PostgreSQL lagrer dette innholdet. En commit av en Django-modell lagrer ikke radene i databasen, og GitHub er ikke databasebackup.

## PostgreSQL som relasjonsdatabase

PostgreSQL organiserer informasjon i tabeller som kan kobles sammen. En forenklet CRM-modell inneholder blant annet:

```text
Tenant
Organization
Person
OrganizationPerson
PersonContact
Category
Subcategory
Tag
```

En **tabell** samler én type informasjon, som organisasjoner. En **rad** er én konkret organisasjon. En **kolonne** er ett felt, som `name`, `org_number` eller `is_published`.

Hver rad får en unik **primærnøkkel**, vanligvis `id`. Et navn kan endres eller finnes flere ganger, mens ID-en gir databasen en stabil intern identitet.

En **fremmednøkkel** peker fra én tabell til en annen. `Organization.tenant_id` kobler for eksempel en organisasjon til riktig tenant.

## Relasjoner har egen betydning

En person kan være knyttet til flere organisasjoner, og en organisasjon kan ha flere personer. CRM-et bruker derfor koblingsmodellen `OrganizationPerson`.

Koblingen inneholder ikke bare to ID-er. Den har også egne opplysninger, blant annet:

- statusen `ACTIVE` eller `INACTIVE`
- om personen skal publiseres i denne organisasjonssammenhengen
- tidspunktet koblingen ble opprettet

En inaktiv kobling betyr ikke at personen er slettet. Personen kan fortsatt være relevant for andre aktører eller som historikk.

`PersonContact` kan lagre flere e-poster og telefonnumre per person, med markering for primær og offentlig kontakt. Dagens kode har samtidig direktefeltene `Person.email` og `Person.phone`. Denne doble kontaktarkitekturen er en kjent utfordring: ulike deler av systemet kan lese forskjellige kilder.

Målarkitekturen er besluttet i ADR-005, men ikke implementert. Manualen skal derfor ikke beskrive `PersonContact` som eneste autoritative kilde ennå. Ved senere migrering må eksisterende kontaktdata, publiseringsregler og fallback-adferd bevares eller endres kontrollert.

Kontaktomleggingen viser hvorfor datamodellendringer må deles opp. En trygg prosess kan først kartlegge alle direktefelt og `PersonContact`-rader, deretter innføre den nye koblingsspesifikke publiseringsmodellen, kopiere og kontrollere data, bytte lesing og skriving, og først mye senere fjerne gamle felt.

Under overgangen må Editor, import, public API og offentlig HTML kunne fungere mot en bevisst overgangskontrakt. Hvis ett lag byttes før de andre, kan en offentlig e-post forsvinne eller en privat kontakt bli lest fra feil kilde.

Datamigrasjonen trenger regler for konflikter:

- Hva skjer når direktefelt og `PersonContact` har ulike verdier?
- Hvilken verdi er primær?
- Hvilke tidligere offentlige verdier kan fortsatt publiseres?
- Hvordan dokumenteres usikre tilfeller for manuell vurdering?
- Hvordan kan migrasjonen kjøres på nytt uten duplikater?

Dette er grunnen til at kontaktarkitekturen behandles som et eget, additivt og reverserbart prosjekt.

## Tenant-isolasjon

CRM-et er tenant-basert. Flere organisasjoner kan bruke samme plattform uten å se hverandres data. Mange modeller har derfor `tenant_id`.

Dette er ikke bare et frontendfilter. Isolasjonen må håndheves i:

- modellrelasjoner og databasevalg
- backend-spørringer
- serializer-validering
- roller og tilgangskontroll
- tester

En bruker kan sende API-kall utenom frontend. Backend må alltid kontrollere at objektet tilhører en tenant brukeren har tilgang til.

## Constraints og indekser

En **constraint**, eller databasebegrensning, hindrer ugyldig struktur. Eksempler i CRM-et er at:

- en tag og dens slug skal være unik innen samme tenant
- samme person ikke skal kobles to ganger til samme organisasjon i samme tenant
- en underkategori skal tilhøre en eksisterende kategori
- fremmednøkler må peke på gyldige rader

Slike regler beskytter data selv om en feil oppstår i API-et eller importen.

En **indeks** fungerer som registeret bakerst i en bok. Den gjør bestemte søk raskere. CRM-et har blant annet indekser som kombinerer tenant med navn, organisasjonsnummer, rolle eller kontaktverdi.

Indekser bruker plass og må oppdateres når data skrives. De bør velges ut fra reelle søkebehov, ikke legges til overalt.

## SQL og Djangos ORM

PostgreSQL forstår SQL, *Structured Query Language*:

```sql
SELECT *
FROM crm_organization
WHERE is_published = true;
```

Django bruker vanligvis en **ORM**, *Object-Relational Mapping*, som oversetter Python-kode til SQL:

```python
Organization.objects.filter(is_published=True)
```

ORM-en gjør relasjoner og vanlige spørringer lettere å uttrykke, men kan fortsatt brukes dårlig. Et kjent ytelsesproblem er **N+1**: én spørring henter en liste, og så kjøres én ny spørring for hver rad.

Hvis 100 organisasjoner hentes og kontaktpersonene leses i 100 tilleggskall, blir resultatet 101 spørringer. Django kan ofte samle dette med `select_related()` eller `prefetch_related()`.

## Transaksjoner

En databasetransaksjon grupperer flere endringer. Enten fullføres alle, eller så rulles de tilbake.

Ved import kan én rad kreve:

1. oppretting eller oppdatering av organisasjon
2. oppretting eller matching av person
3. lagring av kontaktkanal
4. oppretting av koblingen

Hvis siste steg feiler, kan det være tryggere å angre hele gruppen enn å etterlate halvferdige data.

En database-commit og en Git-commit er ikke samme ting. Git-commit lagrer kodehistorikk. Database-commit fullfører en transaksjon med CRM-data.

## Datamodellen og Django-modellene

Datamodellen beskriver hvilke data som finnes, hvilke typer de har, hvordan de kobles sammen, og hvilke verdier som kan være tomme eller unike.

I Django beskrives dette med Python-klasser:

```python
class Organization(models.Model):
    name = models.CharField(max_length=255)
    org_number = models.CharField(max_length=32, null=True, blank=True)
    is_published = models.BooleanField(default=False)
```

Å redigere klassen endrer ikke automatisk PostgreSQL-tabellen. Koden og databasestrukturen må bringes i samsvar gjennom migrasjoner.

## Hva er en migrasjon?

En migrasjon er en versjonert oppskrift for å endre databasestrukturen. Django bruker to ulike kommandoer:

```bash
docker compose exec api python manage.py makemigrations
docker compose exec api python manage.py migrate
```

`makemigrations` sammenligner modellene med tidligere migrasjoner og lager en ny migrasjonsfil. Den endrer normalt ikke databasen.

`migrate` kjører utestående migrasjoner mot databasen. Den kan legge til eller fjerne kolonner, endre constraints, opprette tabeller eller flytte data.

Migrasjonsfilen er kode og committes sammen med modellendringen. Databasen registrerer hvilke migrasjoner som allerede er kjørt, slik at Django bare utfører de manglende.

Nyttige kontroller er:

```bash
docker compose exec api python manage.py showmigrations
docker compose exec api python manage.py makemigrations --check
docker compose exec api python manage.py check
```

## Schema- og datamigrasjoner

En **schema migration** endrer strukturen, for eksempel en tabell, kolonne, datatype eller indeks.

En **data migration** endrer eksisterende innhold, for eksempel ved å:

- fylle et nytt felt
- dele én adresse i flere felter
- normalisere gamle verdier
- flytte kontaktdata til en ny modell

En migrasjon kan gjøre begge deler.

Å legge til et valgfritt tekstfelt er ofte lav risiko. Å gjøre organisasjonsnummer obligatorisk er langt mer krevende hvis hundrevis av eksisterende rader mangler nummeret. Da må vi bestemme hvordan de gamle dataene skal behandles før databasen kan håndheve den nye regelen.

Standardverdier må også vurderes mot eksisterende data. `default=False` kan være trygt for et nytt publiseringsfelt, mens en oppdiktet standardkommune ville skjule manglende kunnskap. En migrasjon skal ikke fylle et felt bare for å få kommandoen til å lykkes; verdien må være faglig riktig eller uttrykkelig ukjent. Valget dokumenteres fordi det påvirker alle gamle rader, ikke bare nye registreringer, og kan endre senere rapporter og filtre.

## Test med realistiske data

En migrasjon kan fungere på en tom lokal database og feile i produksjon. Et nytt unikt felt kan for eksempel møte duplikater som ikke finnes lokalt.

Risikable migrasjoner bør derfor prøves mot:

- anonymiserte eller syntetiske data som ligner virkeligheten
- eksplisitte tester for kjente konflikter
- stagingdatabasen
- eksisterende og nye arbeidsflyter

Kontrollen må omfatte oppretting, redigering, import, eksport, API og publisering når disse delene berøres. Vi må også vite om migrasjonen låser tabeller eller tar lang tid.

## Expand and contract

En trygg endring gjøres ofte i flere steg:

1. **Expand:** Legg til det nye uten å fjerne det gamle.
2. **Migrate:** Flytt data og la koden støtte begge variantene.
3. **Contract:** Fjern den gamle strukturen etter kontroll.

Hvis ett kontaktfelt skal erstattes, kan vi først opprette det nye feltet, kopiere data, bytte lesing og skriving, og fjerne det gamle i en senere leveranse.

Denne metoden gjør gammel og ny kode mer kompatibel under overgangen og gir flere muligheter til å stoppe.

## Tilbakerulling og backup

Django kan i enkelte tilfeller kjøre en migrasjon bakover:

```bash
docker compose exec api python manage.py migrate crm 0005
```

Dette er bare et eksempel på målrettet tilbakeføring og skal ikke kjøres uten at konsekvensen er undersøkt. Reversering av struktur gjenoppretter ikke nødvendigvis slettede data. En kolonne kan opprettes på nytt uten det tidligere innholdet. Derfor er migrasjonsrollback ikke en erstatning for backup.

Før en risikabel produksjonsmigrasjon må vi vite:

- når siste backup ble tatt
- hvor den ligger
- om den omfatter riktig database
- hvor lang gjenoppretting tar
- om gjenoppretting er testet
- hvem som kan utføre den

En vanlig PostgreSQL-backup kan lages med `pg_dump`, men produksjonskommandoen må følge prosjektets dokumenterte driftsoppsett. Jeg skal ikke improvisere databasebackup fra en generell bokkommando.

## Logisk, fysisk og tidsbasert backup

En **logisk backup** eksporterer databaseinnholdet til SQL eller PostgreSQLs eget backupformat. Den kan ofte gjenopprettes på en annen server og er nyttig når innholdet skal inspiseres eller flyttes.

En **fysisk backup** kopierer databaserelaterte filer eller diskblokker. Den kan være rask for store databaser, men må tas på en måte som er konsistent med PostgreSQL. En tilfeldig kopi av aktive databasefiler er ikke nødvendigvis en gyldig backup.

Mer moden drift kan bruke **point-in-time recovery**, der løpende transaksjonslogger gjør det mulig å gjenopprette databasen til et bestemt tidspunkt – for eksempel rett før en feilaktig masseimport. Dette gir bedre presisjon, men krever mer lagring, overvåkning og testet drift.

Prosjektet trenger ikke velge den mest avanserte løsningen først. Det må velge en dokumentert løsning som oppfyller faktisk RPO og RTO.

## Hvor gode må backupene være?

To begreper gjør behovet konkret:

- **RPO**, *Recovery Point Objective*: Hvor mye data kan vi akseptere å miste?
- **RTO**, *Recovery Time Objective*: Hvor lenge kan systemet være utilgjengelig?

Hvis backup tas én gang i døgnet, kan nesten ett døgns registrering gå tapt. Hvis CRM-et må være tilbake innen fire timer, må gjenopprettingsrutinen faktisk kunne klare det.

Backupen bør ligge et annet sted enn den aktive databasen, være kryptert, tilgangsbegrenset, tidsstemplet og testet. CRM-backup inneholder personopplysninger og må følge regler for tilgang, oppbevaring og sletting.

En backup som aldri er gjenopprettet i en test, er ikke et dokumentert sikkerhetsnett.

Gamle backuper inneholder fortsatt personopplysninger. En backup-policy må derfor angi hvor lenge de beholdes, hvem som kan bruke dem, og hva som skjer hvis slettede data gjeninnføres ved katastrofegjenoppretting.

En praktisk regel er at backup bare brukes til gjenoppretting, ikke som et skjult arkiv. Etter restore må slettinger og andre senere korreksjoner gjennomføres på nytt når det er påkrevd.

## Sletting, historikk og audit

**Hard delete** fjerner raden fysisk. Det er vanskelig å angre og kan påvirke relasjoner.

**Soft delete** beholder raden, men markerer den inaktiv eller slettet. Det bevarer historikk, men betyr også at personopplysningene fortsatt finnes og at alle spørringer må følge regelen.

`OrganizationPerson.status = INACTIVE` er relasjonsstatus, ikke sletting av personen.

En **auditlogg** registrerer hvem som endret hva, når og i hvilken tenant. Den er verdifull for feilsøking, import og ansvarlighet. Men auditlogg og backup har ulike jobber:

```text
Auditlogg = sporbarhet
Backup = gjenoppretting
```

Prosjektet har commit-logg for importjobber, men en komplett, generell auditlogg er fortsatt planlagt. Manualen skal ikke omtale den som ferdig.

## Import er databaseskriving i stor skala

Import påvirker mange modeller og må håndtere validering, matching, duplikater, forhåndsvisning, beslutninger, transaksjoner og feilrapport.

En **unique constraint** svarer på om nøyaktig samme verdi eller kombinasjon kan lagres to ganger. **Deduplisering** vurderer om to rader beskriver samme virkelige person eller aktør. Det siste krever faglige regler og ofte menneskelig godkjenning.

Databasen skiller også mellom `NULL` og tom tekst:

```text
NULL = ingen verdi
""   = en tekstverdi som er tom
```

Django skiller mellom `null=True`, som gjelder databasen, og `blank=True`, som påvirker validering. Uklare regler for tomme verdier gir problemer i import, filtrering og API.

Standardverdier har også betydning. `is_published = False` er en trygg standard fordi nye aktører ikke blir offentlige uten en bevisst beslutning.

## Sletting gjennom relasjoner

Django bruker `on_delete` til å bestemme hva som skjer med relaterte rader:

- `CASCADE`: relaterte rader slettes sammen med forelderen
- `PROTECT` eller `RESTRICT`: sletting stoppes
- `SET_NULL`: referansen settes tom hvis feltet tillater det

Ingen regel er alltid riktig. Valget påvirker dataintegritet, historikk, personvern og brukerforventning. Derfor er endring av en relasjons slettelogikk en arkitektur- og databaseendring, ikke en liten kodeopprydding.

## Sikkerhet og drift

Applikasjonens databasebruker bør ha minst mulig nødvendige rettigheter. PostgreSQL skal normalt ikke være åpen direkte mot internett. Tilgang skjer gjennom interne nettverk og kontrollert administrasjon.

Driften bør følge med på:

- diskplass og databasevekst
- minne og aktive forbindelser
- trege spørringer og låser
- feilmeldinger
- backupstatus

Et lite CRM trenger ikke maksimal driftskompleksitet, men det må oppdage at databasen nærmer seg en grense før den stopper.

Forbindelser er også en begrenset ressurs. Hver API-prosess og bakgrunnsjobb kan åpne databaseforbindelser. Når bruken vokser, kan en **connection pool** gjenbruke forbindelser og hindre at PostgreSQL overbelastes. For dagens størrelse kan et enkelt oppsett være nok, men import og flere samtidige prosesser må tas med i vurderingen.

Data må beskyttes både i transport og i ro. HTTPS og SSH beskytter nettverkstrafikk i relevante deler av flyten, mens kryptert disk og backup beskytter ved tyveri eller uautorisert tilgang til lagringen.

## En trygg modellendring i CRM-et

Ved et nytt felt:

1. Beskriv den faglige hensikten.
2. Velg datatype, tomverdi og standard.
3. Vurder tenant, publisering og personvern.
4. Oppdater Django-modellen.
5. Lag og les migrasjonen.
6. Oppdater serializer, API og frontendtype.
7. Test med eksisterende og nye data.
8. Kjør relevante automatiske tester.
9. Commit modell og migrasjon sammen.
10. Test på staging.
11. Bekreft backup ved produksjonsrisiko.
12. Kjør migrasjonen kontrollert og kontroller data og logger.

Ved sletting av et felt stopper vi først all lesing og skriving, flytter nødvendige data og deployer kompatibel kode. Selve kolonnen fjernes i en senere migrasjon.

### Kontrollert produksjonsmigrasjon

Før migrasjonen bekrefter jeg:

```bash
hostname
pwd
git branch --show-current
docker compose ps
```

Deretter må den dokumenterte deployrutinen gi svar på:

- kjører serveren riktig commit?
- er backupen fersk og gjenopprettbar?
- er dette riktig database?
- hvor lang tid og låsing forventes?
- kan gammel og ny kode kjøre under overgangen?
- hva er stopp- og tilbakeføringskriteriet?

Etter migrasjonen kontrollerer vi:

```bash
docker compose exec api python manage.py showmigrations
docker compose ps
docker compose logs --tail=100
```

Deretter testes relevante API-kall, oppretting, redigering, import og public-visning. Vi teller eller stikkprøver berørte data når migrasjonen har flyttet innhold.

Codex skal rapportere modeller, tabeller, migrasjonsfil, eksisterende data, reverserbarhet, testresultat og backupbehov. «Migrasjonen er laget» er ikke en tilstrekkelig leveranserapport.

## Vanlige databasefeil

**`No such column`** eller **`relation does not exist`** betyr ofte at migrasjoner mangler, at koden bruker feil database, eller at containeren har koblet seg til en tom database.

**`Unique constraint failed`** peker mot duplikater eller manglende normalisering.

**`Foreign key violation`** betyr at en relasjon peker feil, at importrekkefølgen er gal, eller at sletting bryter en avhengighet.

**`Null constraint violation`** betyr at et obligatorisk felt mangler. Gammel data eller importmapping kan være årsaken.

**Migration conflict** oppstår når branches lager migrasjoner fra samme utgangspunkt. Django kan trenge en kontrollert merge-migrasjon.

**Langvarig lås** kan gjøre API-et tregt eller utilgjengelig. Store endringer må planlegges med forventet varighet og påvirkning.

## Takeaways

- GitHub beskytter kodehistorikken; databasebackup beskytter CRM-innholdet.
- Tabeller, nøkler, relasjoner og constraints former systemets virkelige datastruktur.
- `makemigrations` lager oppskriften; `migrate` endrer databasen.
- Risikable migrasjoner må testes med realistiske data og en verifisert vei tilbake.
- Import, sletting og kontaktomlegging er databasearbeid, ikke bare filendringer.
- Auditlogg gir sporbarhet, mens backup muliggjør gjenoppretting.

## Prinsippet

En databaseendring endrer prosjektets virkelige hukommelse og skal behandles deretter.
