# Kapittel 17 – Biblioteker og dependencies

Da jeg begynte å utvikle Kreative Norge CRM, ble jeg overrasket over hvor mye av programvaren andre hadde skrevet. Profesjonelle utviklere bygger med gjennomprøvde byggeklosser i stedet for å lage alt fra bunnen av.

## Biblioteker og avhengigheter

Et bibliotek er ferdig programvare vi kan bruke i vårt eget prosjekt. Det kan være en liten samling funksjoner eller et helt rammeverk som Django eller React.

En *dependency*, eller avhengighet, er en byggekloss prosjektet trenger for å virke. Den kan ha egne avhengigheter, slik at noen få direkte valg fører til mange installerte filer.

Dette sparer arbeid, men skaper ansvar. En feil eller sikkerhetssvakhet i et sentralt bibliotek kan påvirke hele systemet.

## Pakkehåndtering og versjoner

Pakkehåndterere installerer og holder oversikt over biblioteker. Python bruker ofte `pip`, mens JavaScript gjerne bruker `npm`.

Prosjektfilene beskriver hvilke pakker og versjoner som trengs. En låsefil registrerer mer nøyaktig hva som ble installert, slik at utviklingsmaskinen og CI kan bruke samme grunnlag.

Nye versjoner kan rette sikkerhetsfeil, men også endre oppførsel. Oppdater derfor kontrollert og test etterpå. Gamle pakker er risikable; å oppdatere alt samtidig gjør feil vanskelige å spore.

## Eksempel fra Kreative Norge CRM

Backend bruker blant annet Django, Django REST Framework, PostgreSQL-driver, OpenAPI-verktøy og OpenAI-bibliotek. Frontend bruker React, TypeScript, Vite og testbiblioteker.

Python-avhengighetene står i `requirements.txt`. Noen er avgrenset til en versjonsserie, mens andre er mindre stramt låst. Frontend bruker `package.json` sammen med `package-lock.json`, som registrerer det konkrete npm-avhengighetstreet.

Vi skrev altså ikke API-rammeverket, React eller Swagger-visningen selv. Vi brukte dem til å bygge det som er spesielt for CRM-et: aktører, personer, relasjoner, import og offentlig publisering.

## Velg med omtanke

Før et nytt bibliotek legges til, bør jeg spørre:

- Løser det et reelt problem bedre enn enkel egen kode?
- Er det aktivt vedlikeholdt, dokumentert og testet?
- Passer det prosjektets størrelse og teknologistack?
- Forstår vi sikkerhetsrisiko og oppdateringsbehov?
- Kan vi oppnå det samme med en avhengighet vi allerede har?

Popularitet er ingen garanti. Hver avhengighet øker vedlikeholdsbehovet. Målet er å unngå unødvendige biblioteker uten å bygge grunnleggende infrastruktur på nytt.

## Takeaways

- Biblioteker lar oss bruke tiden på produktet i stedet for løste standardproblemer.
- En dependency er en avhengighet prosjektet må vedlikeholde og sikre.
- Versjoner og låsefiler gjør installasjoner mer forutsigbare.
- Nye pakker og oppdateringer må begrunnes og testes.

## Prinsippet

Velg solide byggeklosser, forstå hva prosjektet blir avhengig av, og skriv bare den koden som gir produktet egen verdi.
