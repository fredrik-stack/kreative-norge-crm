# Staging backup activation 2026-08-02

**Status:** ACTIVE

**Verifisert:** 2026-08-02

Denne rapporten dokumenterer den kontrollerte aktiveringen av ADR-008s backupgrunnmur uten å lagre Storage Box-identitet, repository-ID, fingerprints, nøkkelpaths, credentials eller environmentverdier.

## Operativt resultat

- serverrepoet ble fast-forwardet til den godkjente backupmodulen uten applikasjonsdeploy, rebuild eller restart
- stabil Borg 1.2.8 passerte den felles versjonsgaten
- separat Storage Box med dedikert skrivbar subaccount, SSH-støtte og kryptert `repokey-blake2`-repository ble etablert
- host key ble kontrollert mot Hetzners offisielle, uavhengige fingerprintoversikt før den ble pin-net
- dedikert nøkkelinnlogging med `BatchMode=yes` passerte
- original passfrase og kryptert repositorynøkkel ble sikret separat off-server med verifisert checksum og tilgang for minst to ansvarlige
- den midlertidige serverkopien av repositorynøkkel-eksporten ble fjernet etter bekreftet custody
- første Storage Box-snapshot er aktivert og synlig
- Hetzner Cloud Backups er fortsatt aktivert, og prosjekteier har kontrollert en nyere synlig backup

## Backup- og restore-gater

| Kontroll | Resultat |
| --- | --- |
| Operativ preflight | PASS |
| Første manuelle systemd-backup | PASS |
| PostgreSQL custom-format dump og `pg_restore --list` | PASS |
| Manifest og checksums | PASS |
| Repository-ID og arkivstatus | PASS |
| Skrivebeskyttet repository-inspeksjon | PASS |
| Full repository- og dataverifikasjon | PASS |
| `activation-ready` blokkert før restore | PASS |
| Isolert PostgreSQL 16 restore av samme arkiv | PASS |
| Forventede CRM-tabeller og ufarlige tellinger | PASS |
| Restore-container og arbeidsområde ryddet | PASS |

Første backup brukte 8 sekunder. Den isolerte restore-smoke-testen brukte 8,7 sekunder og kjørte med tilfeldig containernavn, `--network none`, ingen publisert port og automatisk cleanup. Live database ble ikke brukt som restore-mål, og CRM-containerne ble ikke restartet eller gjenskapt.

## Aktiv timerstatus

- nattlig backup-timer er enabled og active med plan `02:30 Europe/Oslo` og inntil 30 minutters randomisert forsinkelse
- ukentlig verify-timer er enabled og active med plan søndag `04:30 Europe/Oslo` og inntil 30 minutters randomisert forsinkelse
- første observerte neste kjøring etter aktivering var 2026-08-03 02:33:49 Europe/Oslo for backup og 2026-08-09 04:59:04 Europe/Oslo for verify
- begge tilhørende tjenester var `inactive/success` etter kontrollen, og ingen relatert unit var failed

## Foreløpig RPO- og RTO-evidens

Den nattlige frekvensen gir et foreløpig backup-RPO på inntil omtrent 24 timer pluss randomisert timerforsinkelse og eventuell operativ forsinkelse. Risikofylte dataoperasjoner krever fortsatt en fersk manuell backup.

Målingen på 8,7 sekunder er bare evidens for isolert restore-smoke av dagens lille backupgrunnlag. Den er ikke et løfte om full katastrofe-RTO; ny host, tilgang til custody, repositoryoverføring, full applikasjonsrestore, nettverk og hendelsesledelse er ikke inkludert.

## Uendrede grenser og åpne risikoer

- backupaktiveringen deployet ikke applikasjonen og endret ikke database, data, publiseringsflagg, DNS eller Cloudflare
- dagens API-container mangler fortsatt host-persistent import-, eksport- og media-mount
- ekstern feilvarsling er fortsatt ikke etablert; daglig operatørkontroll må ha en tydelig eier
- Storage Box-snapshots og Cloud Backups er tilleggslag og erstatter ikke Borg eller logisk database-restore
