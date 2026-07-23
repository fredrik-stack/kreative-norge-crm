# Fredrik Skill Pack

**Status:** installert i repo på `.agents/skills/`

**Formål:** gjøre arbeidsflyten mellom Fredrik, ChatGPT og Codex kortere, tryggere og mer konsekvent.

## Bruk

I Codex kan en skill normalt påkalles med `$skill-navn` eller ved å beskrive oppgaven slik at Codex velger riktig skill automatisk. Start Codex på nytt etter at nye skills er hentet lokalt.

## Prosjektets skills

1. `$forklar-for-fredrik` – forklar tekniske ting på norsk uten å forutsette utviklerbakgrunn.
2. `$planlegg-ny-funksjon` – lag gjennomarbeidet plan uten å kode.
3. `$grill-med-dokumentasjonen` – finn motsetninger, hull, risiko og overarbeid.
4. `$skriv-codex-oppgave` – lag en kort, komplett Codex-prompt som viser til repoets dokumentasjon.
5. `$fullfor-til-staging` – implementer, test, dokumenter, commit, push og kontroller staging.
6. `$gjennomga-siste-endring` – kontroller siste commit eller PR mot krav, kode og dokumentasjon.
7. `$oppdater-prosjektdokumentasjonen` – hold `docs/` synkronisert med faktisk app.
8. `$vurder-mvp-eller-overarbeid` – velg riktig løsningsnivå og unngå unødvendig kompleksitet.
9. `$trygg-databaseendring` – håndter modeller, migrasjoner og eksisterende data sikkert.
10. `$klargjor-produksjonssetting` – gjør produksjonskontroller, men stopp før deploy uten uttrykkelig godkjenning.
11. `$undersok-feil-for-retting` – finn dokumentert rotårsak før kode endres.

## Codex sine standard-/systemskills

Codex-distribusjonen kan også ha systemskills som følger installasjonen. De mest sentrale er:

- `$skill-creator` – opprette eller forbedre skills med korrekt `SKILL.md`-struktur.
- `$skill-installer` – installere kuraterte eller eksterne skills i brukerens Codex-oppsett.

Hvilke øvrige system- eller personlige skills som finnes, avhenger av Codex-versjonen og innholdet i brukerens lokale skill-katalog. Repoet kan ikke automatisk lese `~/.codex/skills` eller andre lokale mapper.

## Katalogstruktur

```text
.agents/skills/
  forklar-for-fredrik/SKILL.md
  planlegg-ny-funksjon/SKILL.md
  grill-med-dokumentasjonen/SKILL.md
  skriv-codex-oppgave/SKILL.md
  fullfor-til-staging/SKILL.md
  gjennomga-siste-endring/SKILL.md
  oppdater-prosjektdokumentasjonen/SKILL.md
  vurder-mvp-eller-overarbeid/SKILL.md
  trygg-databaseendring/SKILL.md
  klargjor-produksjonssetting/SKILL.md
  undersok-feil-for-retting/SKILL.md
```

## Arbeidsregel

Stabil prosjektkunnskap skal ligge i `docs/`. Skills skal beskrive arbeidsmåten. Den enkelte Codex-prompt skal primært beskrive den konkrete oppgaven, avgrensningen, akseptansekriteriene og stoppunktet.
