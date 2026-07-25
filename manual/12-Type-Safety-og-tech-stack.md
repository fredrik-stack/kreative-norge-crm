# Kapittel 12 – Type Safety og tech stack: hvordan lagene kan være enige

Kreative Norge CRM består av flere tekniske lag:

```text
React + TypeScript
→ REST API med JSON
→ Django + Python
→ PostgreSQL
```

Alle arbeider med navn, kommuner, publiseringsstatus, kategorier, tags og kontaktpersoner. Mange feil oppstår ikke fordi ett lag er ødelagt, men fordi to lag forventer forskjellig form på samme verdi.

Typesikkerhet hjelper lagene å oppdage slike avvik før brukeren møter dem.

## Hva er en type?

En type beskriver hva slags verdi noe er:

| Type | Eksempel |
| --- | --- |
| Tekst | `"Tromsø"` |
| Heltall | `42` |
| Desimaltall | `42.5` |
| Boolsk verdi | `true` eller `false` |
| Liste | `["Tromsø", "Bodø"]` |
| Objekt | `{"name": "Festivalen"}` |
| Tom verdi | `null` |
| Dato som JSON-tekst | `"2026-07-22"` |

Typen avgjør hvilke operasjoner som gir mening. `is_published` skal være en boolsk verdi, ikke teksten `"ja"` eller `"true"`.

**Type Safety**, eller typesikkerhet, betyr at systemet bruker regler for å varsle eller stoppe når en verdi brukes på en måte som ikke passer typen.

## Typesikkerhet i flere lag

CRM-et har ikke ett felles typesystem. Hvert lag har egne regler.

**PostgreSQL** bruker datatyper som tekst, heltall, boolsk verdi og tidsstempel. Databasen kan nekte enkelte ugyldige verdier.

**Django-modellene** beskriver feltene i Python:

```python
name = models.CharField(max_length=255)
is_published = models.BooleanField(default=False)
created_at = models.DateTimeField(auto_now_add=True)
```

**Serializerne** validerer hva API-et mottar og returnerer, inkludert relasjoner, tenant og egendefinerte regler.

**OpenAPI** beskriver kontrakten maskinelt slik at mennesker og verktøy kan lese den.

**TypeScript** beskriver hva React forventer:

```typescript
type Organization = {
  id: number;
  name: string;
  municipalities: string;
  is_published: boolean;
};
```

Dagens frontend har `strict: true` i TypeScript-konfigurasjonen. Det gir strengere kontroll av blant annet `null`, parametere og returverdier, men det garanterer ikke at API-et faktisk sender riktig data i produksjon.

## Python og TypeScript kontrollerer på ulike tidspunkt

Python er i hovedsak dynamisk typet. En variabel kan få ulike typer mens programmet kjører. Type hints gjør forventningen tydeligere:

```python
def normalize_phone(value: str) -> str | None:
    ...
```

Statiske analyseverktøy kan kontrollere slike hints, men Python håndhever dem ikke automatisk på samme måte som en kompilator.

TypeScript analyserer typer før frontend bygges:

```typescript
let municipality: string = "Tromsø";
municipality = 42; // typefeil
```

TypeScript blir deretter til JavaScript, som nettleseren kjører. Typeinformasjonen beskytter derfor utviklingen og bygget, ikke alle data som kommer inn mens programmet kjører.

## Type, format, mening og tilgang

Typesikkerhet løser bare en del av problemet:

- **Type:** `org_number` er tekst.
- **Format:** verdien består av ni sifre.
- **Forretningsregel:** nummeret tilhører riktig virksomhet.
- **Tilgangsregel:** brukeren kan endre denne tenantens organisasjon.
- **Publiseringsregel:** private kontakter skal ikke vises offentlig.

Et felt kan ha riktig type og fortsatt være feil, gammelt eller ulovlig å bruke. Typer, validering, tilgang og faglige regler må virke sammen.

## `null`, tom tekst og manglende felt

