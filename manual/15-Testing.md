# Kapittel 15 – Testing

Jeg trodde først at testing bare handlet om å finne feil. Etter hvert forstod jeg at målet er større: Testing gir trygghet til å endre et system der mange deler påvirker hverandre.

En liten endring i Kreative Norge CRM kan berøre import, API, publisering, innlogging, Editor og database. Ingen utvikler kan holde alle konsekvensene i hodet. Tester fungerer som et sikkerhetsnett og som en presis beskrivelse av hva systemet skal gjøre.

## Flere nivåer av trygghet

Ulike tester svarer på ulike spørsmål. Et prosjekt trenger en fornuftig kombinasjon, ikke flest mulig tester.

### Manuell testing

Jeg åpner systemet og bruker det: logger inn, oppretter en aktør, redigerer en person, kobler en kontakt og kontrollerer den offentlige visningen. Mennesker oppdager uklare tekster, merkelige overganger og andre problemer som er vanskelige å beskrive i kode.

Svakheten er at vi glemmer trinn og ofte prøver den lykkelige veien. Derfor må kritiske brukerflyter også kunne gjentas automatisk.

### Unit-tester

En unit-test kontrollerer en liten, avgrenset del, for eksempel funksjonen som velger hvilket bilde en aktør skal vise. Slike tester er raske og gjør det lettere å finne nøyaktig hvor en feil oppstår.

### Integrasjonstester

Integrasjonstester kontrollerer samspillet mellom deler. Et API kan motta data riktig, men lagre dem feil i PostgreSQL eller returnere et resultat som frontend ikke forstår. Hver del kan virke alene selv om helheten feiler.

### End-to-end-tester

En end-to-end-test, ofte forkortet E2E, bruker systemet omtrent som et menneske. Den kan åpne en nettleser, logge inn, opprette og redigere data og kontrollere resultatet. Testen dekker mye, men tar lengre tid og kan være mer følsom for små endringer i brukergrensesnittet.

## Test både suksess og motstand

En nybegynner spør gjerne: «Kan jeg opprette en organisasjon?» En sterkere teststrategi spør også:

- Hva skjer hvis organisasjonsnummeret mangler?
- Blir en ugyldig e-post avvist?
- Hva skjer hvis samme importfil behandles to ganger?
- Kan en bruker se data fra en annen tenant?
- Lekker private kontaktopplysninger til PUBLIC?
- Stopper en masseendring trygt når enkelte rader har feil?

Det holder altså ikke å bekrefte at riktig input gir riktig svar. Vi må også kontrollere at ugyldige handlinger stoppes, og at feil ikke skader eksisterende data.

## Eksempel fra Kreative Norge CRM

CRM-et har automatiske Django-tester for blant annet autentisering, tenant-avgrensning, import, kontaktdata og offentlig visning. Frontend har egne tester, og Playwright brukes til E2E-flyter i nettleseren. I tillegg finnes en smoke-test som raskt kontrollerer at de viktigste delene av editor-API-et svarer.

Import er et godt eksempel på behovet for flere nivåer. En fil kan parses riktig, men koblingen mellom person og organisasjon kan likevel bli feil. Preview kan se korrekt ut, mens commit-fasen skriver uønskede publiseringsflagg til databasen. Derfor tester prosjektet blant annet CSV og XLSX, validering, matching, tenant-avgrensning, uløste rader, commit-logg og feilrapport.

PUBLIC viser en annen type risiko. Editor, API og offentlig HTML har ikke alltid brukt kontaktdata på samme måte. En endring må derfor testes både der data redigeres og der de publiseres. En grønn test på ett endepunkt beviser ikke at hele brukerreisen er riktig.

## AI kan skrive tester, men ikke definere sannheten

Codex kan lage unit-, integrasjons- og E2E-tester raskt. Det er særlig nyttig når en feil først gjenskapes i en test og rettingen deretter må få testen til å bestå.

Men AI tester spesifikasjonen den får. Den vet ikke alene om arbeidsflyten er forståelig, eller om løsningen dekker brukerens behov. Jeg må fortsatt vurdere produktet og prøve realistiske situasjoner i lokal Docker eller staging når risikoen tilsier det.

## Når er en endring ferdig testet?

Før jeg kaller en funksjon ferdig, spør jeg:

1. Fungerer den forventede brukerreisen?
2. Håndteres ugyldige og uventede data trygt?
3. Består relevante eksisterende tester?
4. Er både Editor og PUBLIC kontrollert dersom begge påvirkes?
5. Er tenant-, rolle- og publiseringsgrenser bevart?
6. Er løsningen prøvd med realistiske data og i riktig miljø?

Testomfanget skal følge risikoen. En tekstendring krever mindre enn en migrasjon eller masseimport, men ingen endring bør godkjennes bare fordi koden ser riktig ut.

## Takeaways

- Testing skaper trygghet til å endre et sammenkoblet system.
- Manuelle, avgrensede, integrerte og komplette tester finner ulike feil.
- Test også ugyldige handlinger, datagrenser og uventede situasjoner.
- AI kan automatisere kontrollen, men prosjekteieren vurderer om produktet løser behovet.
- Testomfanget skal følge konsekvensen hvis noe går galt.

## Prinsippet

Programvare blir ikke robust fordi vi tror den virker, men fordi vi kontrollerer det på de nivåene der den kan svikte.
