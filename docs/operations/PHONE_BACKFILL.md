# Kontrollert telefonbackfill

Denne operatørveien gjelder bare fase 4G etter
[ADR-010](../decisions/ADR-010-INTERNATIONAL_PHONE_IDENTITY_AND_NORMALIZATION.md).
Den setter eksplisitt region på den komplette, godkjente tenantsamlingen og
backfiller bare de additive canonical-feltene fra migrasjon `0032`.

## Sikkerhetskontrakt

`backfill_phone_identity` er read-only uten `--apply`. Forward-kjøring krever:

- alle tenant-ID-er eksplisitt og uten duplikater
- forventet eksakt antall tenants i databasen
- en eksplisitt støttet regionkode
- ved apply: unik batch-ID og absolutt manifestpath utenfor repoet
- ved apply: manifestmappe eid av operatøren og uten gruppe-/andretilgang

Kommandoen stopper ved tenantavvik, Person/primær PHONE-avvik, cross-tenant
kontakt eller konflikt mot en eksisterende canonical verdi. Output er
aggregert og inneholder ingen rå telefonverdier. Den rapporterer
klassifisering og faktiske endringer per modell, tenant og resultatgruppe samt
fingerprints for råtelefon, publisering og additive identitetsfelt.

Eksempel på tørrkjøring:

```bash
python manage.py backfill_phone_identity \
  --tenant-id <id-1> --tenant-id <id-2> --tenant-id <id-3> \
  --expect-total-tenants 3 \
  --default-region NO
```

Før live apply skal operatøren ha to identiske tørrkjøringer, uendrede
fingerprints, fersk verifisert Borg-backup og grønn isolert restore-/rollback-
smoke. Deretter brukes et nytt batchnavn og en no-clobber manifestfil:

```bash
python manage.py backfill_phone_identity \
  --tenant-id <id-1> --tenant-id <id-2> --tenant-id <id-3> \
  --expect-total-tenants 3 \
  --default-region NO \
  --batch-id <unik-batch-id> \
  --manifest-path /kontrollert-path/<unik-batch-id>.json \
  --apply
```

Etter apply skal samme forward-tørrkjøring gi `changes_total=0`. Råtelefon- og
publiseringsfingerprints skal være identiske før og etter. Manifestet skal være
operatøreid med eksakt filmodus `0600`, ikke legges i Git og beholdes sammen
med batch- og backupevidensen.

## Rollback

Rollback bruker bare manifestets additive felt og berører derfor ikke rå
telefon, publisering eller canonical data som eksisterte før batchen. Standard
er også her read-only:

```bash
python manage.py backfill_phone_identity \
  --rollback-manifest /kontrollert-path/<unik-batch-id>.json
```

Apply krever eksplisitt `--apply`. Rollback stopper uten delvis restore dersom
en batchrad senere har fått en annen additiv verdi. En vellykket live 4G-state
skal ikke reverseres som del av normal verifikasjon; rollback kjøres på isolert
restorekopi.
