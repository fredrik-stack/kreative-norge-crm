# ADR-008: Hetzner one-server storage and backup baseline

## Status

Godkjent arkitekturretning og **ACTIVE** operativ backupgrunnmur. Den skrivebeskyttede [stagingbaselinen](../status/STAGING_BACKUP_BASELINE_2026-08-01.md) er fulgt av en kontrollert [aktivering 2026-08-02](../status/STAGING_BACKUP_ACTIVATION_2026-08-02.md). Storage Box-/Borg-kjeden, recovery-custody, første backup, full repository-check, isolert restore av samme arkiv, Storage Box-snapshot, nyere synlig Cloud Backup og begge systemd-timerne er verifisert grønne.

**Beslutningsdato:** 2026-08-01

**Dokumentert i repo:** 2026-08-02

Operativ status skal alltid bruke disse begrepene:

- **ACTIVE:** manuell backup og isolert restore er grønne, recovery-custody og manuelle Hetzner-kontroller er bekreftet, timerne kjører, og intern bilde-runtime er host-persistent og backup-/restore-verifisert
- **PREPARED:** kode, maler, tester og runbook finnes, men ekstern kjede er ikke aktivert
- **MANUAL REQUIRED:** en kontroll i Hetzner Console eller organisasjonens passordlager må utføres av prosjekteier
- **NOT IMPLEMENTED:** host-persistent default storage og eventuell migrering av generelle FileField-filer finnes ikke

## Bakgrunn

Kreative Norge CRM kjører Django, PostgreSQL og frontend på én Hetzner Cloud-server. GitHub beskytter kode og dokumentasjon, men er ikke backup av database, opplastede filer eller serverunik konfigurasjon. Dagens Compose-oppsett har et persistent PostgreSQL-volume, men ingen eksplisitt media-mount for API-containeren. Serverbaselinen 2026-08-01 fant verken `/app/imports`, `/app/exports` eller eksisterende filer i disse områdene. Django default storage peker likevel til `/app`; fremtidige `ImportJob.file`, preview-/feilrapporter og `ExportJob.file` kan derfor bli liggende i containerlaget og gå tapt ved recreate. Host-persistent default/media-storage krever en separat, kontrollert runtimeleveranse før slike filer tas i aktiv bruk.

[ADR-007](ADR-007-IMAGE_ASSET_ARCHITECTURE.md) definerer fortsatt bildeasset-, processing-, delivery-, takedown- og restoreinvariantene. Det krevde tidligere S3-kompatibel staging-/produksjonsstorage før en faktisk provider var valgt. Prosjekteier har nå valgt en enklere MVP: aktiv media forblir på dagens server, mens verifisert off-server backup etableres før bildearkitekturen implementeres.

## Beslutning

### Primærdata og media

- Django, PostgreSQL og aktiv media ligger på dagens Hetzner Cloud-server i MVP.
- PostgreSQL beholder sitt navngitte, persistente Docker-volume.
- Fremtidig media bruker lokale, navngitte Django `STORAGES`-aliaser og host-persistente kataloger under `/srv/kreative-norge/media/`.
- Planlagte standardområder er `default`, `private` og `public`; eksakt runtimekobling og eventuell migrering krever en egen fase og er ikke del av dette ADR-ets repoimplementering.
- Filer lagres ikke som databaseblob.
- Storage-abstraksjonen beholdes slik at senere flytting til objektlagring ikke krever omskriving av domenemodellen.
- S3, AWS, Backblaze, CDN og flerleverandørbackup utsettes. Objektlagring vurderes på nytt ved dokumentert vekst, kapasitetsgrense, tilgjengelighetskrav eller operasjonell belastning.

### Backup-lag

1. Primærdata ligger på Hetzner Cloud-serveren.
2. Den autoritative off-server data-/filbackupen er et kryptert Borg-repository på en separat Hetzner Storage Box.
3. Automatiske Storage Box-snapshots er et ekstra rollbacklag, ikke en erstatning for Borg.
4. Hetzner Cloud Backups er et ekstra helserverlag, ikke en erstatning for Borg eller logisk database-restore.
5. GitHub er autoritativ kilde for kode og dokumentasjon, ikke database- eller mediabackup.

