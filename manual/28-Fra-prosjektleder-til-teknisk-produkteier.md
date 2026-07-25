# Kapittel 28 – Fra prosjektleder til teknisk produkteier

Da jeg begynte med Kreative Norge CRM, hadde jeg ikke utviklerutdanning. Jeg hadde derimot kunnskap om feltet, behovene og hvorfor produktet burde finnes. Gjennom arbeidet oppdaget jeg en tredje rolle mellom prosjektleder og utvikler: den tekniske produkteieren.

Jeg trenger ikke skrive all koden selv. Jeg trenger å forstå nok til å stille gode spørsmål, ta bevisste valg og se når tekniske beslutninger påvirker produktet.

## Hva rollen innebærer

En tradisjonell prosjektleder følger gjerne tid, budsjett og leveranser. En produkteier prioriterer brukerbehov og bestemmer hva som skal bygges. Den tekniske produkteieren kobler dette til en praktisk forståelse av arkitektur, data, integrasjoner, sikkerhet, testing, deploy, drift og risiko.

Det betyr ikke at jeg skal vite alt. Profesjonelle utviklere gjør heller ikke det. Forskjellen ligger i metoden: Jeg kan undersøke et ukjent begrep, følge en dataflyt, be om alternativer og kontrollere påstander mot kode, tester og dokumentasjon.

Produktkunnskapen min er fortsatt avgjørende. Teknisk god kode kan løse feil problem dersom ingen beskytter formålet. I CRM-et må noen forstå hva en aktør, person, relasjon, kategori, tenant og publiseringsbeslutning betyr i praksis. Det ansvaret kan ikke delegeres til et kodeverktøy.

## Samarbeidet med AI

AI har gjort avstanden mellom idé og fungerende programvare mindre. ChatGPT kan hjelpe meg å undersøke behov, utfordre antakelser, formulere beslutninger og lage en tydelig oppgave. Codex kan lese repoet, spore kode og data, implementere avgrensede endringer og kjøre tester.

Grensen mellom verktøyene er ikke absolutt. Det viktige er at arbeidet etterlater spor som andre kan kontrollere: beslutninger i ADR-er, stabil kunnskap i dokumentasjonen, endringer i Git og verifisering i tester og staging.

AI overtar ikke ansvaret. Jeg må fremdeles avgjøre:

- hvilket problem vi faktisk løser
- hvilke brukere og data som berøres
- hva som er godt nok nå
- hvilke risikoer som kan aksepteres
- hvordan resultatet skal kontrolleres

Et godt samarbeid er kontinuerlig. Jeg gir kontekst og rammer, AI foreslår eller utfører arbeid, og jeg vurderer resultatet mot produktbehovet. Det er tryggere enn å levere en vag bestilling og vente på et ferdig svar.

## Spørsmål som gir bedre beslutninger

Når jeg ikke forstår en løsning, prøver jeg å gjøre usikkerheten konkret:

1. Hvilket problem løser denne endringen?
2. Hvor i systemet hører ansvaret hjemme?
3. Hvilke data leses eller endres?
4. Hva kan gå galt for brukeren?
5. Finnes det en enklere løsning?
6. Hvordan kan vi teste at resultatet er riktig?
7. Hvordan oppdager vi feil etter lansering?
8. Kan endringen rulles tilbake?

Spørsmålene gjør ikke alle valg enkle. De synliggjør avveiningene. En rask løsning kan gi læring, men også teknisk gjeld. Streng validering kan beskytte data, men blokkere legitime unntak. Mer automatisering kan spare tid, men gjøre feil mindre synlige. Min oppgave er å velge bevisst og dokumentere hvorfor.

## Beskytt produktets kjerne

Kjernen i Kreative Norge CRM er ikke skjermbildene. Den er forståelsen av aktører, personer, relasjoner, segmentering, tenant-grenser og kontrollert publisering. Brukergrensesnitt, importer og integrasjoner kan endres, men disse begrepene må forbli tydelige.

Dataansvar følger samme tanke. Jeg må vite hvor en opplysning kommer fra, hvem som kan se og endre den, om den kan publiseres, og hvilket felt som er autoritativt når flere kilder finnes. Hvis dette er uklart, kan en teknisk vellykket automatisering likevel skade tillit eller personvern.

Tre deler av CRM-et viser hvorfor:

### Import

