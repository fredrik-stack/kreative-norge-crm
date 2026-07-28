# Fredrik Development System

Disse reglene gjelder for alt utviklingsarbeid i Kreative Norge CRM:

1. Ingen større implementering uten godkjent ADR.
2. Ingen funksjon er ferdig før dokumentasjonen er oppdatert eller kontrollert.
3. Stabil prosjektkunnskap skal ligge i `docs/`, ikke gjentas i prompts.
4. Diagnose → beslutning → implementering.

Start med `docs/README.md` og `docs/status/PROJECT_STATUS_CURRENT.md`. Følg `docs/development/WORKFLOW.md`, og bruk prosjektets skills under `.agents/skills/` når oppgaven passer.

Bruk `$start-arbeidsokt` ved utviklingsøkter som viderefører prosjektarbeid, og `$avslutt-arbeidsokt` før arbeidet overleveres eller sessionen avsluttes. GitHub og dokumentasjonen er varig hukommelse; samtaler og session-oppsummeringer skal verifiseres mot repoet.

Ved kontinuitet fra en ny ChatGPT-samtale brukes `$fortsett-prosjekt` som strategisk arbeidsrutine. I Codex er `$fortsett-prosjekt` bare en skrivebeskyttet bro som kontrollerer håndoffen og leder videre til `$start-arbeidsokt`.

Ikke omtal planlagt funksjonalitet som implementert. Ved motstrid mellom dokumentasjon og verifisert kode skal avviket synliggjøres før arbeidet fortsetter.
