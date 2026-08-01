# Kreative Norge backupmodul

**Operativ status:** PREPARED, NOT ACTIVE

Modulen implementerer den inaktive repo-delen av [ADR-008](../../docs/decisions/ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md). Den tar en konsistent PostgreSQL-dump, samler eksplisitt konfigurerte applikasjonsfiler og serverkonfigurasjon og oppretter et kryptert Borg-arkiv på en separat Hetzner Storage Box.

Ingen filer her aktiverer en timer automatisk. `install.sh activate` avviser aktivering før statusfilen beviser både vellykket backup, dump-/repository-verifikasjon og isolert restore av samme arkiv.

## Innhold

- `backup.sh`: preflight eller nattlig dump, arkiv, check, prune og compact
- `verify.sh`: ukentlig full repository-check
- `restore-smoke.sh`: isolert restore i en upublisert PostgreSQL 16-container
- `install.sh`: eksplisitte `prepare`, `generate-key`, `init-repository`, `preflight` og `activate`-steg
- `backup.env.example`: root-only konfigurasjonsmal uten secrets
- `status.py`: atomisk, ikke-sensitiv statusfil og sikker Borg-JSON-parsing
- `systemd/`: inaktive service- og timerfiler
- `tests/`: syntetiske feil- og gate-tester

Den autoritative operatørprosedyren, sikkerhetskravene og eksakt aktiveringsrekkefølge ligger i [BACKUP_AND_RESTORE.md](../../docs/operations/BACKUP_AND_RESTORE.md).