Disse tre tilstandene er forskjellige:

```json
{"phone": null}
```

```json
{"phone": ""}
```

```json
{"name": "Eksempel"}
```

I siste objekt mangler `phone` helt. I JavaScript blir en manglende verdi ofte `undefined`.

Hvis frontendtypen sier:

```typescript
type Person = {
  phone: string;
};
```

men API-et kan returnere `null`, er typen feil. Den bør være:

```typescript
type Person = {
  phone: string | null;
};
```

Alternativt må backend standardisere kontrakten. Det avgjørende er at alle lag følger samme regel.

## Lister, ID-er, datoer og enums

En enkeltverdi og en liste er ulike typer:

```json
{"municipalities": "Tromsø, Bodø"}
```

```json
{"municipalities": ["Tromsø", "Bodø"]}
```

Dagens CRM bruker første form som tekst. En overgang til liste vil påvirke modell, migrasjon, serializer, frontend, import, eksport og public API.

Interne database-ID-er er vanligvis tall. Eksterne systemer kan bruke tekst eller UUID. En tydelig modell skiller:

```typescript
type InternalId = number;
type ExternalId = string;
```

Datoer transporteres ofte som tekst i JSON, men representerer et tidspunkt. Frontend må vite format, tidssone og om verdien kan være tom.

Et **enum** begrenser et felt til bestemte verdier. `OrganizationPerson.status` kan være:

```typescript
type RelationshipStatus = "ACTIVE" | "INACTIVE";
```

Hvis `PENDING` legges til, må database, Django, serializer, frontend, filtre, import og tester oppdateres. Det er nyttig at endringens fulle omfang blir synlig.

## Kontrakten kan drive fra hverandre

Django og TypeScript beskriver ofte samme begrep i separate filer:

```python
name = models.CharField(max_length=255)
```

```typescript
type Organization = {
  name: string;
};
```

Hvis backend endres uten at frontend oppdateres, oppstår **contract drift**: kontrakten og klientens forventning glir fra hverandre.

En enkel løsning er manuell oppdatering og gode tester. En mer automatisert løsning er:

```text
Django serializers
→ OpenAPI-schema
→ genererte TypeScript-typer
→ frontend-build
```

Det kan redusere duplisering og gjøre kontraktsendringer synlige. Det krever samtidig et presist OpenAPI-schema og en vedlikeholdt genereringsflyt.

En generert API-klient kan i tillegg gi standardfunksjoner som `getOrganizations()` og `updatePerson()`, i stedet for mange håndskrevne `fetch`-kall.

Dette er mulige forbedringer. Repoet har OpenAPI og håndskrevne TypeScript-typer, men automatisk type- eller klientgenerering er ikke verifisert som implementert.

Kontrakter kan også beskyttes med tester. En kontrakttest kan kontrollere at et offentlig endepunkt fortsatt returnerer avtalte felter og typer. Frontend-build kan feile dersom en generert type ikke lenger passer koden.

En slik flyt må være enkel nok til å brukes hver gang. Hvis generering krever manuelle spesialsteg som ingen husker, oppstår drift mellom schema, genererte filer og faktisk API på en ny måte.

Det viktigste er én definert sannhetskjede:

```text
serializer og eksplisitt schema
→ OpenAPI
→ frontendtype eller kontrakttest
→ brukergrensesnitt
```

Når kjeden brytes, skal CI – det automatiske testmiljøet – eller lokale tester gjøre avviket synlig før deploy.

## Database-, API- og UI-modell er ulike

Det er ikke alltid riktig å dele én stor type overalt.

**Databasemodellen** inneholder det som må lagres, også interne felt og tenant-ID.

**API-modellen** inneholder det klienten har lov til å sende eller motta.

**UI-modellen** inneholder det en bestemt side eller komponent trenger.

Et **DTO**, *Data Transfer Object*, er en struktur laget for dataoverføring:

