# Fredrik Development System – eksempler

**Sist oppdatert:** 2026-07-23

Eksemplene viser når hver skill brukes i Kreative Norge CRM. De kan kopieres og tilpasses. Stabil prosjektkunnskap skal fortsatt leses fra `docs/`.

## LEVEL 1 – FORSTÅ

### `$forklar-for-fredrik`

Bruk når en teknisk situasjon må forklares uten å starte endringer.

```text
$forklar-for-fredrik

Forklar hvorfor PUBLIC kan vise en annen e-post enn Editor CRM, og hva «fallback» betyr i praksis. Ikke endre noe.
```

### `$grill-med-dokumentasjonen`

Bruk før en større implementering for å finne motsigelser og skjulte antakelser.

```text
$grill-med-dokumentasjonen

Kontroller ADR-005, DATA_MODEL, PUBLIC, IMPORT og roadmap mot dagens kontaktkode. Finn alt som fortsatt er uklart før kontaktomleggingen kan starte.
```

### `$undersok-feil-for-retting`

Bruk når symptomet er kjent, men rotårsaken ikke er dokumentert.

```text
$undersok-feil-for-retting

En kontaktpersons e-post vises i public HTML, men ikke i public API. Reproduser og følg dataflyten gjennom modell, serializer og template. Ikke rett feilen.
```

## LEVEL 2 – BESLUTT

### `$planlegg-ny-funksjon`

Bruk når et behov berører flere deler av produktet og må designes før kode.

```text
$planlegg-ny-funksjon

Design en samlet kontaktopplevelse for Editor, IMPORT, PUBLIC og EKSPORT med eksplisitt publisering og trygg GDPR-standard. Ikke implementer.
```

### `$ta-arkitekturavgjorelse`

Bruk når en godkjent design skal bli prosjektets formelle beslutning.

```text
$ta-arkitekturavgjorelse

Gjør den godkjente kontakt-designrapporten om til et ADR. Oppdater roadmap og prosjektstatus, men ikke kode eller migrasjoner.
```

### `$vurder-mvp-eller-overarbeid`

Bruk når et forslag kan være større enn brukerbehovet tilsier.

```text
$vurder-mvp-eller-overarbeid

Vurder om ny IMPORT trenger full gamification-motor nå, eller om fremdrift, prioritering og tydelig review-status er en bedre første leveranse.
```

## LEVEL 3 – BYGG

### `$skriv-codex-oppgave`

Bruk når en godkjent beslutning skal bli en avgrenset implementeringsprompt.

```text
$skriv-codex-oppgave

Lag oppgaven for første leveranse i ADR-005: kontrakts- og personverntester. Prompten skal vise til ADR og docs, ikke gjenta hele arkitekturen.
```

### `$trygg-databaseendring`

Bruk ved modeller, constraints, migrering eller eksisterende data.

```text
$trygg-databaseendring

Implementer den godkjente additive utvidelsen av PersonContact fra ADR-005. Behold legacy-felter, test backfill og dokumenter rollback.
```

### `$fullfor-til-staging`

Bruk når retning og akseptansekriterier er godkjent og leveransen skal helt til verifisert staging.

```text
$fullfor-til-staging

Gjennomfør den godkjente rettingen av thumbnail-preview, kjør relevante tester, oppdater docs, commit, push og kontroller brukerreisen i staging.
```

## LEVEL 4 – KVALITET

### `$gjennomga-siste-endring`

Bruk etter en commit eller push for å finne feil før neste gate.

```text
$gjennomga-siste-endring

Gjennomgå siste commit for kontakt-kontraktstester mot ADR-005. Prioriter personvernlekkasjer, falskt grønne tester og avvik fra scope.
```

### `$oppdater-prosjektdokumentasjonen`

Bruk når faktisk kode eller planstatus har endret seg.

```text
$oppdater-prosjektdokumentasjonen

Kontroller siste IMPORT-endring mot arkitektur, feature-dokument og PROJECT_STATUS_CURRENT. Oppdater bare dokumenter som faktisk er blitt utdaterte.
```

### `$klargjor-produksjonssetting`

Bruk når staging er godkjent og produksjonsrisiko skal vurderes, men deploy ikke er autorisert.

```text
$klargjor-produksjonssetting

Forbered produksjonssetting av den godkjente kontaktleveransen. Kontroller staging, migrering, backup, rollback og personvern. Stopp før deploy.
```