Storage Box bør om mulig være i en annen Hetzner-lokasjon enn applikasjonsserveren. Dette er ett leverandørvalg med separate failure-domains, ikke en flerleverandørstrategi.

Den verifiserte baselinen målte et svært lite database- og filgrunnlag. Aktiv startplan er BX11 med 1 TB i FSN1. Applikasjonsserveren står i HEL1, slik at FSN1 gir fysisk lokasjonsseparasjon innen Hetzner. Kapasiteten vurderes på nytt ved 60–70 prosent faktisk bruk, og minst 20–30 prosent holdes ledig for Borg-vekst og Storage Box-snapshots. Fremtidig bildevekst er ikke regnet som eksisterende data.

Hetzner Cloud Backups er fortsatt aktivert etter prosjekteiers manuelle Console-kontroll 2026-08-02, og en nyere helserverbackup er synlig. Console viste tidligere 0 Cloud Volumes. Dette endrer ikke kravet om logisk PostgreSQL-dump, Borg, Storage Box eller restore-smoke.

### Borg-kontrakt

- Lokal Borg-klient er pin-net til en stabil versjon `>=1.2.8` og `<1.3.0`, mens eksplisitt Hetzner remote path forblir `borg-1.2`.
- Eldre `1.2.x`, `1.3.x`, `2.x`, prerelease og malformed eller ukjent versjonsoutput avvises før repository- eller backuparbeid. Repository-init, key export, inspect, backup, verify og restore bruker samme port uten en generell environment-bypass.
- Valget følger Hetzners dokumenterte Borg-støtte og prosjektets sikkerhetsminimum; en eventuell eldre distrobackport krever en senere eksplisitt og sporbar beslutning.
- Repository bruker `repokey-blake2`-kryptering og en recovery-hemmelighet i en root-only fil, aldri i Git eller repository-URL.
- Etter repository-init og registrering av forventet repository-ID skal operatøren eksplisitt eksportere Borgs krypterte repositorynøkkel med `install.sh export-recovery-key <absolute-destination>`. Kommandoen verifiserer samme Borg-/SSH-/repository-ID-kontrakt, nekter overskriving, krever en sikker absolutt path utenfor repoets backupkilder og lager bare en root-eid `0600`-fil.
- Eksporten inneholder ikke passfrasen og kopieres eller synkroniseres ikke automatisk. Både original passfrase og eksportert nøkkel må sikres off-server; den lokale overføringskopien fjernes etter manuelt verifisert custody uten løfte om sikker overskriving eller sikker sletting på SSD.
- Tilgang bruker dedikert Storage Box-subaccount når tilgjengelig, dedikert SSH-nøkkel og en dedikert `known_hosts`-fil med `StrictHostKeyChecking=yes`.
- Konfigurasjonen må inneholde forventet 64-tegns repository-ID. Backup, check, prune og restore stopper ved mismatch eller ukjent identitet.
- `install.sh inspect-repository` er den skrivebeskyttede operatørkommandoen for repository-status. Den bruker samme preflight og viser bare verifisert repository-ID, antall relevante arkiver og nyeste sikre arkivnavn; den lister aldri arkivmedlemmer og kjører ingen muterende Borg-kommando.
- Første MVP bruker ikke et komplisert append-only/admin-key-regime. Append-only kan vurderes som senere hardening.
- Original Borg-passfrase, eksportert kryptert repositorynøkkel og nødvendig Storage Box-identitet/repository-ID må ligge i godkjent off-server custody med tilgang for minst to ansvarlige. Kode kan ikke bevise passordmanageren eller menneskelig custody; dette forblir **MANUAL REQUIRED**, og før det er bekreftet er kjeden ikke fullt gjenopprettbar.

### Pathkontrakt

- Alle konfigurerte paths valideres semantisk før muterende filsystem-, Docker- eller Borg-operasjoner.
- Dedikert backup-state inneholder work, status, restore-gate og Borgs cache/config/security på faste paths. Ambient Borg-directoryvariabler kan ikke flytte disse til andre systemområder.
- Host-media er en eksplisitt allowlist av underkataloger under `/srv/kreative-norge/media/`; API-containerens media er eksplisitte underkataloger under `/app`, aldri `/` eller hele `/app`.
- Root, brede systemområder, parent traversal, ikke-normaliserte paths, symlinkkomponenter og mediaoverlapp med apprepo, backup-state, recovery-secret, SSH-key, `known_hosts` eller serverkonfigurasjon avvises fail-closed.
- Recovery-key-export krever en operator-eid destinasjonsparent som ikke er group/world-writable og oppretter sluttfilen atomisk uten overskriving. Eksisterende filer, directories, symlinks og beskyttede destinasjoner avvises; sluttfilen forblir root-eid mode `0600`.