```typescript
type PublicActorCard = {
  name: string;
  municipalities: string;
  image_url: string | null;
  primary_category: string | null;
};
```

DTO-en trenger ikke inneholde interne notater, importdata eller private kontakter. Tydelige offentlige typer reduserer risikoen for at interne felt lekker ut.

Typesikkerhet alene håndhever ikke tenant-isolasjon. En `id: number` sier ikke hvilken tenant objektet tilhører. Backend-spørringer, URL-er, autorisasjon, databaseforhold og tester må fortsatt sikre skillet.

### Kontaktdata viser hvorfor modellene må skilles

Den interne personmodellen kan inneholde direkte e-post og telefon, flere `PersonContact`-rader, notater og tenantinformasjon. En offentlig kontaktprojeksjon skal bare inneholde kontaktkanaler som er godkjent i riktig organisasjonssammenheng.

Hvis frontend bruker en generell `Person`-type i public-visningen, blir det lettere å returnere et internt felt ved en feil. En mindre `PublicContact`-type gjør hensikten tydelig:

```typescript
type PublicContact = {
  type: "EMAIL" | "PHONE";
  value: string;
};
```

Dette er ikke nok alene. Backend må fortsatt velge riktig datakilde og håndheve publiseringsreglene. Men en avgrenset DTO gjør feil bruk vanskeligere og lekkasje lettere å oppdage i review.

Dagens doble kontaktarkitektur viser også at like TypeScript-typer ikke skaper én sannhet hvis dataene finnes i to backendmodeller. Typesikkerheten må bygge på en avklart datamodell.

## Runtime-validering

Et API-svar kan være feil selv om TypeScript-koden bygget uten feil. **Runtime-validering** kontrollerer data mens programmet kjører.

Et schema kan kontrollere at:

- alle nødvendige felt finnes
- typer og enumverdier er gyldige
- ukjente verdier håndteres
- en forståelig feil logges

Dette er særlig nyttig for eksterne API-er, importfiler, miljøvariabler og AI-resultater. Et schema-bibliotek kan koble validering og TypeScript-typer, men blir også en ny avhengighet som må vedlikeholdes.

## Python type hints og Django

Python type hints kan gjøre funksjoner og tjenestelag tydeligere:

```python
def find_public_contacts(person_id: int) -> list[str]:
    ...
```

Statiske typekontrollere kan oppdage feil returtype, manglende `None`-håndtering og enkelte ugyldige kall.

Django er samtidig dynamisk. Modellfelt blir attributter, relasjoner oppretter managers, og serializers bygger mye struktur gjennom rammeverket. God typing kan derfor kreve tilpassede typedefinisjoner eller plugins, tydelige tjenestelag og disiplin.

Målet er ikke maksimal typing av hver linje. Vi bør prioritere grensene der feil er dyre:

- servicefunksjoner som endrer data
- import og normalisering
- offentlig projeksjon
- adaptere for eksterne API-er
- funksjoner som kan returnere `None`
- delte kontrakter mot frontend

Typesikkerhet er et spektrum. Sterke databasefelt og TypeScript-typer hjelper lite hvis et uvalidert dictionary sendes mellom dem.

## `any` og `unknown`

TypeScript-typen `any` slår i praksis av kontrollen:

```typescript
const response: any = await fetchData();
```

Mye `any`, type assertions eller ignorerte feil kan gjøre et TypeScript-prosjekt langt mindre typesikkert enn navnet tilsier.

`unknown` er tryggere for eksterne data:

```typescript
const data: unknown = await response.json();
```

Da må strukturen valideres før koden behandler dataene som en kjent type.

## Import og AI-output

Importdata kan inneholde `JA`, `yes`, `1`, `true` eller `publisert`, selv om målfeltet er boolsk.

Importflyten må:

1. lese råverdien
2. normalisere kjente varianter
3. validere
4. konvertere
5. rapportere ukjente verdier
6. lagre først etter kontroll

