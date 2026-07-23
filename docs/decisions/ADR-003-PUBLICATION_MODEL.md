# ADR-003: Separat intern og offentlig publiseringsmodell

## Status

Godkjent og implementert som grunnmodell.

## Bakgrunn

CRM-et inneholder intern informasjon, mens public bare skal vise eksplisitt publiserte data.

## Beslutning

Offentlig visning styres av publiseringsfelter på aktør, kobling og kontaktkanal.

## Konsekvenser

Public-endepunkter skal aldri eksponere intern informasjon uten eksplisitt publiseringsvalg.