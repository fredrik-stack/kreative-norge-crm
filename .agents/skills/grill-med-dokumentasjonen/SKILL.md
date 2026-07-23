---
name: grill-med-dokumentasjonen
description: Kritisk gjennomgå dokumentasjon, planer og beslutninger i Kreative Norge CRM for å finne motsetninger, uklare antakelser, manglende beslutninger og avvik fra kode. Bruk før større implementering eller når Fredrik ber om å utfordre planen.
---

# Grill med dokumentasjonen

Følg `AGENTS.md`. Les relevant dokumentasjon og kontroller mot kode, migrasjoner, API-ruter og tester.

Finn og ranger:

- motsetninger mellom dokumenter
- plan som omtales som implementert
- kode som mangler dokumentasjon
- uavklarte beslutninger skjult som fakta
- sikkerhets-, personvern- og datarisiko
- unødvendig kompleksitet
- manglende akseptansekriterier
- avhengigheter og tilbakeføringsbehov

Rapporter:

1. kritiske funn
2. viktige spørsmål som må avgjøres
3. anbefalt forenkling
4. hva som kan vente
5. dokumenter som bør oppdateres

Ikke kode eller endre beslutninger. Skill mellom dokumenterte fakta, avvik, antakelser og spørsmål som trenger prosjekteierens godkjenning.

## Output

En prioritert granskningsrapport med belegg, kritiske og viktige funn, åpne beslutninger, anbefalt forenkling og berørte dokumenter.

## Neste anbefalte skill

Bruk `$planlegg-ny-funksjon` når funnene krever ny helhetsdesign. Bruk `$ta-arkitekturavgjorelse` når grunnlaget allerede er godkjent og skal formaliseres.
