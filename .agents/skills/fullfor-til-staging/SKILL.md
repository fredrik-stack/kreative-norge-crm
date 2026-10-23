---
name: fullfor-til-staging
description: Gjennomfør en godkjent endring i Kreative Norge CRM fra implementering til test, commit, push, staging og kontroll uten unødvendige spørsmål. Bruk når retning og akseptansekriterier allerede er avklart.
---

# Fullfør til staging

Følg `AGENTS.md`, `docs/development/WORKFLOW.md` og gjeldende godkjente beslutning. Stopp hvis en større implementering mangler godkjent ADR.

1. Kontroller mandatets scope, aksept, tillatte handlinger og sluttpunkt mot workflowen. Skills utvider ikke fullmakten.
2. Les relevante kilder; implementer minste robuste løsning, test og oppdater/kontroller dokumentasjonen. Bruk isolert lokal Docker/PostgreSQL når risiko eller relevante eksisterende porter krever det.
3. Commit, push og opprett draft PR med mandat, endringer og faktisk validering.
4. Bruk en faktisk separat reviewer med `$gjennomga-siste-endring`, bundet til dokumentert base/head. Reviewer er skrivebeskyttet og endrer heller ikke PR-en. Egenkontroll er ikke uavhengig review.
5. Lagre reviewresultat med versjonsreferanser; rett funn innen mandatet, retest og innhent relevant nytt review av endringer etter review.
6. Gjør PR-en klar og utfør bestilt ordinær merge først etter review uten blokkerende funn og nødvendige grønne kontroller på siste head. Bevar påkrevde godkjenninger og branchregler uten adminomgåelse.
7. Verifiser nødvendig main-CI på mergecommiten. Utfør staging bare når bestilt og driftsportene er oppfylt; dokumentasjonsendringer alene skal ikke deployes.
8. Publiser sanitert evidens/status gjennom samme review-/merge-/CI-flyt. Lenker i PR-en skal vise faktisk kode-, deploy-, måle- og aktiveringsstatus. Ikke lag ny dokumentasjonsrunde bare for å registrere dokumentasjonsmergen.
9. Fortsett gjennom autoriserte steg og trygge rettinger uten nye bekreftelser. Lever ett samlet `$avslutt-arbeidsokt` ved sluttpunkt eller reell blokkering etter workflowens stoppregler.

Denne skillen eier også publisering av en bestilt dokumentasjonsleveranse etter
`$oppdater-prosjektdokumentasjonen`. Ikke produksjonssett eller utfør destruktive
databaseoperasjoner uten uttrykkelig mandat. Ikke start neste produktetappe.

## Output

En sporbar leveranse ved mandatets sluttpunkt, med separate statuser for review, PR, merge, CI, eventuell staging og evidens. Ingen stagingpåstand ved ren dokumentasjonsleveranse.

## Neste anbefalte skill

Bruk `$gjennomga-siste-endring` under leveransen; `$avslutt-arbeidsokt` ved faktisk sluttpunkt eller reell blokkering.
