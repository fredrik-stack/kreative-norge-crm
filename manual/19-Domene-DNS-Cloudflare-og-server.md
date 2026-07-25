# Kapittel 19 – Domene, DNS, Cloudflare og server

Når en bruker skriver et domenenavn, må forespørselen finne riktig server og tjeneste. Domenet er adressen, ikke selve serveren.

## Fra navn til applikasjon

**DNS**, internettets navnetjeneste, oversetter domenet til en IP-adresse. **Serveren** kjører applikasjonen og databasen. Et SSL-sertifikat muliggjør kryptert HTTPS.

Cloudflare kan ligge mellom brukeren og serveren for DNS, beskyttelse, mellomlagring og deler av HTTPS-oppsettet.

En typisk forespørsel går slik:

1. Nettleseren spør DNS hvor domenet peker.
2. Trafikken går direkte eller via Cloudflare til serveren.
3. nginx sender forespørselen til riktig tjeneste.
4. Django behandler kallet, eller nginx leverer React-appen.

## Eksempel fra Kreative Norge CRM

Repoet dokumenterer staging med Docker Compose, PostgreSQL, Django/Gunicorn og nginx. nginx skiller mellom frontend, `/api/`, `/admin/` og `/public/`.

Domene, DNS, Cloudflare og HTTPS er ikke dokumentert i repoet som verifisert prosjektstatus. Oppsettet må kontrolleres hos domeneeier, DNS-leverandør og server. Integrasjonen mot Musikkontoret.no er heller ikke ferdig.

En DNS-feil kan gjøre løsningen utilgjengelig selv om koden virker. Før endring må jeg kjenne dagens poster, ny verdi og veien tilbake.

## Takeaways

- Domenet er adressen; DNS peker den mot riktig server.
- Cloudflare kan være mellomledd for DNS, sikkerhet og mellomlagring.
- nginx fordeler trafikken videre til frontend og Django.
- Ekstern infrastruktur må verifiseres der den faktisk administreres.

## Prinsippet

Infrastrukturen lykkes når brukeren finner riktig, sikker applikasjon uten å måtte vite hvor serveren står.