Et AI-resultat kan leveres som strukturert JSON:

```json
{
  "website_url": "https://example.no",
  "municipality": "Tromsø",
  "confidence": 0.91
}
```

Backend må fortsatt kontrollere felter, typer, URL, tillatte verdier, kilde og sikkerhetsnivå. AI-output er ekstern input, ikke intern sannhet.

## Adaptere beskytter den interne modellen

Eksterne leverandører bruker egne feltnavn og begreper. Et **adapterlag** oversetter svaret til en intern type:

```text
ekstern respons
→ leverandøradapter
→ intern kandidat eller DTO
→ CRM-regler
```

Det hindrer at hele kodebasen blir avhengig av leverandørens råformat. Adapteren kan testes isolert og oppdateres når API-versjonen endres.

Oversettelsen må bevare mening, ikke bare kopiere feltnavn. En `attendee` i et påmeldingssystem er ikke automatisk en CRM-person med markedsføringssamtykke.

## Hva er en tech stack?

En **tech stack** er kombinasjonen av teknologier prosjektet bygger på.

Den verifiserte hovedstacken er:

- **Frontend:** React, TypeScript og Vite
- **Backend:** Python, Django og Django REST Framework
- **Database:** PostgreSQL
- **Drift:** Docker, nginx og Linux-server
- **Historikk og samarbeid:** Git og GitHub
- **AI i import:** OpenAI API når aktivert

Google Sheets, Checkin og Mailmojo er reserverte importtyper, ikke ferdige integrasjoner. Andre mulige eksterne tjenester må også omtales som planlagte til kode og test viser noe annet.

En tech stack er ikke bare en liste. Delene må kunne bygges, testes, sikres, driftes og vedlikeholdes sammen.

## Teknisk gjeld er mer enn gammel teknologi

Teknisk gjeld er valg som gjør fremtidig arbeid dyrere. Eksempler er:

- dupliserte eller motstridende typer
- manglende kontrakttester
- hardkodede hemmeligheter
- utydelige modulgrenser
- manuelle deploysteg uten kontroll
- avhengigheter uten oppdateringsrutine
- dokumentasjon som ikke stemmer med kode

En ny stack kan få teknisk gjeld fra første dag. En eksisterende stack kan forbedres. «Ny» og «ryddig» er ikke synonymer.

Stacken bør vurderes jevnlig mot støttede versjoner, sikkerhetsoppdateringer, kompetanse, ytelse og produktbehov. Kontinuerlig vurdering betyr ikke kontinuerlig omskriving. Stabilitet og kjent drift har også verdi.

## Hvordan vurdere en stack

Et teknologivalg må vurderes mot:

1. produktbehov og datamodell
2. teamets kompetanse og vedlikeholdsevne
3. økosystem, dokumentasjon og sikkerhetsoppdateringer
4. utviklingshastighet og testverktøy
5. drift, logging, backup og kostnad
6. migreringskostnad fra eksisterende løsning

For et etablert system teller ikke bare hvor raskt en tom prototype kan bygges. Modeller, migrasjonshistorikk, autentisering, roller, API, import, public-visning, tester og eksisterende data må følge med.

## Django er et helt økosystem

Django er ikke bare Python-syntaks. Rammeverket gir blant annet ORM, migrasjoner, autentisering, sessions, sikkerhetsmekanismer, URL-routing og administrasjon.

Django REST Framework gir serializers, API-visninger, permissions, validering og paginering.

Å bytte backend betyr å erstatte eller gjenbygge disse delene. PostgreSQL kan beholdes, men ORM, migrasjonsverktøy og validering vil endres.

## «Node.js» er ikke én løsning

Node.js er et kjøremiljø for JavaScript på serveren. Et konkret forslag må også velge rammeverk, ORM, autentisering, validering, testing og deployoppsett.

Et Node-/TypeScript-oppsett kan gi:

