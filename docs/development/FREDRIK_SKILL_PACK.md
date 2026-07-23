# Fredrik Development System – Skill Pack

**Status:** Installert og validert i repo

**Sist oppdatert:** 2026-07-23

**Plassering:** `.agents/skills/`

Skill Pack er den Codex-spesifikke arbeidsflytdelen av `FREDRIK_DEVELOPMENT_SYSTEM.md`.

## Offisielt grunnlag og valgt struktur

Strukturen er kontrollert mot OpenAIs gjeldende Codex-dokumentasjon og verifisert med `codex-cli 0.145.0-alpha.27` 2026-07-23.

Offisielle kilder:

- [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills)
- [OpenAI: Custom instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Agent Skills specification](https://agentskills.io/specification)

Dagens Codex støtter repo-baserte skills som mapper med en påkrevd `SKILL.md`. For et Git-repo søker Codex etter `.agents/skills` fra aktiv arbeidsmappe opp til repo-roten. Repoets skills ligger derfor flatt i:

```text
.agents/skills/
  <skill-navn>/
    SKILL.md
    agents/
      openai.yaml
```

Valgene følger OpenAIs dokumentasjon for skills og `AGENTS.md`:

- `.agents/skills/` er dokumentert plassering for prosjektbaserte skills.
- `.codex/` brukes ikke som prosjektets skill-katalog.
- `AGENTS.md` i repo-roten brukes til korte, varige prosjektinstruksjoner.
- Det finnes ikke et påkrevd skill-manifest for repoet.
- `agents/openai.yaml` er valgfri produktmetadata, ikke et manifest.
- README-filer inne i hver skill er unødvendige; den tekniske katalogen og eksemplene vedlikeholdes sentralt her i `docs/`.

## Metadata og navngivning

Hver `SKILL.md` har YAML-frontmatter med:

- `name`: små bokstaver, tall og bindestrek; identisk med mappenavnet
- `description`: kort beskrivelse av både hva skillen gjør og når den skal brukes

Hver `agents/openai.yaml` har:

- lesbart `display_name`
- kort `short_description`
- eksempel i `default_prompt` som nevner `$skill-navn`
- ingen verktøyavhengigheter, fordi disse arbeidsflytene bruker prosjektets normale Codex-verktøy

Implisitt aktivering er på som standard. Beskrivelsene er derfor skrevet slik at de viktigste triggerne kommer tidlig og overlapper minst mulig.

## Fire nivåer

### LEVEL 1 – FORSTÅ

- `$forklar-for-fredrik`
- `$grill-med-dokumentasjonen`
- `$undersok-feil-for-retting`

### LEVEL 2 – BESLUTT

- `$planlegg-ny-funksjon`
- `$ta-arkitekturavgjorelse`
- `$vurder-mvp-eller-overarbeid`

### LEVEL 3 – BYGG

- `$skriv-codex-oppgave`
- `$trygg-databaseendring`
- `$fullfor-til-staging`

### LEVEL 4 – KVALITET

- `$gjennomga-siste-endring`
- `$oppdater-prosjektdokumentasjonen`
- `$klargjor-produksjonssetting`

Nivåene er en konseptuell arbeidsflyt. Skills ligger ikke i nivå-undermapper fordi den dokumenterte oppdagelsesroten er `.agents/skills/`, og Codex har ingen dokumentert metadatafunksjon for nivågrupper eller tvungen rekkefølge.

## Hvordan Codex oppdager og bruker skills

Codex leser først `name`, `description` og filsti for tilgjengelige skills. Hele `SKILL.md` lastes først når skillen velges.

En skill kan brukes på to måter:

1. Eksplisitt: skriv `$skill-navn`, velg fra `$`-menyen eller bruk `/skills` i CLI/IDE.
2. Implisitt: beskriv en oppgave som tydelig matcher `description`.

Eksplisitt bruk anbefales når riktig arbeidsfase er viktig, for eksempel:

```text
$undersok-feil-for-retting

PUBLIC viser feil e-post for en kontaktperson. Finn rotårsaken, men ikke rett kode.
```

Codex oppdager normalt filendringer automatisk. Hvis en ny eller endret skill ikke vises, skal Codex startes på nytt fra repoet.

## Prioritet og overlapp

Codex skanner skills på repo-, bruker-, admin- og systemnivå. Skills med samme `name` blir ikke slått sammen eller overstyrt; begge kan vises. Prosjektet skal derfor unngå duplikate navn i andre skill-kataloger.

Implisitt valg styres av beskrivelsen og modellens vurdering, ikke av LEVEL-nummeret. `$skill-navn` er den sikre måten å velge en bestemt arbeidsflyt.

## Verifisering

Skill Pack verifiseres på tre nivåer:

1. **Struktur:** 12 mapper, hver med `SKILL.md` og `agents/openai.yaml`.
2. **Metadata:** gyldig YAML-frontmatter, samsvar mellom mappe og `name`, gyldig `openai.yaml`, unike navn og de påkrevde sluttdelene.
3. **Ny Codex-run:** start Codex fra repo-roten, åpne `/skills` eller `$`-menyen, og test minst én eksplisitt og én relevant implisitt prompt.

OpenAIs `quick_validate.py` brukes når Python-miljøet har PyYAML. Prosjektets verifisering skal i tillegg kontrollere arbeidsflytkrav som ikke inngår i standardvalidatoren.

Ved installasjonen 2026-07-23 ble alle 12 skills godkjent av standardvalidatoren. En ny, skrivebeskyttet Codex-run fra repo-roten bekreftet:

- at `AGENTS.md` ble lastet
- at alle fire grunnregler var aktive
- at alle 12 repo-skills var tilgjengelige
- eksplisitt aktivering av `$ta-arkitekturavgjorelse`
- implisitt valg av `$undersok-feil-for-retting` for et relevant feilsymptom

## Start en ny Codex-session

CLI:

```bash
cd /sti/til/kreative-norge-crm
codex
```

Kontroller deretter med `/skills` eller ved å skrive `$` at prosjekt-skillene vises. I VS Code skal repo-mappen åpnes som workspace før en ny Codex-samtale startes. Hvis instruksjoner eller skills virker utdaterte, avslutt den gamle samtalen og start en ny fra repoet.

## Begrensninger

- Codex har ingen dokumentert repo-manifestfil som grupperer skills i LEVEL 1–4.
- «Neste anbefalte skill» er tekstlig veiledning; Codex kjeder ikke skills deterministisk.
- Implisitt aktivering kan ikke garanteres. Bruk eksplisitt `$skill-navn` ved kritiske arbeidsfaser.
- Mange installerte skills deler et begrenset metadata-budsjett i startkonteksten. Codex kan forkorte beskrivelser eller utelate enkelte fra startlisten og vise en advarsel.
- `agents/openai.yaml` forbedrer presentasjon og invokasjon, men er ikke nødvendig for grunnleggende oppdagelse.
- En allerede startet sesjon kan ha lastet `AGENTS.md` én gang ved oppstart. Start ny sesjon etter endringer i prosjektinstruksjoner.
- Plugins er riktig distribusjonsformat hvis Skill Pack senere skal installeres utenfor dette repoet. Det er ikke nødvendig for prosjektlokal bruk.

## Vedlikehold

Bruk `$skill-creator` når en skill opprettes eller endres vesentlig. Hold stabil prosjektfakta i `docs/`, og hold `SKILL.md` fokusert på arbeidsmåte, stoppunkt og forventet resultat.

Alle skills skal avslutte med:

```text
Output
Neste anbefalte skill
```

Praktiske oppgaver finnes i `EXAMPLES.md`.
