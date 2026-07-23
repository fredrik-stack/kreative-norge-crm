# Export Architecture

**Status:** delvis implementert

Det finnes `ExportJob` med støtte for:

- eksporttyper
- CSV og XLSX som formatvalg
- filtre
- valgte felt
- jobbstatus
- filfelt og sammendrag

Grunnleggende API for eksportjobber finnes. Selve eksportmotoren, filgenerering, nedlasting og komplett UI-flyt er ikke bekreftet ferdig og skal ikke beskrives som implementert.

## Planlagt kontakt-eksport

`ADR-005` beslutter at fremtidig eksport skal skille mellom:

- intern arbeidsliste
- offentlig katalogeksport fra samme resolver som PUBLIC
- full relasjonell eksport av personer, kontakter, aktørkoblinger og offentlige kontakttildelinger

Intern kontakt-eksport skal være tenant-isolert, rollebeskyttet, logget og underlagt avklart filretensjon. Dette er ikke implementert.
