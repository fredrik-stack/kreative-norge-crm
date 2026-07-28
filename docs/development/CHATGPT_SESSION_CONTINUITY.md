# ChatGPT session continuity

**Status:** Gjeldende arbeidsrutine

**Sist oppdatert:** 2026-07-28

## Formål

`$fortsett-prosjekt` er den felles språklige inngangen når prosjektarbeid flyttes mellom en ny ChatGPT-samtale og en ny Codex-session.

GitHub og repoets dokumentasjon er prosjektets varige hukommelse. En `CHATGPT SESSION SUMMARY` er en strategisk håndoff som hjelper neste samtale å forstå hva som skjedde, men er ikke varig teknisk sannhet og kan ikke overstyre Git, ADR-er, prosjektstatus, roadmap eller verifisert runtime.

## `$fortsett-prosjekt` i ChatGPT

I ChatGPT er `$fortsett-prosjekt` en arbeidsrutine, ikke en teknisk Codex-skill. Den brukes sammen med siste `CHATGPT SESSION SUMMARY`.

ChatGPT skal når tilgang finnes:

1. lese eller kontrollere oppdatert GitHub-repo og relevante dokumenter
2. plassere forrige arbeidsøkt i strategisk og arkitektonisk sammenheng
3. skille besluttet, implementert og foreslått
4. kontrollere hva som faktisk er pushet eller dokumentert
5. vurdere om tidligere prioritering fortsatt er riktig
6. anbefale neste strategiske prioritet
7. lage første konkrete Codex-prompt, normalt med `$start-arbeidsokt` og angitt fokus

Hvis ChatGPT ikke har repo- eller GitHub-tilgang, skal manglende verifisering sies eksplisitt. Sammendraget skal aldri brukes som bevis for at kode, commit, CI, staging eller dokumentasjon finnes.

Fast ChatGPT-output:

1. `HVOR STÅR PROSJEKTET?`
2. `VIKTIGSTE BESLUTNINGER`
3. `HVA LÆRTE VI?`
4. `VIKTIGSTE RISIKO`
5. `NESTE STRATEGISKE PRIORITET`
6. `NESTE CHATGPT-FOKUS`
7. `KOPIER INN I NY CODEX-SESSION`

## Avslutning av en ChatGPT-økt

Avslutt en strategisk ChatGPT-økt ved å:

1. fylle ut `CHATGPT_SESSION_SUMMARY_TEMPLATE.md`
2. skille uttrykkelig mellom beslutning, implementasjon og forslag
3. oppgi hva som er pushet eller dokumentert, og hva som bare finnes i samtalen eller lokalt
4. unngå å kopiere stabil teknisk prosjektkunnskap som allerede ligger i `docs/`
5. lagre viktige godkjente beslutninger i ADR, roadmap eller prosjektstatus gjennom riktig arbeidsflyt

Sammendraget kan kopieres til neste ChatGPT-chat, men det blir først varig prosjektminne når de relevante fakta er lagret og pushet i repoet.

## Oppstart av en ny ChatGPT-chat

Lim inn:

```text
$fortsett-prosjekt

<siste CHATGPT SESSION SUMMARY>
```

Be ChatGPT kontrollere repoet når tilgang finnes. Resultatet skal ende med en konkret Codex-prompt som viser til relevante dokumenter fremfor å gjenta deres stabile innhold.

## Bruk av den resulterende Codex-prompten

Kopier `KOPIER INN I NY CODEX-SESSION` til en ny Codex-session fra repoet. Prompten skal normalt:

- bruke `$start-arbeidsokt`
- angi ett konkret teknisk fokus
- be Codex verifisere sammendraget mot repoet
- navngi neste fag-skill bare når arbeidsfasen allerede er avklart

Hvis hele `CHATGPT SESSION SUMMARY` skal følge med inn i Codex, kan prompten bruke `$fortsett-prosjekt`. Codex-broskillen kontrollerer da sammendraget før den delegerer til `$start-arbeidsokt`.

## Forskjellen mellom inngangene

| Inngang | Miljø | Ansvar | Skal ikke |
| --- | --- | --- | --- |
| `$fortsett-prosjekt` | ChatGPT | Strategisk kontinuitet, prioritering og første Codex-prompt | Påstå teknisk status uten repo-verifisering |
| `$fortsett-prosjekt` | Codex | Kontrollere ChatGPT-handoff og delegere teknisk baseline | Prioritere produktstrategi eller implementere |
| `$start-arbeidsokt` | Codex | Verifisere dokumentasjon, Git, risiko og teknisk arbeidsplan | Bruke sammendrag som sannhetskilde eller endre filer |

## Varig lagring

- Godkjente arkitekturvalg lagres i `docs/decisions/`.
- Strategisk rekkefølge lagres i `docs/status/ROADMAP.md`.
- Verifisert nåstatus lagres i `docs/status/PROJECT_STATUS_CURRENT.md`.
- Implementasjon og historikk lagres i Git og pushes til GitHub.
- Samtaler og session-sammendrag er midlertidige arbeidsflater.
- Session-flyten skal ikke generere parallelle `*REFERENCE`-, `*STATUS`- eller håndoffdokumenter i repo-roten. Oppdater den autoritative filen under `docs/`, eller oppbevar midlertidige kontekstpakker utenfor repoet.
