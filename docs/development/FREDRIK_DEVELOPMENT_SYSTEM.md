# Fredrik Development System

**Status:** Gjeldende utviklingsplattform

**Sist oppdatert:** 2026-07-23

Fredrik Development System er prosjektets samlede system for å forstå, beslutte, bygge og kvalitetssikre Kreative Norge CRM. Systemet består av:

- stabil prosjektkunnskap i `docs/`
- repo-regler i `AGENTS.md`
- gjenbrukbare Codex-arbeidsflyter i `.agents/skills/`
- Git og GitHub som historikk og felles sannhetskilde
- tester, lokal Docker og staging som verifiseringsnivåer

Skill Pack er arbeidsflytdelen av plattformen. Det erstatter ikke arkitektur-, feature- eller statusdokumentasjon.

## Grunnregler

1. Ingen større implementering uten godkjent ADR.
2. Ingen funksjon er ferdig før dokumentasjonen er oppdatert eller kontrollert.
3. Stabil prosjektkunnskap skal ligge i `docs/`, ikke gjentas i prompts.
4. Diagnose → beslutning → implementering.

En «større implementering» er en endring med vesentlig produkt-, arkitektur-, personvern-, sikkerhets-, integrasjons-, API-, data- eller migreringskonsekvens. Små, reversible feilrettinger og vedlikeholdsoppgaver kan gjennomføres uten nytt ADR når de følger eksisterende beslutninger og har tydelig scope.

## Arbeidsflyt i fire nivåer

| Nivå | Formål | Resultat |
| --- | --- | --- |
| 1 – FORSTÅ | Forklare, undersøke og utfordre grunnlaget | Felles forståelse eller dokumentert diagnose |
| 2 – BESLUTT | Designe, dimensjonere og formalisere retning | Godkjenningsklar design eller ADR |
| 3 – BYGG | Formulere og gjennomføre godkjente leveranser | Testet, dokumentert og sporbar endring |
| 4 – KVALITET | Gjennomgå, synkronisere dokumentasjon og forberede release | Verifisert leveranse og tydelig release-gate |

Normal rekkefølge ved ukjent feil:

```text
undersøk → planlegg ved større konsekvens → ADR → Codex-oppgave
→ implementering → gjennomgang → dokumentasjonskontroll → release-forberedelse
```

Skillene foreslår neste naturlige skill i slutten av hvert resultat. Dette er veiledning, ikke automatisk kjeding.

## Ansvar og sannhetskilder

- `AGENTS.md` inneholder korte regler som Codex skal ha i hver prosjektøkt.
- `docs/status/PROJECT_STATUS_CURRENT.md` beskriver verifisert nåstatus.
- `docs/architecture/` beskriver faktisk system og dataflyt.
- `docs/features/` beskriver produktkrav og ønsket brukeropplevelse.
- `docs/decisions/` inneholder godkjente arkitekturbeslutninger.
- `docs/status/ROADMAP.md` viser planlagt rekkefølge.
- `.agents/skills/` beskriver hvordan Codex skal utføre bestemte arbeidsformer.

Kode, migrasjoner, aktive API-ruter og verifisert runtime-adferd er teknisk fasit. Dokumentasjonen skal korrigeres når den ikke stemmer.

## Beslutningsgater

Før en større implementering skal et ADR minst ha:

- kontekst og problem
- valgt retning og begrunnelse
- relevante alternativer
- konsekvenser og risiko
- implementeringsetapper
- akseptansekriterier
- test-, migrerings- og rollbackkrav når det er relevant
- eksplisitt status for gjenværende godkjenninger

En skill eller Codex-session kan forberede beslutningsgrunnlaget, men prosjekteieren godkjenner produktretning og vesentlige risikovalg.

## Vedlikehold

Når en arbeidsflyt endres:

1. Oppdater den aktuelle `SKILL.md`.
2. Oppdater `agents/openai.yaml` hvis visningsnavn, kort beskrivelse eller eksempelprompt endres.
3. Kontroller at skillen fortsatt avslutter med `Output` og `Neste anbefalte skill`.
4. Kjør strukturell validering for alle skills.
5. Oppdater Skill Pack-katalogen og eksemplene dersom rolle eller overgang endres.
6. Start en ny Codex-session og kontroller eksplisitt og relevant implisitt aktivering.

Se `FREDRIK_SKILL_PACK.md` for teknisk struktur og `EXAMPLES.md` for praktisk bruk.
