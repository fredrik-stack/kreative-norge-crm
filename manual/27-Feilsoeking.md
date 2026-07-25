# Kapittel 27 – Feilsøking

Når noe ikke virker, er det fristende å endre kode med en gang. Jeg har lært at god feilsøking begynner tidligere: med en presis beskrivelse, et gjentakbart symptom og bevis for hvor resultatet først blir feil.

## Beskriv problemet før løsningen

«Importen virker ikke» er for uklart. En nyttig feilbeskrivelse sier hva jeg gjorde, hva jeg forventet, hva som faktisk skjedde, hvilke data det gjaldt og i hvilket miljø feilen oppstod. Deretter prøver jeg å gjenskape den med færrest mulige steg.

Det er viktig å vite om feilen finnes lokalt, i staging eller begge steder. Ulik kodeversjon, konfigurasjon eller data kan gi samme synlige symptom. Hvis problemet ikke kan gjenskapes, dokumenterer jeg det vi faktisk vet i stedet for å late som årsaken er funnet.

Jeg skiller også mellom kodefeil, datafeil og konfigurasjonsfeil. En regel kan være riktig implementert, men få uventede data. Koden kan fungere lokalt, mens en miljøvariabel mangler i staging. Denne inndelingen hindrer at alle problemer automatisk behandles som behov for ny kode.

## Følg dataene gjennom systemet

En feil kan ligge i nettleseren, React-grensesnittet, API-et, Django, en serializer som oversetter data, forretningslogikken, databasen, Docker, nginx, serveren, DNS eller en ekstern tjeneste. Jeg trenger ikke forstå alle lagene på forhånd. Jeg må finne det første punktet der riktig informasjon blir til et feil resultat.

For en manglende verdi kan jeg følge denne kjeden:

1. Finnes verdien i databasen?
2. Velger modellen og forretningsreglene riktig verdi?
3. Sender API-et verdien?
4. Mottar nettleseren den?
5. Viser komponenten den?

Når et ledd er riktig og det neste er feil, er søkeområdet blitt mye mindre.

Verktøyene gir ulike typer bevis. Nettleserens utviklerverktøy viser forespørsler, svar og feil i grensesnittet. Django- og Docker-logger viser hva serveren gjorde. Databaseverktøy viser hvilke data som faktisk finnes. Hele feilmeldingen og stack trace, altså sporingen av hvor feilen oppstod, er som regel mer verdifull enn den siste røde linjen alene.

## Én hypotese om gangen

En hypotese skal kunne testes: «Staging viser gammel kode fordi siste versjon ikke er deployet» er bedre enn «det er noe galt med serveren». Jeg gjør én avgrenset kontroll eller endring, tester igjen og beholder bare endringen hvis resultatet støtter forklaringen.

Flere samtidige endringer gjør det vanskelig å vite hva som virket og kan introdusere nye feil. `git diff` viser hva som er endret, mens commit-historikken hjelper meg å finne når oppførselen skiftet. En liten rettelse bør også få en test som ville ha oppdaget feilen.

Før jeg endrer noe, kontrollerer jeg dessuten om testen allerede beskriver ønsket oppførsel. Hvis test og dokumentasjon er uenige, har vi ikke bare en kodefeil, men en beslutning som må avklares. Da stopper jeg implementeringen til forventningen er tydelig.

## Tre eksempler fra CRM-et

### Staging viser gammel oppførsel

Først sammenligner jeg aktiv commit i staging med commit-en jeg forventet. Deretter kontrollerer jeg deploy-logg og om riktig container kjører. Hvis versjonene ikke stemmer, trenger jeg ikke begynne å omskrive funksjonen.

### Importen lager dubletter

Jeg følger én rad gjennom opplasting, normalisering, matching, brukerens gjennomgang og lagring. Feilen kan skyldes ulike skrivemåter, feil identifikator, manglende organisasjonsnummer eller at valget fra gjennomgangen ikke blir bevart. Først når det første avviket er funnet, vet jeg hvor rettelsen hører hjemme.

### Kontaktinformasjon mangler offentlig

Jeg kontrollerer først om opplysningen finnes på organisasjonen eller personen, og om den er godkjent for publisering. Så ser jeg på serializer og API-svar før visningslaget. En rask endring i malen kan skjule symptomet uten å løse uenigheten om hvilken kontaktopplysning som er autoritativ.

## AI som feilsøkingspartner

AI kan lese logger, søke i kode og sammenligne dataflyt raskt, men kan også foreslå en overbevisende årsak uten bevis. Oppgaven bør derfor inneholde:

- det presise symptomet og stegene som gjenskaper det
- forventet og faktisk resultat
- miljø, relevante data og feilmeldinger
- hvilke hypoteser som allerede er testet
- beskjed om å diagnostisere før kode endres

Jeg ber gjerne Codex finne rotårsaken og peke på beviset i kode eller data. Når diagnosen er kontrollert, kan vi beslutte en rettelse. Denne rekkefølgen følger prosjektets arbeidsform: diagnose, beslutning, implementering.

## Når systemet er nede

Ved en alvorlig hendelse er første mål å redusere skade og få tjenesten tilbake. Hvis siste endring sannsynligvis utløste feilen, kan tilbakeføring være tryggere enn improvisert retting i produksjon. Rotårsaken undersøkes etter at situasjonen er stabil.

En hendelse er ikke ferdig behandlet når symptomet forsvinner. Vi må spørre hvorfor feilen slapp gjennom, og om den bør forebygges med tester, validering, databasekrav, bedre logger, dokumentasjon eller en tydeligere arbeidsflyt.

Det er forskjell på symptom og rotårsak. Hvis en import stopper fordi et felt er tomt, kan en reserveverdi få jobben videre. Rotårsaken kan likevel være at valideringen godtar en rad som senere ikke kan lagres. En varig løsning plasserer kontrollen der ugyldige data først kommer inn og gir brukeren en forståelig melding.

## Min faste metode

1. Beskriv symptomet presist.
2. Gjenskap feilen og avgrens miljø og data.
3. Les hele feilmeldingen og relevante logger.
4. Følg dataene til det første avviket.
5. Formuler én testbar hypotese.
6. Gjør én kontroll eller endring om gangen.
7. Verifiser resultatet og test berørte nabofunksjoner.
8. Dokumenter rotårsak og forebygging.

## Takeaways

- Et presist og gjentakbart symptom er starten på diagnosen.
- Jeg følger dataene til det første stedet resultatet blir feil.
- Logger, API-svar og databaseinnhold er bevis, ikke pynt.
- Én hypotese og én endring om gangen gjør resultatet forståelig.
- AI skal hjelpe med undersøkelsen, ikke hoppe over den.
- En varig rettelse behandler rotårsaken og forebygger gjentakelse.

## Prinsippet

Feilsøking er ikke gjetting med høy fart, men systematisk innsnevring til bevisene peker på årsaken.
