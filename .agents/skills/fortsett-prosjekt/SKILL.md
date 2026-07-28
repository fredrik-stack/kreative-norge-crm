---
name: fortsett-prosjekt
description: Fortsett Kreative Norge CRM i Codex fra en ny session ved å kontrollere en eventuell CHATGPT SESSION SUMMARY mot Git, GitHub og prosjektdokumentasjonen og deretter delegere teknisk oppstart til `$start-arbeidsokt`. Bruk når en ChatGPT-handoff følger med, når brukeren skriver `$fortsett-prosjekt`, eller når strategisk kontekst skal kobles trygt til en ny Codex-session.
---

# Fortsett prosjekt

Følg `AGENTS.md`, `docs/development/CHATGPT_SESSION_CONTINUITY.md` og session-kontrakten i `docs/decisions/ADR-006-SESSION_WORKFLOW.md`. Les `$start-arbeidsokt` før den tekniske oppstarten.

1. Les eventuell medfølgende `CHATGPT SESSION SUMMARY`. Fravær av sammendrag er ikke en blokkering.
2. Trekk bare ut øktspesifikt fokus, påståtte beslutninger, læring, risiko og henvisninger til varig lagring.
3. Kontroller at sammendraget ikke overstyrer GitHub, Git, prosjektstatus, roadmap, ADR-er eller verifisert kode/runtime.
4. Merk alle konflikter som `SAMMENDRAG ↔ REPO` og oppgi hvilken verifisert kilde som gjelder.
5. Bruk angitt Codex-fokus når det er konsistent med repoet. Hvis fokus mangler, bruk øverste uavsluttede roadmap-prioritet som anbefaling.
6. Deleger den tekniske oppstarten til `$start-arbeidsokt` og følg dens komplette outputkontrakt. Ikke dupliser eller forkort Git-, risiko- eller project-health-kontrollene.

I Codex er dette en tynn bro, ikke strategisk produktprioritering. Ikke endre filer, starte implementering, stage, committe, pushe, merge eller deploye. En senere handling krever en ny uttrykkelig bestilling og riktig fag-skill.

## Output

En kort `KONTINUITETSKONTROLL` med status for sammendraget, eventuelle `SAMMENDRAG ↔ REPO`-konflikter og valgt teknisk fokus, fulgt av den komplette skrivebeskyttede rapporten fra `$start-arbeidsokt`.

## Neste anbefalte skill

Bruk skillen som `$start-arbeidsokt` anbefaler etter at kontinuitetskontrollen og den tekniske baseline er fullført.
