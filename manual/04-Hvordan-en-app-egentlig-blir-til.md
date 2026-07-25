# Kapittel 4 – Hvordan en app egentlig blir til

Første gang jeg åpnet CRM-prosjektet, så jeg en stor samling mapper og filer. Jeg visste ikke hva som var kritisk, eller hvor jeg skulle lete når noe gikk galt. Oversikten kom da jeg sluttet å se tusen enkeltdeler og begynte å se noen få lag som samarbeider.

## Fem deler i samme kjede

Kjernen i CRM-et kan forenkles til denne flyten:

```text
Bruker → Nettleser → Frontend → Backend → Database
```

**Brukeren** klikker, skriver, søker og lagrer. Brukerens behov er grunnen til at resten av systemet finnes.

**Nettleseren** er vinduet inn til CRM-et. Chrome, Safari eller en annen nettleser viser løsningen, men lagrer ikke CRM-dataene.

**Frontend** er brukergrensesnittet med knapper, tabeller, søk og dialogbokser. I prosjektet er dette bygget med React. Frontend viser informasjon og sender forespørsler videre.

**Backend** mottar forespørslene og bruker reglene i systemet. I Kreative Norge CRM er backend bygget med Django. Den vurderer blant annet om en handling er tillatt, om dataene er gyldige og hva som skal hentes eller lagres.

**Databasen** lagrer informasjonen. Den viser ikke knapper og bestemmer ikke produktreglene. Når backend ber om en organisasjon eller en kontaktperson, finner databasen de lagrede opplysningene.

## Hva skjer når jeg lagrer?

Når jeg oppretter en organisasjon, skjer dette:

1. Jeg fyller ut et skjema i nettleseren.
2. Frontend sender opplysningene til backend.
3. Backend kontrollerer reglene og ber databasen lagre.
4. Databasen bekrefter resultatet.
5. Backend svarer frontend.
6. Frontend oppdaterer det jeg ser.

Prosessen går vanligvis på under et sekund. Modellen hjelper meg likevel å stille bedre spørsmål når noe feiler. En knapp som ikke reagerer, peker ofte mot frontend. Avvist eller feil lagring kan ligge i backend. Manglende eller uriktige data kan kreve kontroll av databasen.

Dette er utgangspunkt for undersøkelsen, ikke en automatisk fasit. Feil kan forplante seg mellom lagene.

## Verktøyene rundt appen

Docker, Git, GitHub og Codex er viktige, men de er ikke nye lag i dataflyten:

- **Docker** starter og kobler sammen tjenestene som CRM-et trenger.
- **Git** registrerer valgte versjoner av filene og gir prosjektet en lokal historikk.
- **GitHub** oppbevarer og deler Git-historikken, slik at arbeidet ikke bare finnes på én Mac.
- **Codex** leser og endrer prosjektfilene når en oppgave skal implementeres.
- **ChatGPT** brukes til å forstå, planlegge og kvalitetssikre med den konteksten det får.

På samme måte er Linux-serveren maskinen som kjører løsningen i et servermiljø. Hvis hele systemet ikke starter, undersøker jeg kjøringen og Docker-oppsettet. Hvis serveren ikke svarer, må jeg også kontrollere selve maskinen og forbindelsen til den.

## Finn landskapet i CRM-prosjektet

Jeg trenger ikke lese alle filene for å kjenne igjen hovedområdene. I prosjektmappen, ofte kalt repoet, kan jeg blant annet finne:

```text
kreative-norge-crm/
├── crm/                 # sentral backend-kode
├── config/              # Django-konfigurasjon
├── frontend/            # React-grensesnitt
├── docker-compose.yml   # lokal Docker-kjøring
├── manage.py            # Django-kommandoer
└── requirements.txt     # Python-avhengigheter
```

En nyttig øvelse er å finne disse områdene i VS Code, åpne repoet i GitHub og legge merke til hvor frontend, backend og kjøreoppsett ligger. Målet er ikke å forstå hver fil, men å kunne orientere seg.

## Takeaways

- CRM-et kan forstås som en kjede fra bruker til database.
- Frontend viser og sender forespørsler; backend håndhever regler; databasen lagrer.
- Git, GitHub og Docker støtter utvikling og kjøring, men er ikke del av selve dataflyten.
- En lagmodell gjør det lettere å avgrense hvor en feil kan ligge.
- Prosjektmappen blir mindre overveldende når jeg kjenner hovedområdene.

## Prinsippet

Forstå først hvilke deler som samarbeider; lær detaljene når du trenger dem.