Hetzner dokumenterer tilgjengelige Borg remote paths i [Storage Box: SSH/rsync/Borg](https://docs.hetzner.com/storage/storage-box/access/access-ssh-rsync-borg/). Borg dokumenterer `--remote-path` i [Borg usage](https://borgbackup.readthedocs.io/en/stable/usage/general.html#environment-variables) og sikkerhetsrettelser i [Borg 1.2 change log](https://borgbackup.readthedocs.io/en/1.2.8/changes.html).

### Nattlig backup

Hver vellykkede kjøring inneholder:

- `pg_dump --format=custom --no-owner --no-acl` fra kjørende PostgreSQL uten restart eller datastopp
- obligatorisk `pg_restore --list` før arkivering
- eksisterende, konfigurerte FileField-/mediaområder, inkludert `/app/imports` og `/app/exports` fra API-containeren når de finnes
- eksplisitt allowlistede host-paths under `/srv/kreative-norge/media/` når de finnes; nye områder må legges til og restore-verifiseres før aktivering
- eksplisitt allowlistet serverkonfigurasjon: aktiv Compose-/environmentfil, Caddy, backupkonfigurasjon uten innebygd secret og systemd-units
- manifest uten persondata eller secretverdier, samt checksums av dump og stagingbundles

Private SSH-nøkler, recovery-secret, eksportert repositorynøkkel, hele `/etc`, home-kataloger, rått live databasevolume, Docker-lag, caches, staticfiles, `node_modules`, Python-cache og store applikasjonslogger ekskluderes. Export-kommandoen avviser destinasjoner i applikasjonsrepo, backup-workdir, beskyttede mediaområder og allowlistede serverkonfigurasjonsfiler.

Arbeidskatalogen er root-only og må ha databaseomfang pluss minst 1 GiB ledig før dump. Midlertidige filer slettes ved både suksess og feil.

### Retention og verifikasjon

Standard retention er konfigurerbar til 14 daglige, 8 ukentlige og 12 månedlige arkiver. Prune og compact kjører bare etter vellykket ny backup og en avgrenset repository-check. En ukentlig separat timer verifiserer repository, arkiver og data.

Daglig frekvens gir et foreløpig backup-RPO på inntil omtrent 24 timer, i tillegg til randomisert timerforsinkelse og eventuell operativ forsinkelse. Risikofylte dataoperasjoner krever fortsatt en fersk manuell backup. Første manuelle backup brukte 8 sekunder. Isolert restore-smoke av samme arkiv brukte 8,7 sekunder, men dette er bare teknisk restore-evidens for dagens lille datagrunnlag og ikke et løfte om full katastrofe-RTO.

### Restore- og aktiveringsgate

Timeraktivering krever i denne rekkefølgen:

1. grønn preflight
2. manuelt bekreftet off-server custody av original Borg-passfrase, eksportert kryptert repositorynøkkel, nødvendig Storage Box-identitet/repository-ID og tilgang for minst to ansvarlige
3. verifisert ledig disk og `pg_restore --list`
4. første manuelle krypterte Borg-backup
5. skrivebeskyttet repository-inspeksjon, arkiv- og manifestkontroll
6. grønn repository-check
7. isolert restore til en PostgreSQL 16-container uten port og uten live databasetilknytning
8. forventede CRM-tabeller og ufarlige tellinger uten datautskrift
9. checksum av representativ mediafil når en finnes
10. manuell kontroll av Storage Box-snapshots og Hetzner Cloud Backups

`install.sh activate` håndhever de tekniske backup-/restoreportene. Prosedyren kan ikke teknisk bevise passordlager- eller Console-stegene; operatøren må dokumentere dem separat. Ingen CRM-container restartes eller gjenskapes av backupmodulen.

### Drift og varsling

Backup kjører nattlig via systemd med `Persistent=true`, randomisert forsinkelse, felles `flock`, lav CPU-/I/O-prioritet og journalføring. Backup, verify og restore bruker samme lås. Bare prosessen som har ervervet låsen kan skrive operativ status; lock contention feiler med `already running` uten å opprette eller endre statusfilen. En root-only JSON-statusfil registrerer siste start, suksess, feil, arkiv, dumpstatus, repositorystatus og restorestatus uten secrets.

Ingen ekstern varslingstjeneste innføres. Manglende proaktiv ekstern varsling er en åpen driftsrisiko inntil serveren eventuelt viser en allerede sikker, brukt kanal.

## Begrunnelse

Denne løsningen beskytter dagens viktigste data uten å gjøre bildearkitekturen avhengig av en ny provider-, CDN- eller IAM-flate. Borg gir kryptert, deduplisert og testbar off-server backup, mens lokale Django-storagealiaser holder senere migrering mulig. Samtidig er restore, ikke bare arkivopprettelse, en eksplisitt aktiveringsport.

## Konsekvenser

### Positive

- én forståelig driftskjede og én leverandør
- separat off-server failure-domain for database, media og konfigurasjon
- kontrollert retention og isolert restore-bevis
- ingen endring i CRM-runtime, modeller, API, Editor, PUBLIC eller Import 2.0

### Risiko og begrensninger

- aktiv server er fortsatt et enkelt tilgjengelighetspunkt mellom backupene
- ingen eksisterende generelle FileField-filer ble funnet i containerområdene 2026-08-01; bildeområdene er senere gjort persistente, men nye default-storage-filer kan fortsatt forsvinne ved container-recreate
- Storage Box-snapshots bruker kapasitet på samme boks og er ikke uavhengig katastrofebackup; se [Hetzner Storage Box snapshots](https://docs.hetzner.com/storage/storage-box/snapshots/)
- Cloud Backup-status må fortsatt kontrolleres i Console; en nyere backup ble verifisert 2026-08-02, men Cloud Backup er bare et ekstra helserverlag
- recovery avhenger av både korrekt sikret original Borg-passfrase, eksportert kryptert repositorynøkkel og nødvendig Storage Box-identitet/repository-ID; custody er bekreftet for minst to ansvarlige, men forblir en manuell organisatorisk kontroll
- ingen ekstern feilvarsling er etablert
- foreløpig RPO og restore-smoke-varighet er målt, men full katastrofe-RTO, diskvekst og senere representative restoreforløp må fortsatt måles

## Avviste eller utsatte alternativer

- S3/AWS/Backblaze/CDN nå: utsatt fordi MVP-behovet kan dekkes med lokal media og verifisert off-server backup.
- flerleverandørbackup: utsatt for å holde drift og recovery forståelig.
- bare Hetzner Cloud Backups eller bare Storage Box-snapshots: avvist fordi ingen av dem erstatter verifisert, applikasjonsbevisst Borg-backup og logisk PostgreSQL-restore.
- råkopi av live PostgreSQL-volume: avvist; konsistent custom-format dump brukes.
- automatisk aktivering ved installasjon: avvist; restore-gaten må være grønn først.

## Implementeringsstatus

- **ACTIVE:** separat Storage Box, kryptert Borg-repository, dedikert nøkkel og pin-net host key, off-server recovery-custody for minst to ansvarlige, første backup, full repository-check, isolert restore av samme arkiv, Storage Box-snapshot, nyere synlig Cloud Backup og aktive nattlige/ukentlige timere
- **MANUAL REQUIRED:** løpende custody-, snapshot- og Cloud Backup-kontroll kan ikke bevises av kode og må fortsatt eies av operatør
- **ACTIVE:** intern lokal bilde-runtime i staging, eksplisitte host mounts, persistence-probe og backup-/restore-verifikasjon; se [aktiveringen 2026-08-10](../status/STAGING_IMAGE_RUNTIME_ACTIVATION_2026-08-10.md)
- **NOT IMPLEMENTED:** host-persistent default storage, migrering av generelle FileField-filer og offentlig media-serving

Cloud Backups og Storage Box-snapshots teller fortsatt ikke alene som `ACTIVE`; statusen bygger på hele den verifiserte backup-, recovery- og restorekjeden.
