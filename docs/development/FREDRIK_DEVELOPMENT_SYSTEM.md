# Fredrik Development System

**Status:** Gjeldende utviklingsplattform

**Sist oppdatert:** 2026-07-24

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

## Kontinuitets- og SESSION-lag rundt arbeidsflyten

Kontinuitetsrutinen og session-skillene kobler nye ChatGPT-samtaler til nye Codex-sessioner:

```text
ChatGPT: $fortsett-prosjekt
  → Codex: $fortsett-prosjekt
  → $start-arbeidsokt
  → LEVEL 1–4 etter behov
  → $avslutt-arbeidsokt
```

I ChatGPT er `$fortsett-prosjekt` en strategisk arbeidsrutine som bruker siste `CHATGPT SESSION SUMMARY` og produserer neste prioritet og første Codex-prompt. I Codex er navnet en tynn repo-skill som kontrollerer sammendraget mot repoet og delegerer til `$start-arbeidsokt`.

Oppstarten etablerer dagens fokus, verifisert dokument- og Git-status, åpne beslutninger, risiko, project health og neste arbeidsplan. Avslutningen kontrollerer faktisk utført arbeid, leveransestatus, dokumentasjonsbehov og varig lagring før den lager en standardisert handoff.

Codex-broen og session-skillene er skrivebeskyttede kontroll- og rutingsskills. De erstatter ikke fagarbeidet i LEVEL 1–4, og de overtar ikke strategisk prioritering, commit, push, merge, deploy eller dokumentasjonsoppdatering fra eksisterende arbeidsformer.

GitHub og dokumentasjonen er prosjektets varige hukommelse. En samtale, `CHATGPT SESSION SUMMARY` eller `SESSION WRAP-UP` skal peke til branch, commit, PR og dokumenter, men skal ikke behandles som teknisk fasit uten ny verifisering.

Beslutningen og den faste kontrakten er dokumentert i `docs/decisions/ADR-006-SESSION_WORKFLOW.md`. ChatGPT-rutinen og sammendragsmalen er dokumentert i `docs/development/CHATGPT_SESSION_CONTINUITY.md` og `docs/development/CHATGPT_SESSION_SUMMARY_TEMPLATE.md`.

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

Skillene foreslår neste naturlige skill i slutten av hvert resultat. Dette er veiledning, ikke automatisk kjeding. Session-start velger normalt inngang til riktig nivå, mens session-slutt pakker en kontrollert handoff.

## Ansvar og sannhetskilder

- `AGENTS.md` inneholder korte regler som Codex skal ha i hver prosjektøkt.
- `docs/status/PROJECT_STATUS_CURRENT.md` beskriver verifisert nåstatus.
- `docs/architecture/` beskriver faktisk system og dataflyt.
- `docs/features/` beskriver produktkrav og ønsket brukeropplevelse.
- `docs/decisions/` inneholder godkjente arkitekturbeslutninger.
- `docs/status/ROADMAP.md` viser planlagt rekkefølge.
- `.agents/skills/` beskriver hvordan Codex skal utføre bestemte arbeidsformer.
- Git og GitHub dokumenterer brancher, commits, PR-er, CI og hva som faktisk er delt.

Kode, migrasjoner, aktive API-ruter og verifisert runtime-adferd er teknisk fasit. Dokumentasjonen skal korrigeres når den ikke stemmer. Lokale, upushede endringer er ikke tilgjengelige for ChatGPT eller andre maskiner og skal markeres som ikke varig delt.

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
