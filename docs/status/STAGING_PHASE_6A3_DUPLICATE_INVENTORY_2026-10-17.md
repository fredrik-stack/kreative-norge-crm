# 6A.3 – skrivebeskyttet duplikatinventar og beskrivende migreringsmanifest

**Dato:** 2026-10-17. **Status:** INVENTAR FULLFØRT / SKRIVEBESKYTTET REVIEW FULLFØRT UTEN KRITISKE ELLER VIKTIGE FUNN / DOKUMENTASJON PUBLISERT I PR #81.
Reviewresultatet er registrert i denne dokumentasjonsleveransen. Dokumentasjonen er publisert og merget gjennom [PR #81](https://github.com/fredrik-stack/kreative-norge-crm/pull/81) på `ed8b70b93068124d525d80b26e2f3d9085dc727f`, med main-CI `39067291349` success (6/6), verifisert 2026-10-23. Dette ajourfører publiseringsstatus, ikke inventarsnapshotet. Ingen ny eiergodkjenning av dataretting eller aktivering inngår. Ingen shadow eller ny runtimefunksjon er implementert eller aktivert; hele 6A er ikke ferdig.

## Mandat og baseline

Uttrykkelig godkjent 6A.3-bestilling: diagnose og kartlegging, uten generell ny planrunde. Kandidater, strukturelle integritetsavvik og datadekning rapporteres separat. Ingen identitetsavgjørelse, automatisk merge, catch-up eller retting.

- Lokal og fersk GitHub-main: `4e7661b1314299aeb0fbbf891de36a7d890b605e`; PR #80 MERGED 2026-10-17 19:26:34 UTC. PR-CI 6/6 success; eksisterende main-CI `39062484867` success. Ingen ny CI eller testsuite kjørt.
- Ren stagingcheckout: `63743441a173d2c1b4c71d9f9011b93fbadd2ca4`. Main har bare dokumentasjonsendringer siden runtimebaselinen; ingen deploy er nødvendig for inventaret.
- Aktiv API-container: `4192604eb5d726f700aeed7cb08ed37877ded6f23fca3c7053a61f336eba485c`.
- Image: `sha256:bfdc9d281ddf1fab03152f9a85d12a4bfd70df5ae5f2506d3b9bb5ee743d34fb`. Samme container/image var running med restart count 0 ved sluttkontroll.
- Checksums for modeller, importnormalisering, telefonadapter, importmatcher, API-views og backfilltjeneste samsvarte mellom faktisk API og lokal main.
- Databaseidentitet: `postgresql:7621672066239828005:crm_db`, verifisert fra `pg_control_system()` og `current_database()`.
- SharingDomain: eksakt ID 1 / `musikkontoret` / `Musikkontoret`; eksakte sju tenants nedenfor. Domainets faktiske tenantsett er likt bestilt sett. Ingen ukjent identitet eller scopeutvidelse.

## Snapshot og skrivebeskyttelse

Autoritativt sluttsnapshot: **2026-10-17 19:58:19.652017–19:58:19.688472 UTC / 21:58:19 CEST**. PostgreSQL snapshot `25160:25160:`. Start- og sluttkontroll viste `transaction_read_only=on`, `transaction_isolation=repeatable read` og samme snapshot. Transaksjonen ble eksplisitt rullet tilbake etter SELECT-lesingen.

Avgrensede ORM-/SELECT-lesinger omfattet valgte legacytenants, profiler bundet til eksakt domain, relevante assignments og inbound/outbound relasjons-/kontakt-/tagkoblinger. Vanlige AccessShare-leselåser ble ikke brukt til å stanse skrivere; ingen eksplisitte tabell-/radlåser, midlertidige DB-tabeller, schema-/datawrites, DB-sekvenskall, tjenestestans eller timerpause. Statement timeout 30 s og lock timeout 2 s var transaksjonslokale. Python ble kjørt direkte med bytecode-skriving av, uten management-startup/migrate/collectstatic.

En foreløpig, tilsvarende read-only-måling 19:57:42 avdekket behov for mer presis telefon-/dekningsrapportering. Alle leverte datatall og kontrollsummer bygger på sluttsnapshotet alene; snapshots er ikke slått sammen. Endelig transaksjonsvindu var omtrent 36 ms; dette er ikke en generell ytelsesgaranti.

Automatisk godkjenningskontroll avviste en tidligere foreslått bred rådataeksport før kjøring. Den utførte metoden beregnet signalene i minnet på staging og eksporterte bare interne ID-er, private hashverdier og aggregater. Ingen rå profil-/kontaktverdier ble eksportert eller vist i terminal. Privat analyse er engangsevidens utenfor repoet; ingen ny applikasjonskode eller permanent CLI.

## Faktisk datatilstand og historisk batch

| ID | Eksakt slug | Navn | Aktører | Personer | NULL-profiler |
| ---: | --- | --- | ---: | ---: | ---: |
| 1 | musikkontoretnord | Musikkontoret Nord | 121 | 147 | 0 |
| 2 | musikkontoretmxst | Musikkontoret MØST | 3 | 4 | 0 |
| 3 | musikkontoretbrak | Musikkontoret Brak | 4 | 6 | 0 |
| 6 | musikkontoretoks | Musikkontoret ØKS | 0 | 0 | 0 |
| 7 | musikkontoretsorf | Musikkontoret SØRF | 0 | 0 | 0 |
| 8 | musikkontoretstar | Musikkontoret STAR | 0 | 0 | 0 |
| 9 | musikkontorettempo | Musikkontoret Tempo | 0 | 0 | 0 |

Totalt **128 Organization, 157 Person, 128 OrganizationTenantAssignment og 157 PersonTenantAssignment**. Hver bundet profil har nøyaktig én assignment til egen legacytenant. **0 nye NULL-bundne aktører og 0 nye NULL-bundne personer**; ingen catch-up utført. Eventuelle framtidige NULL-profiler må fortsatt rapporteres separat og får ingen automatisk domainplassering.

Historisk batch `phase6a2-staging-20261017-01` finnes fortsatt som `COMMITTED_VERIFIED` i samme database; dette er historisk auditstate, ikke en ny apply eller kvittering for inventaret. Eksakte 128/157 historiske profil-PK-er og deres legacytenant fra det private PREPARED-manifestets plan ble sammenholdt med dagens ID-er/bindinger: **0 manglende, 0 nye og 0 endrede legacytenantbindinger**. Alle dagens profiler er bundet til domain 1. Historisk plan og dagens datatilstand er kontrollert separat; ingen påstand om full innholds-/bevaringsfingerprint mot 6A.2-kvitteringen inngår.

## Strukturell integritet

**0 observerte strukturelle avvik** i kontrollert scope:

- 285 profil-/legacytenant-/domainbindinger og 285 assignments: ingen manglende, ekstra, feil-tenant eller feil-domain assignment; ingen inbound assignment fra feil legacytenant.
- 176 OrganizationPerson-rader (174 ACTIVE, 2 INACTIVE): ingen tenantmismatch eller ulike domainbindinger mellom endepunktene. Begge statuser inngår i personnavn+aktør-signalet.
- 223 PersonContact-rader: ingen kontakt-/person-tenantmismatch.
- 60 relevante tags; 73 aktør–tag- og 24 person–tag-koblinger: ingen profil-/tag-tenantmismatch, inklusive inbound scope.

Kontrollene er lesende observasjoner. Image-/import-/PUBLIC-/safety-state ble ikke fullinventert eller endret her; historisk 6A.2-bevaringsevidens beholdes. Det utføres ingen assignmentfjerning eller endring av slettebegrensningen.

## Signaldekning og kandidater

Alle tall i tabellen er **distinkte profiler** per signal. Mangler/ufullstendig og ubrukbart er gjensidig utelukkende på profilnivå; undersøkt = brukbart + de to mangelkategoriene. En profil med minst én brukbar verdi regnes som brukbar selv om et annet felt er tomt/ugyldig. Tomme eller ufullstendige nøkler deltar aldri i kandidatgrupper.

| Modell / signal | Undersøkt | Brukbart | Mangler / ufullstendig | Ubrukbart ikke-tomt | Grupper samme tenant | Grupper cross-tenant | Berørte profiler |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Organization / Org.nr. | 128 | 87 | 40 | 1 | 0 | 0 | 0 |
| Organization / Normalisert aktørnavn | 128 | 128 | 0 | 0 | 0 | 0 | 0 |
| Organization / Aktørnavn + nettstedsdomene | 128 | 104 | 24 | 0 | 0 | 0 | 0 |
| Organization / E-post | 128 | 57 | 71 | 0 | 1 | 0 | 2 |
| Organization / Canonical telefon | 128 | 3 | 125 | 0 | 0 | 0 | 0 |
| Person / E-post | 157 | 154 | 3 | 0 | 5 | 0 | 10 |
| Person / Canonical telefon | 157 | 57 | 100 | 0 | 1 | 0 | 2 |
| Person / Personnavn + aktør-PK | 157 | 156 | 1 | 0 | 0 | 0 | 0 |
| Person / Personnavn + normalisert aktørnavn | 157 | 156 | 1 | 0 | 0 | 0 | 0 |
| Person / Personnavn + sted | 157 | 141 | 16 | 0 | 0 | 0 | 0 |

**Sju signalgrupper / sju unike profilpar**, alle innen samme tenant: ett aktørpar på e-post (to aktører), fem personpar på e-post (ti personer) og ett personpar på canonical telefon (to personer). Unionskontroll på tvers av signaler gir **2 distinkte aktører og 12 distinkte personer**, totalt 14 profiler. Ingen overlapp mellom disse observerte personparene. **0 cross-tenant-grupper og 0 cross-tenant-par** etter undersøkte regler. Gruppeantall for ulike signaler skal ellers ikke summeres som unike identiteter.

Person-e-post kombinerer direktefelt og EMAIL-kontakter: 154 brukbare profiler i hver kilde, 154 i overlapp, 154 i union. **154 gjentatte forekomster på samme profil/signalverdi ble fjernet** før kandidatgruppering. Canonical persontelefon kom fra PHONE-kontakter på 57 distinkte profiler. Flere kontaktfelt/rader på samme profil er ikke i seg selv duplikater.

Kandidater er bare observerte like signaler; felles postkasse eller telefon kan være legitimt. Ingen identitet, winner/loser, canonical ny-ID, transitive grupper, mergeordre eller nye assignments er konstruert. Telefon er aldri selvstendig personidentitet.

## Datadekning og metodebegrensninger

- Org.nr.: eksisterende digits-only-normalisering; bare ni siffer tas med, uten ekstern register-/kontrollsifferverifikasjon. 40 tomme og én ikke-tom ubrukbar verdi.
- Navn: eksisterende trim, whitespace-kollaps og casefold. Ingen fuzzy matching, aksent-/tegnsettingsutjevning eller aliasoppslag.
- Nettsted: eksisterende domenenormalisering, med avvisning av tom/udottet host, credentials og whitespace. Eksakt host, uten DNS, PSL, IDNA- eller redirectekvivalens; 24 mangler komplett navn+domene.
- E-post: eksisterende trim/lower-normalisering og Django-formatvalidering. Ingen alias-/plus-adresse-/provider-/deliverabilityoppslag. Aktør- og personpooler vurderes separat; ingen påstand om cross-type-identitet.
- Canonical telefon: lagrede canonical felter valideres med eksisterende telefonadapter. Råtelefon brukes bare i minnet til datakvalitetsmåling med eksplisitt tenantregion; ingen raw-only backfill. 3 aktører og 57 personer har både råtelefon og brukbar lagret canonical verdi; ingen raw-only-profil uten canonical ble observert.
- **Rå/canonical-avvik:** én Organization og én PersonContact på én Person har råverdi som feiler telefonvalidering (`NOT_POSSIBLE`), mens lagret canonical verdi er gyldig. Ingen retting eller identitetskonklusjon. Dette er signalkvalitetsavvik, separat fra domain-/assignmentintegritet. Direkte- og kontaktkildens råfeltstatistikk kan telle samme persons råverdi flere ganger; profilavvikene er deduplisert. Bruk av canonical alene skjuler ikke denne begrensningen.
- Personnavn+aktør undersøkes både med eksakt aktør-PK og separat normalisert aktørnavn for å fange signaler mellom legacyaktører; navnelikhet etablerer ikke aktøridentitet. Én person mangler brukbar aktørkombinasjon.
- Personnavn+sted bruker hele normaliserte legacyfriteksten; 16 mangler komplett signal. Ingen splitting, geografisk verifikasjon eller implementert Place-identitet.
- Null treff er bare null observerte kandidater etter disse reglene, aldri bevist duplikatfrihet. Fase 5As null cross-tenant-treff er historisk bakgrunn, ikke dagens bevis.

## Privat manifest og etterprøvbarhet

Privat rapportmappe er utenfor repoet, med **0700** på mappen og **0600** på samtlige filer. Manifestet beskriver versjon, snapshot/mode, kode/image/database/domain/tenantscope, metode, dekning, interne profil-/assignment-ID-er, kandidatgrupper, struktur-/signalkvalitetsavvik, private signal-/inputkontrollsummer og gjenstående avklaringer. Det inneholder ingen rå profiler, kontaktverdier eller notater. Hashverdier knyttet til personer holdes private.

Uavhengig lokal rekalkulering fra ID-/hashmanifestet kontrollerte dekningssummer, antall grupper, distinkte berørte profiler/par og eksakte historiske PK-/tenantbindinger. Alle kontroller bestod. Manifestets SHA-256: `7366f2500302fbe634f9adf0c8a69e9fbf9c3227db122d87da28dbd3da375c9f`. Hashen gjelder filintegritet, ikke identitetsavgjørelse eller ny commitkvittering. Private paths og detaljer følger sessionens lokale håndoff og skal ikke inn i Git.

## Skrivebeskyttet review fullført 2026-10-17

Review av sanitert rapport, lokal statusdiff, beregningsmetode og privat evidenspakke fant **ingen kritiske eller viktige funn**. Lokal og fersk GitHub-main `4e7661b1314299aeb0fbbf891de36a7d890b605e`, merget PR #80 og eksisterende main-CI `39062484867` success ble revalidert. Ingen ny CI-kjøring inngikk.

Rekalkulering fra private signalhashverdier bekreftet de sju kandidatgruppene, to distinkte aktører og tolv distinkte personer, uten cross-tenant-par. Dekningssummer, utelatelse av tomme signaler, vern mot dobbelttelling, historiske profil-PK-/legacytenantbindinger og dagens 285 egne assignments stemte. Alle elleve filkontrollsummer, rapportens manifesthash og 0700/0600-rettighetene stemte. Metoden og skillet mellom kandidater, strukturelle avvik og signalkvalitet ble kontrollert; shadowkonklusjonen innfører ikke krav om null kandidater.

**Verifikasjonsbegrensning:** Rånormalisering og detaljkontroller av relasjoner, kontakter og tags kan ikke rekalkuleres fra pakken alene, fordi råverdier og detaljrader er utelatt. Disse kontrollene ble vurdert mot beregningskoden og registrert evidens. Reviewet innebar ingen ny staging-/databasekjøring, datamutasjon, aktivering eller retting. Reviewrapporten anbefalte en avgrenset dokumentasjonsleveranse etter oppdatering av reviewstatus. Denne registreringen inngår i den separate dokumentasjonsleveransen nedenfor. Ingen ny identitetsavgjørelse eller senere shadowbestilling inngår.

## Konklusjon og forutsetninger for senere shadowbestilling

Inventaret er komplett innen verifisert scope og skrivebeskyttet review er fullført uten kritiske eller viktige funn. **Ingen observert strukturell domain-/tenant-/assignmentblocker for et separat bestilt, lesende shadow finnes i dette snapshotet. Null duplikatkandidater er ikke et krav.** De sju kandidatgruppene skal bevares som observasjoner med uavklarte identiteter; shadow må sammenligne eksisterende PK-/resultatsett uten deduplisering, merge eller ombinding.

En senere konkret shadowbestilling må avklare eksakte lesestier/tenantsett, aggregert logging uten PII, forventet likhet og forklarte avvik, default-off aktivering og stopp/tilbakeføring til autoritativ legacylesing. Database-/domainscope og eventuelle nye NULL-profiler må revalideres ferskt; hvis NULL-profiler da finnes, må bestillingen uttrykkelig velge avgrenset eksisterende scope eller separat godkjent catch-up. **Dagens inventar viser ikke catch-up-behov.**

De to rå/canonical-telefonavvikene bør få en egen avgrenset diagnose før matching eller andre brukereiser skal stole på rå/canonical-samsvar. De endrer ikke observerte assignmentsett og er ikke alene en blocker for PK-basert leseshadow. Eventuell senere retting/kode/test er en separat bestilling, ikke utført eller besluttet her. Ingen ny generell gate innføres.

Inventar- og reviewstoppunktet er oppfylt: inventar, privat beskrivende manifest og sanitert evidens er reviewet uten kritiske eller viktige funn. Inventar- og reviewarbeidet omfattet ingen stage, commit, push eller PR; den etterfølgende dokumentasjonsleveransen er separat beskrevet nedenfor. Ingen merge, deploy, backfill/catch-up, backup/restore, shadow/shared-aktivering, nettverksberikelse eller endring av slettebegrensningen inngår.

## Separat dokumentasjonsleveranse 2026-10-17

Prosjekteier har bestilt branch, commit, push og PR for denne saniterte rapporten og prosjektstatus. Leveransen omfatter bare disse to Markdown-filene. Inventartall, privat manifesthash, metodebegrensninger og historisk evidens er bevart. Private detaljfiler og personrelaterte signalhashverdier inngår ikke i Git.

Lokalt inventar-/manifestreview er fullført uten kritiske eller viktige funn; publisert PR krever eget skrivebeskyttet review. Faktisk branch, commit, PR og CI-status følger GitHub og SESSION WRAP-UP. Eventuell CI for dokumentasjonsleveransen er separat fra inventar- og reviewbevisene ovenfor. Ingen ny database-/stagingkjøring, datamutasjon, retting, aktivering, deploy eller merge er bestilt eller utført i denne dokumentasjonsleveransen.