En import handler ikke bare om å lese et regneark. Systemet må normalisere data, finne mulige treff, vise usikre valg og bevare brukerens beslutning før noe lagres. Her beskytter den tekniske produkteieren både datakvalitet og arbeidsflyt.

### AI-berikelse

AI kan foreslå informasjon, men forslaget er ikke automatisk sannhet. Kilder, usikkerhet, kostnader, personvern og reserveflyt må vurderes. Brukeren trenger kontroll over hva som godkjennes.

### Publisering

Offentlig visning krever mer enn at data finnes i databasen. Organisasjonen må være publiserbar, og kontaktopplysninger eller andre felt må følge vedtatte regler. Her møtes datamodell, tilgang, personvern og produktløfte.

## Slik gjør jeg AI-arbeidet styrbart

AI gir bedre arbeid når oppgaven har et tydelig mål, relevant kontekst og avgrenset omfang. Jeg oppgir hvilke filer eller deler av produktet som er berørt, hvilke regler som gjelder, og hvordan resultatet skal verifiseres. Ved større valg bruker vi prosjektets rekkefølge:

1. Diagnostiser behovet eller problemet.
2. Ta og dokumenter beslutningen.
3. Implementer en avgrenset endring.
4. Kjør relevante tester.
5. Kontroller resultatet i riktig miljø.
6. Oppdater dokumentasjon og status.

Prosjektets dokumentasjon, ADR-er og lokale skills gjør denne arbeidsformen repeterbar. De reduserer behovet for å gjenskape viktig kontekst i hver samtale og gjør det lettere å komme tilbake etter et langt opphold.

## Teknisk trygghet uten å late som

Teknisk trygghet betyr ikke at jeg kjenner svaret på forhånd. Det betyr at jeg vet hvordan jeg kan finne det: lese dokumentasjonen, be om en forklaring, kontrollere kode og data, sammenligne alternativer og teste en avgrenset hypotese.

Jeg har særlig lært å unngå fire feller:

- å delegere hele produktforståelsen til AI
- å miste brukerbehovet i tekniske detaljer
- å detaljstyre kode uten å forstå konsekvensen
- å la viktige beslutninger bli liggende i samtaler

Den beste arbeidsdelingen utnytter ulike styrker. Jeg kjenner formålet, feltet og prioriteringene. AI hjelper med analyse, presisjon og gjennomføring. Kode, tester, dokumentasjon og Git gir et felles, kontrollerbart minne.

## Når jeg kommer tilbake til prosjektet

Etter et opphold trenger jeg ikke huske alle detaljer. Jeg kan begynne med prosjektstatusen, de relevante ADR-ene og arbeidsflyten. Deretter kan jeg kontrollere siste commits, kjøre systemet lokalt og se hva staging faktisk viser.

Før jeg starter nytt arbeid, spør jeg:

- Er funksjonen dokumentert som implementert, planlagt eller uavklart?
- Stemmer dokumentasjonen med kode og tester?
- Krever endringen en arkitekturbeslutning?
- Hvilke data og brukergrupper berøres?
- Hva er minste nyttige og trygge leveranse?
- Hvordan skal den testes, settes ut og driftes?

Denne rutinen gjør at jeg kan gjenoppta arbeidet uten å basere meg på hukommelse eller gamle samtaler.

## Avslutning

Kreative Norge CRM har lært meg at teknisk produktarbeid ikke først og fremst handler om å kunne skrive mest kode. Det handler om å holde sammen problem, bruker, data, beslutning og gjennomføring.

AI gjør det mulig for meg å arbeide tettere på teknologien enn før. Men verdien oppstår først når jeg bruker verktøyet med tydelige mål, kritiske spørsmål og ansvar for resultatet. Retningen må fortsatt velges av et menneske.

## Takeaways

- Jeg trenger ikke være utvikler for å ta informerte tekniske produktvalg.
- Produktkunnskap og teknisk forståelse må brukes sammen.
- AI kan analysere og gjennomføre, men jeg beholder ansvar for retning og risiko.
- Beslutninger må bli igjen i dokumentasjon, kode, tester og Git.
- Teknisk trygghet er en metode for å undersøke det jeg ikke vet.
- Produktets kjerne og dataansvar skal styre prioriteringene.

## Prinsippet

Den tekniske produkteieren trenger ikke kunne alt, men må kunne stille spørsmålene som holder produkt, teknologi og ansvar samlet.
