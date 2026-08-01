# Kreative Norge backupmodul

**Operativ status:** PREPARED, NOT ACTIVE

Modulen implementerer den inaktive repo-delen av [ADR-008](../../docs/decisions/ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md). Den tar en konsistent PostgreSQL-dump, samler eksplisitt konfigurerte applikasjonsfiler og serverkonfigurasjon og oppretter et kryptert Borg-arkiv på en separat Hetzner Storage Box.

Ingen filer her aktiverer en timer automatisk. `install.sh activate` avviser aktivering før statusfilen beviser både vellykket backup, dump-/repository-verifikasjon og isolert restore av samme arkiv.

## Innhold

- `backup.sh`: preflight eller nattlig dump, arkiv, check, prune og compact
- `verify.sh`: ukentlig full repository-check
- `restore-smoke.sh`: isolert restore i en upublisert PostgreSQL 16-container
- `install.sh`: eksplisitte `prepare`, `generate-key`, `init-repository`, `export-recovery-key`, `inspect-repository`, `preflight` og `activate`-steg
- `backup.env.example`: root-only konfigurasjonsmal uten secrets
- `status.py`: atomisk, ikke-sensitiv statusfil og sikker Borg-JSON-parsing
- `systemd/`: inaktive service- og timerfiler
- `tests/`: syntetiske feil- og gate-tester

Den autoritative operatørprosedyren, sikkerhetskravene og eksakt aktiveringsrekkefølge ligger i [BACKUP_AND_RESTORE.md](../../docs/operations/BACKUP_AND_RESTORE.md).

Etter `init-repository` og registrering av forventet repository-ID er `export-recovery-key <absolute-destination>` neste obligatoriske manuelle recovery-steg. Kommandoen bruker samme root-only Borg-/SSH-/repository-ID-kontrakt som backupjobben, nekter overskriving og lager en root-eid `0600`-fil uten å skrive nøkkelmateriale til output. Den krypterte eksporten og den separate Borg-passfrasen må sikres off-server for minst to ansvarlige; dette er **MANUAL REQUIRED** og er ikke utført av repoet.

`inspect-repository` er en skrivebeskyttet statuskommando som viser verifisert repository-ID, antall relevante arkiver og nyeste sikre arkivnavn. Den lister ikke arkivmedlemmer og kjører ingen muterende Borg-kommandoer.

Backup, verify og restore deler én `flock`. En prosess uten låseierskap skriver aldri status eller oppretter restore-ressurser.
