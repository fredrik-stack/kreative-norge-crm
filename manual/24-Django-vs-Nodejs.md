# Kapittel 24 – Django vs. Node.js

Jeg fikk ofte spørsmålet: «Hvorfor Django og ikke Node.js?» Svaret avhenger av produktet, teamet og kostnaden over tid.

## To ulike utgangspunkt

Django er et web-rammeverk i Python med autentisering, administrasjonspanel, ORM for databasen, skjemaer, sikkerhet og migrasjoner. Det passer godt til datadrevne systemer.

Node.js er et kjøremiljø for JavaScript utenfor nettleseren. En Node-backend krever også rammeverk, som Express eller NestJS, og valg for database, autentisering, validering og migrasjoner.

Django tilbyr etablerte standardvalg. Node-økosystemet gir større frihet og flere deler å sette sammen. Begge kan bygge gode API-er.

## Eksempel fra Kreative Norge CRM

CRM-et er ikke et enten-eller. Django håndterer datamodell, autentisering, API, import og publisering. Node-verktøy bygger og tester React-frontenden med TypeScript og Vite.

Django passet fordi kjernen er strukturerte data, relasjoner, roller og administrasjon. Et Node-bytte måtte også erstatte ORM, migrasjoner, tilgang, API-struktur, tester og drift.

## Spørsmålet som hjelper

Teknologi bør velges ut fra:

- produktets dataflyt og viktigste arbeidsmengder
- teamets kompetanse og rekrutteringsmuligheter
- modenhet, dokumentasjon og sikkerhetsoppdateringer
- test, deploy, drift og langsiktig vedlikehold

Det er mulig å bytte senere, men kostnaden vokser med datamodell, integrasjoner og brukerflyter. Popularitet alene er ikke en god begrunnelse.

## Takeaways

- Django er et komplett Python-rammeverk; Node.js er et JavaScript-kjøremiljø.
- Et Node-valg må også angi rammeverk og resten av backendstacken.
- CRM-et bruker Django i backend og Node-verktøy rundt frontend.
- Velg teknologien som gjør produktet forståelig og vedlikeholdbart over tid.

## Prinsippet

Velg teknologi for problemet og levetiden, ikke for populariteten.