- samme hovedspråk i frontend og backend
- mulighet for delte verktøy og typer
- god tilpasning til utviklerens kompetanse
- et stort webøkosystem

Men TypeScript i begge lag fjerner ikke behovet for API-kontrakter, runtime-validering, databaseconstraints og tester. Database-, API- og UI-modell vil fortsatt ha ulike ansvar.

Ingen overgang fra Django til Node er besluttet eller planlagt som implementering. Det er et arkitekturspørsmål som krever dokumentert gevinst og godkjent beslutning.

## CRM og CMS løser ulike problemer

Et **CMS**, *Content Management System*, er laget for redaksjonelt innhold som sider, artikler, bilder og publisering. Et **CRM** organiserer personer, aktører, relasjoner, kontaktkanaler, segmenter og arbeidsprosesser.

Kreative Norge CRM har behov fra begge verdener. Et CMS kan tilby et godt redaktørgrensesnitt, men kan tvinge komplekse CRM-relasjoner, import og tenant-isolasjon inn i en modell de ikke passer.

Spørsmålet er derfor ikke «CMS eller ikke», men hvilken del som skal være autoritativt system for hvilke data.

## Monolitt, moduler og flere tjenester

CRM-et har i hovedsak én Django-backend og kan beskrives som en monolitt. Det er ikke et skjellsord.

Fordelene er:

- én hoveddeploy
- én database
- enklere transaksjoner
- færre nettverksgrenser
- enklere lokal utvikling og feilsøking

En **modulær monolitt** beholder én deploybar applikasjon, men deler logikken i tydelige områder som organisasjoner, personer, import, eksport, public og autentisering.

En hybrid med flere språk og tjenester kan være riktig når den løser et konkret problem. Den gir også flere builds, avhengigheter, logger, deployprosesser og sikkerhetsoppdateringer. Kompleksiteten må forsvares av gevinsten.

En mellomløsning kan være å beholde Django og PostgreSQL, men styrke OpenAPI-kontrakten og frontendtypene. Et separat CMS kan eventuelt brukes til rent redaksjonelt innhold, mens CRM-et beholder relasjoner og kontaktdata.

En ny Node-tjeneste kan passe for en avgrenset integrasjon eller hendelsesflyt. Samtidig innfører den en ny driftsenhet. Mikrotjenester skal derfor løse et identifisert problem, ikke bare gjøre arkitekturdiagrammet mer moderne.

## Hvordan avgjøre Django mot Node

Beslutningen skal ikke bygge på at én teknologi virker moderne eller at én person foretrekker den.

En seriøs prosess er:

1. Dokumenter dagens funksjoner, data, API, sikkerhet, drift og tester.
2. Beskriv den konkrete alternative stacken, ikke bare «Node».
3. Definer målbar gevinst.
4. Lag eventuelt en avgrenset prototype med CRUD, tenant og relasjoner.
5. Sammenlign typesikkerhet, vedlikehold, testbarhet, drift og kostnad.
6. Beregn omskriving, datamigrasjon, dobbelt vedlikehold og tapt fremdrift.
7. Ta en eksplisitt arkitekturavgjørelse før større implementering.

Mulige utfall er å beholde Django, styrke kontraktene i dagens stack, bruke Node til en avgrenset tjeneste eller gjennomføre en senere migrering. En prototype er et beslutningsgrunnlag, ikke automatisk ny hovedløsning.

En representativ prototype må teste mer enn en enkel liste. Den bør omfatte CRUD, tenant-isolasjon, autentisering, minst én relasjon, validering, migrasjon og relevante tester. Ellers sammenligner vi en tom demo med et ferdig CRM og får et misvisende resultat.

Kostnadsberegningen må ta med:

- omskriving og datamigrasjon
- dobbelt vedlikehold i overgangsperioden
- nye feil og tap av moden funksjonalitet
- test, dokumentasjon og deploy
- opplæring og leverandørbinding
- tapt tid til prioriterte produktbehov

