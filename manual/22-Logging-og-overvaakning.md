# Kapittel 22 – Logging og overvåkning

Et system vil før eller siden feile. Det avgjørende er hvor raskt vi oppdager og forstår feilen.

## Historie og helsetilstand

**Logging** registrerer hendelser, som startet import eller feilet API-kall. Loggen hjelper oss å rekonstruere fortiden.

**Overvåkning** følger systemets tilstand nå: tilgjengelighet, svartid, feilrate, CPU, minne og diskplass. Varsling sier fra når en grense brytes.

Logger uten overvåkning kan forklare en oppdaget feil. Overvåkning uten gode logger kan varsle at noe er galt, men ikke hvorfor. Vi trenger begge.

## Logg det som hjelper

Relevante hendelser kan være innlogging, publisering, import, eksport, AI-kall, unntak og avvist tilgang. Loggen bør forklare hva, når og hvem uten å kopiere databasen.

Kontaktdata, passord, tokens og komplette AI-inndata skal ikke havne ukritisk i logger. Tilgang, lagringstid og sletting av logger er også sikkerhetsvalg.

## Eksempel fra Kreative Norge CRM

Importmotoren har detaljert sporbarhet. Jobben lagrer status, radfeil og advarsler, beslutninger knyttes til brukeren, og commit-loggen registrerer endringer. AI-forslag har diagnostikk for leverandør, fallback og feil.

Dette er ikke det samme som en generell auditlogg for hele CRM-et. Auditlogg og sterkere sporbarhet står fortsatt som planlagt, og repoet dokumenterer ikke et komplett overvåknings- og varslingsoppsett for server, API og database. Vanlige containerlogger kan hjelpe ved feilsøking, men de erstatter ikke definerte målinger og varsler.

## Takeaways

- Logger forklarer hendelser; overvåkning viser systemets helsetilstand.
- Varsler må knyttes til målinger noen faktisk følger opp.
- Logg nok til å rekonstruere feil, men ikke unødvendige personopplysninger.
- Importen har sporbarhet; generell audit og overvåkning er fortsatt uferdig.

## Prinsippet

Et robust system oppdager feil tidlig og etterlater nok spor til at vi kan forstå og rette dem.
