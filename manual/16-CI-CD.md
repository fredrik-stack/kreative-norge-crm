# Kapittel 16 – CI/CD

Å skrive kode er bare begynnelsen. Endringen skal også testes, bygges, pakkes og leveres til riktig miljø på en måte vi kan gjenta og kontrollere. CI/CD automatiserer deler av denne kjeden.

Tenk på det som et samlebånd. Koden går gjennom flere kontrollpunkter, og prosessen stopper hvis et viktig punkt feiler. Målet er ikke bare fart, men en leveranse som ikke er avhengig av hukommelse og flaks.

## CI og CD betyr ulike ting

CI står for *Continuous Integration*, eller kontinuerlig integrasjon. Når kode pushes eller legges i en pull request, kan en automatisert arbeidsflyt:

1. hente riktig versjon fra Git
2. installere avhengigheter
3. bygge prosjektet
4. kjøre tester og kvalitetskontroller
5. rapportere tydelig hvis noe feiler

Da oppdages problemer mens endringen fortsatt er fersk.

CD kan bety *Continuous Delivery* eller *Continuous Deployment*. Ved Continuous Delivery er en testet versjon klar til utrulling, men et menneske godkjenner normalt selve deployen. Ved Continuous Deployment går en godkjent versjon automatisk helt til miljøet den skal kjøre i.

Forskjellen er viktig: Et prosjekt kan ha god CI uten automatisk deploy.

## GitHub, Docker og miljøer

GitHub lagrer ikke bare historikken. GitHub Actions kan starte automatiske jobber når kode pushes. Docker pakker applikasjonen og avhengighetene slik at oppsettet blir mer likt mellom utviklingsmaskin, staging og produksjon.

Staging er miljøet der vi prøver den samlede løsningen før produksjon. Det bør ligne produksjon nok til at vi kan kontrollere migrasjoner, nettverk, bygg og reelle brukerflyter. Hvis prosessen feiler, må vi vite hvilken commit som ble forsøkt deployet, hvor den stoppet, og hvordan vi går tilbake.

## Eksempel fra Kreative Norge CRM

Kreative Norge CRM har allerede en CI-arbeidsflyt i GitHub Actions. Den kjører:

- Django-tester og en smoke-test, altså en rask grunnkontroll av editor-API-et
- frontend-tester med Vitest
- TypeScript-kontroll og bygg av React-appen
- E2E-tester med Playwright i en nettleser

Dette gir automatiske kontrollpunkter for backend og frontend. Staging finnes også med Docker Compose, PostgreSQL, Django/Gunicorn og nginx.

Automatisk staging-deploy ved push er derimot ikke implementert eller verifisert som prosjektstandard. Dagens dokumenterte oppdatering er manuell. Før CD bygges videre, må prosjektet beslutte blant annet hvilken branch som utløser deploy, hvilke tester som er obligatoriske, hvordan secrets (passord, nøkler og andre hemmeligheter) og servertilgang håndteres, og hvordan migrasjon, helsesjekk og rollback (tilbakeføring) skal fungere.

En ønsket leveransekjede kan senere se slik ut:

1. En endring pushes til GitHub.
2. CI kjører backend-, frontend- og E2E-kontroller.
3. Et Docker-image bygges fra den godkjente commiten.
4. Staging oppdateres og får en automatisk helsesjekk.
5. Prosjekteieren prøver den relevante brukerreisen.
6. Produksjonssetting skjer kontrollert og med kjent tilbakeføring.

Dette er en målprosess, ikke en beskrivelse av hva som allerede skjer automatisk.

## Spørsmål prosjektlederen bør stille

Jeg trenger ikke å skrive en GitHub Action for å styre kvaliteten. Jeg bør likevel kunne spørre:

- Hvilke tester ble kjørt, og bestod de?
- Hvilken commit kjører i staging eller produksjon?
- Ble databaseendringer gjennomført trygt?
- Hvor stoppet leveransen hvis noe feilet?
- Finnes det en test etter deploy?
- Kan vi rulle tilbake uten å miste data?

Flere automatiske steg er ikke automatisk bedre. En rask leveransekjede uten riktige tester kan levere feil raskere. Automatiseringen må støtte risikonivået og ha tydelige stoppunkter.

## Takeaways

- CI kontrollerer endringer fortløpende; CD gjør dem klare for eller ruller dem ut.
- GitHub Actions og Docker gir repeterbare kontroll- og leveransesteg.
- CRM-et har CI, men automatisk staging-deploy er fortsatt planlagt.
- En deploy må være sporbar, testbar og mulig å rulle tilbake.
- Prosjektlederen styrer kvalitetskravene selv om teknikken er automatisert.

## Prinsippet

En profesjonell leveranse er en kjent commit som er kontrollert, sporbar og trygt kan flyttes mellom miljøer.
