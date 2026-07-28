---
name: start-arbeidsokt
description: Start en utviklings-, planleggings- eller kvalitetsøkt i Kreative Norge CRM med verifisert prosjekt- og Git-status, åpne beslutninger, risiko, neste oppgave og anbefalt skill. Bruk ved ny Codex-session, ved gjenopptakelse etter et opphold eller før arbeid videreføres fra en tidligere handoff.
---

# Start arbeidsøkt

Følg `AGENTS.md`, `docs/README.md` og `docs/development/WORKFLOW.md`. Bruk GitHub og repoets dokumentasjon som varig hukommelse; en tidligere samtale eller `SESSION WRAP-UP` er bare et spor som skal verifiseres.

1. Sett **DAGENS FOKUS** fra brukerens oppgave. Hvis fokus mangler, bruk øverste uavsluttede prioritet i roadmap og merk det som en anbefaling.
2. Les `docs/status/PROJECT_STATUS_CURRENT.md`, `docs/status/ROADMAP.md`, relevante ADR-er og relevant arkitektur- og featuredokumentasjon.
3. Kontroller aktiv branch, upstream, dirty/clean, ahead/behind og siste commit. Kontroller åpen PR med tilgjengelig skrivebeskyttet GitHub-verktøy; bruk `ukjent` hvis den ikke kan verifiseres.
4. Skill mellom verifisert implementert, dokumentert planlagt, eksplisitt besluttet og fortsatt uavklart.
5. Identifiser åpne beslutninger, dokumentasjonsavvik, teknisk risiko og lokal tilstand som ikke er varig lagret.
6. Oppsummer **PROJECT HEALTH** med reglene i workflowen. Ikke kjør tester eller CI bare for å fylle ut startstatus; rapporter siste verifiserbare tilstand eller `ukjent`.
7. Foreslå én neste naturlig arbeidsoppgave, én primær skill og en kort konkret arbeidsplan med stoppunkt.

Bruk denne faste rekkefølgen:

1. `DAGENS FOKUS`
2. `VERIFISERT UTGANGSPUNKT`
3. `GIT-SNAPSHOT`
   - `Dirty/Clean`
   - `Branch`
   - `Ahead/Behind`
   - `Open PR`
   - `Last commit`
4. `NÅSITUASJON`
5. `ÅPNE BESLUTNINGER OG RISIKO`
6. `PROJECT HEALTH`
7. `ANBEFALT NESTE OPPGAVE`
8. `ANBEFALT SKILL`
9. `ARBEIDSPLAN`

Ikke endre kode, dokumentasjon eller ekstern tilstand. Ikke stage, commit, push, merge eller deploy. Hvis samme brukerprompt uttrykkelig ber om videre arbeid med en navngitt skill, fullfør først oppstartsrapporten og overlat deretter til den skillen.

## Output

En skrivebeskyttet oppstartsrapport i fast rekkefølge med dagens fokus, verifisert prosjekt- og Git-status, risiko, project health, neste oppgave, anbefalt skill og arbeidsplan.

## Neste anbefalte skill

Bruk skillen som oppstartsrapporten anbefaler. Ved ukjent feil er `$undersok-feil-for-retting` normalt neste steg; ved godkjent leveranse brukes `$fullfor-til-staging`.
