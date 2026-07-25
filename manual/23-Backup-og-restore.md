# Kapittel 23 – Backup og restore

Jeg trodde lenge at GitHub var backup. Det beskytter kodehistorikken, men ikke dataene brukerne har lagt inn. I et CRM ligger mye av verdien i databasen.

## Hva må kunne gjenopprettes?

En backup er en separat kopi som kan brukes når originalen blir slettet, skadet eller utilgjengelig. For CRM-et må en beredskapsplan vurdere:

- PostgreSQL-databasen
- opplastede og permanent lagrede filer
- nødvendig server- og Docker-konfigurasjon
- driftsoppsett utenfor repoet
- secrets fra sikker lagring

Kode og dokumentasjon kan hentes fra GitHub. Miljøvariabler skal ikke committes, men må oppbevares sikkert slik at en ny server kan konfigureres.

Et Docker-volum gjør at databasedata overlever en vanlig omstart av containeren. Det er ikke en backup: Volumet kan forsvinne sammen med serveren eller bli skadet sammen med originaldataene.

## Restore er testen på backupen

*Restore* betyr å gjenopprette systemet fra en backup. En fil som aldri er testet, er bare en antatt backup.

En kontrollert restore-test bør:

1. bruke et separat miljø, ikke overskrive produksjon
2. gjenopprette database og nødvendige filer
3. starte riktig kode- og konfigurasjonsversjon
4. kontrollere innlogging og viktige data
5. dokumentere feil og manglende trinn

Flere enn én person må kunne følge rutinen. Ellers er prosjektet fortsatt personavhengig.

## Hyppighet og plassering

Hyppigheten avhenger av hvor mye data prosjektet tåler å miste. Et daglig brukt CRM bør normalt ha minst daglige databasekopier utenfor produksjonsserveren.

Bestem også hvor lenge kopiene beholdes og hvem som har tilgang. Én ny kopi er utilstrekkelig hvis feilen oppdages sent. Automatisering bør varsle når backup uteblir eller feiler.

## Status i Kreative Norge CRM

Staging bruker et navngitt PostgreSQL-volum, men repoet dokumenterer ingen verifisert automatisk databasebackup eller testet restore. Backup og tilbakeføring er krav før risikofylte kontaktendringer. Dette er uferdig driftsarbeid, ikke etablert beskyttelse.

## Takeaways

- Git beskytter kodehistorikken; databasebackup beskytter CRM-verdiene.
- Docker-volumer og backup løser forskjellige problemer.
- Kopier må lagres separat, sikres og tas ofte nok.
- En backup er ikke pålitelig før restore er testet.
- Gjenoppretting skal være dokumentert og forstått av flere.

## Prinsippet

Kode kan bygges opp igjen. Uerstattelige data krever separate, testede kopier og en kjent vei tilbake.
