# Kapittel 18 – Brave Search og OpenAI API i dybden

Jeg trodde først at en språkmodell visste alt. I praksis må vi skille mellom det den har lært, og informasjon systemet henter underveis.

## To forskjellige verktøy

OpenAI API lar et program sende strukturert informasjon til en språkmodell og motta blant annet forslag, kategorisering eller sammendrag. Modellen kan tolke innholdet, men den kjenner ikke automatisk prosjektets database, siste dokumentasjon eller nye nettsider.

Et søke-API som Brave Search finner aktuelle nettsider og søkeresultater. En mulig arbeidsflyt er:

1. Søk etter relevant offentlig informasjon.
2. Velg og hent aktuelle kilder.
3. La språkmodellen tolke innholdet.
4. Kontroller forslaget før noe lagres.

Dette kalles RAG, *Retrieval Augmented Generation*: relevant informasjon hentes før modellen lager svaret. Søket finner kilder; modellen tolker dem.

## Eksempel fra Kreative Norge CRM

Importmotoren kan bruke OpenAI til kontrollerte forslag om kontaktdata, nettsider, kommuner, taksonomi og organisasjonsbeskrivelse. Forslagene følger et fast format, kan falle tilbake til enklere regler og krever menneskelig gjennomgang. AI får ikke publisere eller skrive data automatisk.

Importmotoren henter også signaler fra en kjent nettside, men repoet har ingen implementert eller konfigurert Brave Search-integrasjon. Brave Search er derfor en mulig framtidig kilde, ikke verifisert funksjonalitet.

## Grenser og ansvar

Svake kilder kan gi overbevisende, men gale forslag. Send bare nødvendige data, krev menneskelig kontroll, og la systemet fungere trygt uten eksterne API-er.

## Takeaways

- Språkmodellen tolker informasjon; et søke-API finner aktuelle kilder.
- RAG henter relevant kunnskap før svaret lages.
- OpenAI-forslag i CRM-et krever kontroll og kan ikke publisere automatisk.
- Brave Search er ikke verifisert som implementert i dagens repo.

## Prinsippet

God AI handler ikke om å late som modellen vet alt, men om å hente riktig kunnskap og kontrollere hvordan den brukes.
