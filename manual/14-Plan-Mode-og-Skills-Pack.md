# Kapittel 14 – Plan Mode og Skills Pack

I starten brukte jeg AI som et oppslagsverk: Jeg stilte et spørsmål, fikk et svar og stilte det neste. Det fungerte godt for små oppgaver, men større arbeidsøkter begynte stadig med den samme opplæringen om prosjektet, teknologien og reglene våre.

Løsningen ble å skille mellom planlegging og gjennomføring, og å samle gjentatte arbeidsmåter i prosjektets Skill Pack. Da kunne AI bidra mer som en fast kollega enn som en ny medarbeider hver morgen.

## Planlegg før du bygger

Plan Mode betyr at AI undersøker og strukturerer en oppgave før den endrer kode. En god plan avklarer:

- hvilket problem vi egentlig skal løse
- hvem løsningen er for
- hvilke filer og systemdeler som påvirkes
- hvilke beslutninger og avhengigheter som finnes
- risiko, rekkefølge og testbehov

Målet er ikke en lengst mulig plan. Målet er å oppdage uklare krav og dyre feil før implementeringen begynner.

Dette passer med grunnrytmen i Kreative Norge CRM: diagnose, beslutning, implementering. Hvis en feil har ukjent årsak, undersøker vi den først. Hvis en større endring påvirker arkitektur eller data, beskrives og godkjennes retningen i en ADR. Først deretter bygger og tester Codex løsningen.

Små, entydige oppgaver trenger ikke samme prosess. En skrivefeil eller avgrenset stilendring kan vanligvis rettes direkte. Planlegging har verdi når den reduserer reell usikkerhet.

## Skills er arbeidsinstruksjoner

En Skill er en gjenbrukbar instruks til Codex for én type arbeid. Den kan for eksempel forklare hvordan en ukjent feil skal undersøkes uten at kode endres, eller hvilke sikkerhetskontroller som kreves ved en databaseendring.

En Skill er ikke programkode og beskriver ikke hvordan CRM-et fungerer. Prosjektfakta hører hjemme i `docs/`; arbeidsmåten hører hjemme i Skills og de korte grunnreglene i `AGENTS.md`.

Kreative Norge CRM har 12 prosjektbaserte Skills, organisert rundt fire arbeidsnivåer:

1. forstå problemet
2. ta eller dokumentere en beslutning
3. bygge den godkjente løsningen
4. kontrollere kvalitet og produksjonsberedskap

En Skill kan velges eksplisitt med navnet sitt. Codex kan også velge den ut fra oppgaven, men eksplisitt valg er tryggest når arbeidsfasen er viktig. En diagnoseoppgave skal for eksempel ikke gli over i implementering bare fordi en mulig retting ser enkel ut.

## Eksempel fra Kreative Norge CRM

Importmodulen viser hvorfor planlegging er nyttig. Den er allerede en omfattende og fungerende modul med opplasting, preview (forhåndsvisning), validering, matching, AI-forslag, gjennomgang, kontrollert commit til databasen og feilrapport. Når brukeropplevelsen senere skal forbedres, er det risikabelt å be AI om å «lage ny import» og begynne rett i koden.

En bedre rekkefølge er:

1. Kartlegg dagens importmotor og brukerflyt.
2. Avklar behov, avgrensning og kvalitetskrav.
3. Bestem hva som skal beholdes, endres og utsettes.
4. Dokumenter større arkitekturvalg ved behov.
5. Del implementeringen i kontrollerbare leveranser.
6. Definer automatiske og manuelle tester før arbeidet starter.

Planen hindrer at en ny overflate ødelegger fungerende regler for deduplisering, tenant-avgrensning eller sikker commit av data.

Skill Pack gjør deretter hvert arbeidstrinn mer konsekvent. Vi har blant annet egne arbeidsflyter for å planlegge en funksjon, vurdere om løsningen er overarbeidet, skrive en konkret Codex-oppgave, fullføre til staging og gjennomgå siste endring.

## En praktisk arbeidsøkt

En større oppgave kan gjennomføres slik:

1. Jeg beskriver behovet og ønsket resultat.
2. AI leser gjeldende status, relevant dokumentasjon, kode og tester.
3. Vi avklarer usikkerhet og velger riktig arbeidsfase eller Skill.
4. Planen beskriver berørte områder, risiko og teststrategi.
5. Codex implementerer den godkjente retningen.
6. Endringen testes, dokumenteres og rapporteres med kjent restarbeid.

Denne arbeidsdelingen betyr ikke at ChatGPT bare tenker og Codex bare skriver kode. Begge kan analysere og kontrollere. Poenget er at planlegging og implementering har ulike mål og tydelige stoppunkter.

## Vanlige feil

Plan Mode blir tungvint hvis det brukes på alle småting. Skills blir uoversiktlige hvis hver detalj får sin egen oppskrift. En ny Skill er mest nyttig når oppgaven gjentar seg, har tydelige kvalitetskrav eller trenger et bestemt stoppunkt.

Den farligste feilen er å la Skills erstatte oppdatert prosjektkunnskap. En perfekt arbeidsinstruks kan fortsatt gi feil resultat hvis den bygger på foreldet status.

## Takeaways

- Planlegg større eller usikre endringer før kode endres.
- Bruk diagnose, beslutning og implementering som separate arbeidsfaser.
- Skills lagrer gjenbrukbare arbeidsmåter; `docs/` lagrer prosjektfakta.
- Velg en Skill eksplisitt når riktig arbeidsfase er avgjørende.
- Hold planer og Skills så korte som oppgaven tillater.

## Prinsippet

Den raskeste veien er ikke å skrive kode først, men å avklare problemet, velge riktig arbeidsmåte og deretter bygge målrettet.
