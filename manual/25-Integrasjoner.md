# Kapittel 25 – Integrasjoner

Et CRM-system blir mer nyttig når det utveksler informasjon med andre tjenester, men hver integrasjon øker også avhengighetene. Jeg må forstå hva forbindelsen skal løse, og hva som skjer når tjenesten ikke svarer.

## API-et er kontrakten

En integrasjon bruker ofte et API, et avtalt grensesnitt for forespørsler og svar. Data kan hentes inn eller sendes ut. CRM-et kan selv be om informasjon, eller en tjeneste kan varsle når noe har skjedd.

Kommunikasjonen kan være synkron, slik at CRM-et venter på svar, eller asynkron, slik at jobben behandles i bakgrunnen. Det siste passer når behandlingen tar tid eller tjenesten er ustabil.

En god integrasjon må avklare:

- hvilke data som utveksles, og hvem som eier dem
- hvordan tilgang og personopplysninger beskyttes
- hva som logges
- hvordan feil, tidsavbrudd og utilgjengelige tjenester håndteres
- om tjenesten kan erstattes uten å bygge om kjernen

## Eksempel fra Kreative Norge CRM

CRM-et har egne API-er mellom brukergrensesnittet og Django, og et offentlig API for publiserte data. Importflyten kan bruke OpenAI til forslag, men har en reserveflyt når AI ikke er tilgjengelig.

Andre tjenester som Brønnøysundregistrene, Brave Search, Google Maps, Checkin og Mailmojo er aktuelle eller reserverte integrasjoner, ikke ferdige deler av systemet. Det skillet er viktig når jeg planlegger arbeid eller forklarer hva produktet kan gjøre i dag.

Målet er ikke flest mulig koblinger. Kjernen skal være tydelig, mens spesialiserte tjenester brukes der de gir reell verdi.

## Takeaways

- Et API er en kontrakt mellom systemer.
- Jeg må skille mellom implementerte og planlagte integrasjoner.
- Eksterne tjenester kan feile uten at hele CRM-et bør stoppe.
- Eierskap, tilgang og logging må avklares for data som utveksles.

## Prinsippet

En god integrasjon gir nytte uten å gjøre produktets kjerne unødvendig avhengig.
