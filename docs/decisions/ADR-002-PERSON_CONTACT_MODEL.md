# ADR-002: PersonContact som egen modell

## Status

Godkjent og implementert.

## Bakgrunn

En person kan ha flere e-postadresser og telefonnumre med ulike publiseringsvalg.

## Beslutning

Flere kontaktkanaler lagres i `PersonContact`, med type, primærmarkering og offentlighetsmarkering.

## Konsekvenser

Import og public må håndtere både direkte personfelt og normaliserte kontaktposter på en konsistent måte.