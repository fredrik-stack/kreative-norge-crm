# Kapittel 26 – Drift

Lansering er ikke slutten på et programvareprosjekt. Det er da produktet begynner å møte virkelige brukere, data og feil. Jeg må derfor behandle drift som en del av produktet, ikke som opprydding etter utviklingen.

## Fra endring til stabilitet

Utvikling handler om å endre systemet. Drift handler om å holde det tilgjengelig, sikkert og forståelig mens endringene fortsetter. Det omfatter blant annet server, database, oppdateringer, sikkerhet, sikkerhetskopier, overvåking, feilretting, støtte, kapasitet og kostnader.

Produksjon må behandles annerledes enn lokal utvikling og staging. En endring bør være testet og dokumentert, og det må være mulig å finne ut hva som ble satt ut. Ved risikable endringer trenger vi også en plan for å gå tilbake til forrige fungerende versjon.

Regelmessige, små oppdateringer er som regel lettere å forstå og rette enn sjeldne kjempeløft. Det gjelder også avhengigheter og sikkerhetsoppdateringer. Utsetter vi vedlikeholdet lenge, vokser både risikoen og arbeidsmengden.

Hver produksjonsendring bør ha et kjent formål, en ansvarlig person og en enkel kontroll etterpå. Hvis kontrollen mislykkes, må vi vite om endringen skal rettes fremover eller rulles tilbake. Under en hendelse er første oppgave å stabilisere tjenesten og begrense konsekvensene. Deretter undersøker vi rotårsaken og forbedrer rutiner, tester eller overvåking.

## Hva må følges med på?

Et system kan bli presset av flere brukere, mer data, større lagringsbehov, trege databasespørringer eller mange kall til eksterne API-er. Løsningen er ikke alltid en større server. Først må vi finne flaskehalsen. Tiltak kan være bedre databasespørringer, mellomlagring, bakgrunnsjobber eller færre eksterne kall.

Kostnader må også sees samlet. Server og database er bare deler av bildet. Lagring, trafikk, domener, e-post, AI-tjenester, andre API-er, overvåking og arbeidstid kan bli like viktige. En tjeneste som virker billig per kall, kan bli dyr når mange organisasjoner behandler tusenvis av kontakter.

Teknisk gjeld er arbeid vi skyver foran oss: midlertidige løsninger, manglende tester, gamle avhengigheter eller utydelig dokumentasjon. Litt gjeld kan være et bevisst valg for å komme videre. Problemet oppstår når ingen vet at den finnes, eller når den aldri prioriteres.

Det hjelper å føre gjelden som konkrete oppgaver med konsekvens og prioritet. «Rydd opp i backend» er lite styrbart. «Samle reglene for offentlig kontaktinformasjon slik at API og visning bruker samme kilde» sier både hva problemet er og hvorfor det betyr noe.

## En praktisk driftsrytme

Rutinene må tilpasses risikoen, men en enkel rytme kan være:

1. Følg daglig med på alvorlige feil og tilgjengelighet.
2. Se ukentlig etter mislykkede jobber, lagringsvekst og uvanlige hendelser.
3. Gjennomgå månedlig kostnader, oppdateringer, tilganger og teknisk gjeld.
4. Test med jevne mellomrom at sikkerhetskopier faktisk kan gjenopprettes.
5. Vurder kvartalsvis kapasitet, leverandøravhengigheter og beredskap.

Overvåking har liten verdi uten ansvar. Det må være tydelig hvem som mottar et varsel, hva som regnes som kritisk, og hva personen skal gjøre.

## Eksempel fra Kreative Norge CRM

CRM-et har et staging-miljø med Docker Compose, PostgreSQL, Django med Gunicorn og nginx. Det gir et realistisk sted å kontrollere endringer før produksjon, men staging er ikke det samme som en ferdig driftsmodell.

Automatisk produksjonssetting, generell overvåking, varsling og dokumentert sikkerhetskopiering med testet gjenoppretting er ikke verifisert som ferdige løsninger. Før reell produksjonsdrift må vi derfor avklare ansvar for:

- server, database og domene
- deploy og tilbakeføring
- hemmeligheter, tilganger og sikkerhetsoppdateringer
- sikkerhetskopiering og gjenoppretting
- logger, overvåking og varsler
- støtte, kostnader og leverandører

Dokumentasjonen må være god nok til at en annen person kan forstå oppsettet og overta driften. Et produkt som bare én person tør å oppdatere, er sårbart selv om koden fungerer.

En enkel driftsbeskrivelse bør vise hvor tjenestene kjører, hvordan en versjon settes ut, hvor logger finnes, hvordan databasen gjenopprettes og hvem som kontaktes ved feil. Passord og hemmeligheter skal ikke ligge i dokumentet, men fremgangsmåten for å finne og forvalte dem må være kjent.

## Vanlige feil

Det er risikabelt å lansere uten driftsbudsjett, anta at leverandøren tar ansvar for hele produktet eller vente med rutiner til den første krisen. Det samme gjelder å la all kunnskap bli hos én utvikler. Drift bør planlegges mens systemet fortsatt er oversiktlig.

## Takeaways

- Drift begynner før lansering og fortsetter så lenge produktet lever.
- Produksjonsendringer skal være testet, sporbare og mulig å rulle tilbake.
- Kapasitetsproblemer må måles før vi velger tiltak.
- Kostnader omfatter både teknologi, tjenester og arbeidstid.
- Sikkerhetskopier er først pålitelige når gjenoppretting er testet.
- Ansvar og dokumentasjon reduserer personavhengighet.

## Prinsippet

Et digitalt produkt beviser ikke verdien sin ved lansering, men gjennom stabil og forståelig drift etterpå.
