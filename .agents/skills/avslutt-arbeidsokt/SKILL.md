---
name: avslutt-arbeidsokt
description: Avslutt en utviklings-, planleggings- eller kvalitetsøkt i Kreative Norge CRM ved å verifisere faktisk arbeid, leveransestatus, dokumentasjonsbehov, risiko og neste handoff. Bruk før en Codex-session avsluttes, når arbeid skal overleveres, eller når brukeren trenger en standardisert SESSION WRAP-UP og neste Codex-prompt.
---

# Avslutt arbeidsøkt

Følg `AGENTS.md`, `docs/development/WORKFLOW.md` og `docs/development/DOCUMENTATION_RULES.md`. Verifiser mot repo, Git og tilgjengelig GitHub-status; ikke bruk samtalehistorikken alene som bevis.

1. Sammenlign dagens fokus og eventuell startbaseline med faktisk diff, staged diff, nye filer, commits og upstream. Ikke tilskriv økten filer som var skitne eller usporede før arbeidet startet.
2. Skill tydelig mellom:
   - **implementert:** finnes i lokal diff eller commit
   - **besluttet:** er uttrykkelig godkjent; oppgi om beslutningen er varig lagret
   - **foreslått:** er ikke godkjent eller implementert
3. Rapporter tester, lokal Docker, branch, commit, push, PR, CI, staging og merge som `verifisert`, `ikke kjørt`, `ikke relevant` eller `ukjent`.
4. List åpne feil, risiko og uavklarte spørsmål.
5. Kontroller om prosjektstatus, roadmap, ADR-er, arkitektur-, feature- eller changelogdokumentasjon må oppdateres.
6. Oppsummer **PROJECT HEALTH** med reglene i workflowen.
7. Foreslå én kort ChatGPT-prompt og én kort Codex-prompt som viser til branch, commit, PR og relevante dokumenter fremfor å gjenta stabil prosjektkunnskap.
8. Bruk denne faste rekkefølgen før sluttprompten:
   - `FAKTISK UTFØRT`
   - `IMPLEMENTERT / BESLUTTET / FORESLÅTT`
   - `LEVERANSESTATUS`
   - `ÅPNE FEIL, RISIKO OG SPØRSMÅL`
   - `DOKUMENTASJONSKONTROLL`
   - `PROJECT HEALTH`
   - `NESTE CHATGPT-PROMPT`
   - `NESTE CODEX-PROMPT`
   - `SESSION WRAP-UP`
9. Gjengi alltid `SESSION WRAP-UP` med nøyaktig denne strukturen og alle feltene:

```text
SESSION WRAP-UP
Dato:
Dagens fokus:
Faktisk utført:
Implementert:
Besluttet:
Foreslått, ikke besluttet:
Git:
  Branch:
  Last commit:
  Dirty/Clean:
  Ahead/Behind:
  Push:
  Open PR:
Verifisering:
  Tester:
  Docker:
  CI:
  Staging:
  Merge:
Dokumentasjon:
Åpne feil, risiko og spørsmål:
Neste oppgave:
Neste skill:
Varig lagret:
```

10. Avslutt svaret med seksjonen `Kopier inn i neste Codex-session` og en ferdig prompt i denne formen:

```text
$start-arbeidsokt

Dagens fokus: <neste konkrete oppgave>.
Verifiser branch, commit, PR og relevante dokumenter fra SESSION WRAP-UP.
Etter oppstartsrapporten: bruk $<anbefalt-skill> til <avgrenset handling og stoppunkt>.
```

Ikke endre kode eller dokumentasjon som del av avslutningskontrollen. Ikke stage, commit, push, merge eller deploy. Hvis noe mangler, anbefal riktig eksisterende skill; bruk den bare når brukeren uttrykkelig har bestilt videre arbeid.

## Output

En evidensbasert sluttrapport med faktisk arbeid, adskilt beslutningsstatus, komplett leveransematrise, project health, dokumentasjonsbehov, neste prompter, identisk `SESSION WRAP-UP` og en ferdig prompt for neste Codex-session.

## Neste anbefalte skill

Bruk `$oppdater-prosjektdokumentasjonen` når dokumentasjonsavvik gjenstår, `$gjennomga-siste-endring` når leveransen trenger kontroll, eller skillen som er angitt i neste arbeidsoppgave.