Typesikkerhet er en mulig gevinst, men den må måles mot hva som kan oppnås ved å forbedre dagens kontrakter.

## En trinnvis Type Safety-plan

Typesikkerheten kan styrkes uten full omskriving:

1. Behold `strict: true`, reduser `any`, og bruk presise typer for sentrale modeller.
2. Gjør serializer- og OpenAPI-schema mer presise.
3. Vurder genererte TypeScript-typer og kontrakttester.
4. Valider eksterne API- og AI-responser ved runtime.
5. Bruk adaptere og interne DTO-er.
6. Utvid Python type hints og statisk analyse der det gir verdi.
7. Dokumenter modulgrenser og breaking changes.

Dette er en forbedringsretning, ikke en påstand om at alle stegene allerede er implementert.

Hvert nivå bør ha et konkret mål. «Bedre typer» er for uklart. Et mål kan være at en endring fra tekst til `null`-bar tekst skal stoppe frontend-build, at alle AI-responser valideres før lagring, eller at public API har kontrakttester for kontaktfeltene.

Før nye biblioteker innføres bør vi kontrollere om de reduserer faktisk risiko eller bare flytter definisjonene til enda et schema.

## Breaking changes og API-versjonering

En **breaking change** gjør at en eksisterende klient ikke lenger fungerer.

Før:

```json
{"municipality": "Tromsø"}
```

Etter:

```json
{"municipalities": ["Tromsø"]}
```

Endringen kan være faglig riktig, men klienter som forventer det gamle feltet vil feile.

Et offentlig API kan ved større kontraktsendringer trenge versjonering, for eksempel `/api/v1/` og `/api/v2/`. Prosjektet har ikke en ferdig versjonert public-kontrakt. Behovet må avklares før Musikkontoret.no blir avhengig av API-et.

## Når et felt endrer type

Codex må kartlegge mer enn Django-modellen:

- database og migrasjon
- serializer og OpenAPI
- frontendtype og skjema
- API-kall og filterlogikk
- import og eksport
- public API
- tester og dokumentasjon

Et nytt API-felt må få definert betydning, datatype, `null`-regel, tilgang og publiseringsregel. Tom verdi må testes eksplisitt.

Ved eksternt API behandles responsen som `unknown`, valideres, oversettes i en adapter og blir først deretter en intern DTO.

## Spørsmål som gjør stackdiskusjonen konkret

Når noen foreslår en ny backend, et CMS eller en hybrid, spør jeg:

1. Hvilket konkret rammeverk, ORM og valideringsverktøy foreslås?
2. Hvem eier CRM-dataene og migrasjonshistorikken?
3. Hvordan håndteres tenant-isolasjon, roller og public API?
4. Hvordan oppnås typesikkerhet fra database til frontend?
5. Hvor valideres data mens systemet kjører?
6. Hvordan flyttes eksisterende data uten tap?
7. Hvordan testes, deployes, overvåkes og sikkerhetsoppdateres løsningen?
8. Hvilken målbar svakhet i dagens Django-stack løser byttet?
9. Hva er total tidsbruk, kostnad og tilbakeføringsmulighet?

Disse spørsmålene flytter samtalen fra teknologipreferanse til arkitektur og produktansvar.

## Takeaways

- Typesikkerhet holder formen på data konsistent, men erstatter ikke faglige regler eller tilgangskontroll.
- PostgreSQL, Django, serializers, OpenAPI og TypeScript beskytter på ulike steder.
- `null`, lister, ID-er, datoer og enums må ha én tydelig kontrakt.
- Ekstern data og AI-output må valideres mens systemet kjører.
- Den eksisterende stacken kan få sterkere kontrakter uten full omskriving.
- Teknologibytte krever målbar gevinst, prototype og godkjent arkitekturavgjørelse.

## Prinsippet

Velg teknologi fordi den beskytter dataene, støtter produktet og kan vedlikeholdes – ikke fordi den virker gammel eller moderne.
