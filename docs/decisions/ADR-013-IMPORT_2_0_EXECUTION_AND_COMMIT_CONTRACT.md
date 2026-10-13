# ADR-013: Import 2.0 – kilde-, utførelses- og fullføringskontrakt

## Status

Godkjent målarkitektur – ikke implementert.

**Beslutningsdato:** 2026-10-13

**Godkjent av:** Prosjekteier Fredrik Forssman, som del av godkjenningen av hele Fase 5E-planen og de seks hovedvalgene.

**Dokumentasjonsbaseline:** `main` på `18951b010d46eb7beea85e6c96b228e4472893af`.

**Leveransestatus:** dokumentasjonen er lagret på `docs/phase5e-approved-plan` og leveres gjennom [PR #74](https://github.com/fredrik-stack/kreative-norge-crm/pull/74); review er gjennomført uten blokkerende funn og kontrollert merge er bestilt 2026-10-13. Faktisk mergestatus og CI følger GitHub. Eksakt PR-head, PR-lenke og CI følger GitHub og leveranserapporten. Ingen runtimeimplementering inngår.

Den [samlede 5E-planen](../status/PHASE_5E_IMPLEMENTATION_AND_TEST_PLAN_2026-10-13.md) bevarer hele det godkjente faggrunnlaget og er leveranse-/test-/migreringsplanen. Dette ADR-et er normativt for de nye importkontraktene. [UX v6 revisjon 4](../features/IMPORT_2_0_UX_SPEC_V6.md), inkludert O-24, består.

## Kontekst og faktisk utgangspunkt

Dagens tenantbundne legacyimport har ImportJob, parsing, normalisering, matching, AI-forslag, radvis review, commit og logger. XLSX leser første ark, preview regenererer og sletter rader/commitlogger, og nettleseren driver AI-batcher. Det finnes ingen ny vedvarende worker eller KN_IMPORT/1-kontrakt. Kildekontrollen i 5E-planens §2 er kodekontroll, ikke nye nettleserreproduksjoner eller stagingmålinger.

Aktivt telefonfundament og typed bildebeslutninger gir gjenbruk. SharingDomain, assignments, relasjonsspesifikk kontaktpublisering og Places er fortsatt målarkitektur. Den [historiske 5A-kartleggingen 2026-08-30](../status/PHASE_5_SHARING_DOMAIN_IMPACT_2026-08-30.md) fant manglende importfiler; et nytt avgrenset inventar kreves før relevant datamigrering, ikke i denne dokumentasjonsleveransen.

## Forhold til eksisterende ADR-er

- [ADR-004](ADR-004-IMPORT_ARCHITECTURE.md) videreføres: jobb, parsing, normalisering, validering, matching, forslag, review og eksplisitt sporbar commit. ADR-013 presiserer den nye v2-kildeidentiteten, revisjoner, utførelse og fullføringsgrensen; aktiv legacyimport endres ikke av dokumentasjonen.
- [ADR-005](ADR-005-CONTACT_ARCHITECTURE.md) og [ADR-010](ADR-010-INTERNATIONAL_PHONE_IDENTITY_AND_NORMALIZATION.md) videreføres: autoritative PersonContact, additiv overgang, primær forskjellig fra offentlig, E.164 med eksplisitt landkontekst, ingen telefonbasert automerge og ingen normaliseringspublisering. E-postnormalisering er separat additiv leveranse, ikke en påstand om dagens telefonfelt.
- [ADR-011](ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md) beholder canonical ID-er, assignments, private overlays, agreement/capabilities, én PUBLIC-identitet og image-home uten reassosiering.
- [ADR-012](ADR-012-PLACE_IDENTITY_GEOGRAPHIC_CLASSIFICATION_AND_ACTOR_ONLY_MAPS.md) beholder Place, OrganizationPlace, PersonPlace og provider-/kartinvarianter. Den daterte presiseringen av §28 flytter STEDER/import etter verifisert stedskjerne og før de separate koordinat-/provider-/kartleveransene; kontakt-/relasjonsgrunnlaget ligger fortsatt først.
- [ADR-007](ADR-007-IMAGE_ASSET_ARCHITECTURE.md), [ADR-008](ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md) og [ADR-009](ADR-009-PUBLIC_IMAGE_RUNTIME_RELEASE_DELIVERY_AND_RESTORE_SAFE_DENY_STATE.md) beholder bildeapproval, typed selection, immutable artifacts/releases, lokal storage, backup/restore og deny-first safety. Dette ADR-et gir ikke transient providerdata rett til varig lagring eller backup.

Ingen av ADR-005/007–012 erklæres samlet erstattet eller ferdigimplementert.

## Beslutning

### 1. Grunnmur og aktiveringsrekkefølge

Vedtatt rekkefølge er **6A deling/tilgang → 6B kontakter/relasjoner → 6C stedskjerne → 7A–7E Import 2.0**. Privat importlagring og backup/restore kan forberedes parallelt. Den konkrete oppdelingen og stoppunktene finnes i 5E-planens §12.

Eksisterende Organization-/Person-ID-er og råverdier bevares. Legacytenant gir første assignment. Private notater, interne tags og arbeidsinnhold skilles ut før delt lesing. Aktiv bruker, medlemskap, eksakt SharingDomain, gjeldende avtale, capability og objektscope kontrolleres server-side, også ved gamle API-/admin-/importinnganger og bakgrunnsskriving. Global rollefallback fjernes før shared capabilities aktiveres; gamle innganger må bruke de samme tjenestene eller avvises.

Canonical PUBLIC får additiv `canonical_id` og entydig orgnummeralias. Image-home styrer framtidige private writes; historisk asset-, selection-, release-, key- og ledgerstate reassosieres aldri. Ny assignment endrer ikke profil, publikasjon eller bilde som bivirkning.

6B gir autoritative kontaktposter, høyst én primær per person/type også ved samtidighet, rolle/tittel på relasjonen og offentlig kanalvalg per konkret kobling. Person uten kontakt er gyldig. Ny kontakt er privat; blank input bevarer. Offisiell aktøre-post følger aktørens PUBLIC-state uten nytt e-postflagg. Full eksport og fysisk legacyfeltdropp kan komme senere; full ADR-005 forblir uferdig inntil alle dens leveranser er fullført.

6C gir kildebelagte norske/utenlandske Places, kontrollert normal create/reuse uten obligatorisk plattformgodkjenning, rådgivende geografi og tekstlig visning. Ingen personkart, skjult assignment eller publication. Uttrykkelig pre-commit Place-opprettelse er separat fra profilfullføring og slettes ikke automatisk ved avbrutt import.

### 2. KN_IMPORT/1 og kildeidentiteter

Første pakkeversjon er **KN_IMPORT/1**, med versjonsmarkør i arbeidsbokmetadata og nøyaktig fire ark:

| Ark | Vedtatte identitets-/kontaktfelt | Semantikk |
| --- | --- | --- |
| AKTØRER | `actor_source_id`, navn, organisasjonsnummer og relevante profilfelt | Én aktøridentitet i pakken. |
| PERSONER | `person_source_id`; valgfri `contact_source_id`, `contact_type`, `contact_value`, `contact_primary`, `contact_country` | Flere rader per person, én kontakt per rad; person uten kontakt er gyldig. |
| KOBLINGER | `link_source_id`, `actor_source_id`, `person_source_id`, `role`, `title`, `status`, `publish_person`; eventuelt `contact_source_id`, `publish_contact` | Flere rader per relasjon for flere kanalvalg. |
| STEDER | `place_assignment_source_id`, `entity_type`, `entity_source_id`, `original_place_value`, land/region/kommune/locality, stedstype, primær/offentlig valg og proveniens | ADR-012s typed stedskontrakt. |

Kilde-ID-er er lokale i pakken, ikke CRM-ID-er eller skriveautorisasjon. En kontakt-ID tilhører samme person; en koblings-ID peker alltid til samme aktør/person-par. Fem kontakter gir én personkandidat. Motstridende ikke-tomme verdier går til review; siste rad vinner aldri skjult. Blank betyr ikke oppgitt/bevar, mens eksplisitt `false` er et faktisk valg. Referanser valideres og publikasjon går gjennom review og offentlig sluttkontroll.

Standardmal, validering og «Last ned siste KI-prompt» deler versjonert skjema. Egen CSV/XLSX og Checkin-Excel mappes til samme interne struktur. Google Sheets gir senere konto/ark/faner som kildesnapshot, aldri kontinuerlig synkronisering eller tilbakeskriving. Detaljer som ikke er fastsatt her er ikke nye godkjente kolonner eller DDL.

### 3. Versjonerte jobber, kandidater og API-kontrakt

ImportJob videreføres med tydelig arbeidsflytversjon. Nye logiske enheter omfatter kildesnapshot/filmanifest, kilderader, konsoliderte kandidater, versjonert utkast, reviewbeslutninger/problemer og fullføringsplan/kvittering. De er konseptuelle ansvarsgrenser, ikke ferdige modell- eller endepunktnavn.

Manifestet bevarer kilde, checksum, formatversjon, ark/faner og tilgjengelighet. Kandidaten spores tilbake til alle relevante rader/celler. Mapping, Musikkontor, reviewer, telefonland, regler og berikelse er versjonert. Gamle jobber konverteres ikke automatisk til v2.

Egne versjonerte API-innganger skiller utkastlagring, analyseoppstart, kandidatlesing, reviewgodkjenning, offentlig bekreftelse og fullføring. Lagring returnerer uttrykkelig resultat og ny revisjon; API-/nettfeil gir aldri «Lagret». Utdatert grunnlag gir konflikt; gammelt godkjent-flagg overstyrer ikke den. Problem-/handlingskontrakten fastsettes før review-UI slik at dashboard, gule innganger, godkjenning og sluttkontroll bruker samme grunnlag.

### 4. Vedvarende worker, berikelse og bilder

MVP bruker **én workerprosess i eksisterende applikasjonsimage med PostgreSQL som varig arbeidsgrunnlag**. Kort reservasjon i DB etterfølges av eksternt arbeid uten holdte databaselåser. Resultat lagres bare hvis oppgave og kandidatversjon fortsatt er aktuelle. Restart gjenopptar avbrutt arbeid; sene svar overskriver ikke godkjent review. Større køplattform vurderes bare hvis senere målinger viser behov.

Vedtatte startgrenser per aktuell kandidat/analyseversjon er planlagte grenser for implementering og måling, ikke oppnådde resultater, priser eller garantier:

| Profilberikelse | Grense |
| --- | --- |
| Ingen ekstern berikelse | Ingen ekstra BRREG-, profilside- eller modellkall for profilberikelse. |
| Målrettet ekstern berikelse | Ved konkret mangel: inntil 2 BRREG-kall, 2 relevante offisielle nettsider og 1 modellkall for strukturering. |
| Utvidet beriket søk | Samme registergrense; inntil 4 relevante offisielle nettsider og 1 modellkall totalt, med forslag til beskrivelse, sosiale/musikklenker og relevant klassifisering. |

Teknisk startramme: maksimalt **to samtidige eksterne kall, ett per provider**; **tre forsøk inklusive første** ved forbigående feil; **8 000 relevante kildetegn**, **1 200 outputtokens** og **400 tegn** i beskrivelsesforslag. Start-timeout er **5 sekunder HTML**, **10 BRREG/Brave**, **20 modellkall**. Ingen nye modellnavn, retensjonsdager eller produksjonsvolumer vedtas her.

BRREG gir kildebelagt identitetskontekst. Kontaktforslag må knyttes til riktig person/aktør i identifisert kilde. Modellen strukturerer grunnlaget; private notater, interne tags, private kanaler, avtaledata og hele råpakken sendes ikke skjult. Berikelse godkjenner aldri identitet, publisering, tilknytning eller bilde. Første leveranse bruker kjente offisielle kilder og smal BRREG-adapter; manglende grunnlag vises ærlig, uten påstand om fullstendig nettsøk.

Bildekandidatfunn gjelder uavhengig av profilberikelsesnivå. Gyldig låst/godkjent bilde beholdes. Ved mangel brukes tillatt kjent kilde/offisiell nettside/Open Graph, og ved behov høyst **ett automatisk Brave-søk per aktør/analyseversjon**, bare etter eksisterende providergate. Brave er fortsatt dokumentert deaktivert for ordinære sluttbrukere inntil avtalegaten er oppfylt; ingen ny operativ kontroll er utført her. Offisiell kilde, limt URL, upload og fallback kan fungere uten Brave.

Arbeidssettet med treff er begrenset; bare valgt bilde fullprosesseres. Reviewer godkjenner bilde/utsnitt; manglende bilde blokkerer ikke gyldig profil. Nye aktørers bildeforberedelse bindes til jobb, kandidat, versjon, aktørgrunnlag, reviewer og faktisk/planlagt image-home uten midlertidig CRM-aktør.

Godkjent ferdig bildegrunnlag, utsnitt og approval lagres varig. Previewrefs kan fornyes uten tapt lagret valg. Uvalgte providerresultater transporteres gjennom et lite delt minneområde **uten backup**, med absolutt utløp på **høyst 30 minutter**; de kopieres aldri inn i varig kilde-/review-/jobbhistorikk. Cachetap krever oppfrisking av uvalgte treff, ikke ny godkjenning av bevart bildevalg. ADR-007s transient-/proveniensregler består.

### 5. Fast fullføringsplan, atomisk databasecommit og etterleveranser

Én uttrykkelig godkjent fullføringsplan behandles i **én samlet databasetransaksjon**. Uavklarte kandidater og deres avhengigheter må avklares eller uttrykkelig utelates før planen fryses.

1. Serveren beregner separate handlinger for profil, private arbeidsdata, kontakt, relasjon, assignment, sted, publication og bildevalg.
2. Hele den offentlige forskjellen beregnes fra samme PUBLIC-regler, også synlige endringer på allerede publiserte profiler og avledede visninger utenfor importens egne koblingsrader.
3. Offentlig bekreftelse bindes til planversjon; relevant endring opphever den.
4. Jobb og berørte objekter låses i stabil rekkefølge. Rettigheter, avtale, scope, revisjoner, avhengigheter og plan revalideres.
5. Handlinger, audit og varig kvittering lagres samlet. Feil før databasecommit ruller tilbake databaseendringene.
6. Gjentakelse returnerer samme kvittering. Tapt HTTP-svar eller samtidige forsøk gir ikke nye profiler/kontakter/relasjoner/assignments; samme nøkkel med annet innhold avvises.

Musikkontor velges én gang for jobben; ingen ekstra radbekreftelse. Assignment er likevel separat autorisert, typed og auditert handling, uten generell profiloppdatering som bivirkning. Rolle/status avgjøres individuelt i review, ikke masseregler.

Fullføring gjør ingen providersøk, nedlasting eller bildeprocessing. Forberedte bilder bruker eksisterende selection-/auditkommandoer, med lokal safety-/deny-kontroll. Databaseatomisitet lover aldri atomisk rollback av filer eller ekstern sikkerhetsledger. Rapporter og eventuell offentlig bildelevereanse får varige etterarbeidsoppgaver og separat resultatstatus. Feil etter vellykket DB-commit vises som faktisk lagret data med gjenstående etterleveranse; retry gjør ingen ny profilimport.

### 6. UX-, test-, migrerings- og aktiveringskontrakt

UX-01–UX-14 og videreførte O-korreksjoner består. O-20–O-24 bevises i tekniske tester: serverberegnet føranalyseutvalg omfatter alle treff, står fast under redigering og utvides ikke ved null treff. Alle fire regelgrupper er tilgjengelige under hvert av de tre filtrene for aktør/person. Null effekt vises ærlig; stedsregler endrer bare valgte profilers stedopplysninger, ikke felles stedskandidat eller andre profiler. Underkategoriens hovedkategoriavhengighet består; ingen universelle kontakt-/sted-/kategorikrav legges til.

Køen bruker korte sammendrag, serverfiltrering og puljer på **50**, med én aktiv detaljflate og intern rulling. Klikk, knapper og Option/Alt følger samme søk/filter; sorteringsanker bevarer neste nabo. Siste feltavklaring lar kandidaten stå åpen til uttrykkelig handling. Strukturert problemliste driver antall og riktig gul seksjonsknapp; åpning/fokus godkjenner ingenting. Avhengighetshopp har synlig retur og bevart køkontekst.

Sluttkontroll henter hele listen av kompakte offentlige aktørendringer/personvisninger fra start. Før/etter-detaljer kan åpnes per oppføring. Samme person hos to aktører kan gi to visninger. Tre tekstlinjer per lukket rad og bekreftelse av hele planen består, uten avkutting eller Vis alle-gate.

Før relevant datamigrering kreves nytt avgrenset staginginventar, førverdier, additive ID-/raw-bevarende endringer, idempotent backfill og sammenligning mellom gammel/ny lesing. Legacytags/private data avgjøres før relevant delt lesing/PUBLIC i 6A; global tittel/kontaktpublisering før kontakt-/PUBLIC-omlegging i 6B; retensjon og ferdige utilknyttede bilder før første reelle v2-lagring. Ingen av disse databeslutningene er utført ved plangodkjenningen.

Privat persistent importfilområde bruker manifest med checksum, størrelse, versjon og tilgjengelighet; ferdig fil publiseres internt før DB markerer klar. Backup/isolert restore verifiserer jobb → kilde → kandidater → beslutninger → kvittering → rapporter/filer. Sletting samordnes med backup; retensjon omfatter aktiv storage, DB-rådata og gjenoppretting. Nye lagringsområder gjenskaper ikke historisk manglende filer.

Avtale-/personvern-/tilgangskrav gjelder før delte persondata i produksjon; storage/retensjon/restore før første reelle v2-opplasting; providerkrav før aktuell aktivering. Browser-aktiv Codex er hard gate før første senere UI-implementering, også Editor-grunnmur. Syntetisk utvikling/testing kan komme før konkrete produksjonsdata-/avtaleleveranser er ferdige. Automatisk staging-deploy er et separat infrastrukturløp.

## Alternativer og begrunnelse

- **Nettleserdrevet analyse:** videreføring av legacybatches oppfyller ikke gjenopptakelse ved lukket nettleser. PostgreSQL-forankret worker er et lite MVP-valg uten ny generell køplattform; større løsning avhenger av målt behov.
- **Fullføring per rad:** gir delvise profiler og vanskeligere forståelse av godkjent utvalg/offentlig forskjell. Fast plan med én DB-transaksjon og kvittering gir samlet datakonsistens; filer/ledger behandles med egne eksisterende sikkerhetsgrenser.
- **Destruktiv preview/generell CRUD:** ville svekke kilde-/reviewspor og assignment som egen handling. Versjonerte kandidater og domenehandlinger bevarer stale-kontroll og idempotens.
- **Kart før kjerneimport:** den gamle §28-rekkefølgen i ADR-012 beholdes som historisk spor, men den godkjente presiseringen lar tekstlig stedskjerne/STEDER leveres først. Kartets krav og tester slettes ikke.

## Konsekvenser og avhengigheter

V2 krever additiv modell-/API-/storagegrunnmur, reell serverpersistens, vedvarende bakgrunnsarbeid og samlet handlingsplan. Dette har implementeringskostnad, men er nødvendig for gjenåpning, flerkontakt, sikker delt identitet og etterprøvbart offentlig resultat. Samlet transaksjonsstørrelse må måles; ingen produksjonskapasitetsgaranti er vedtatt.

CSV/XLSX-kjerne først, Google Sheets etter kjernen før v1-lukking. Checkin gjennom Excel-mapping i v1. Direkte Checkin-API, Mailmojo-eksport, kart og XML-konvertering er utenfor kritisk sti; gammel XML konverteres i separat engangsverktøy utenfor CRM.

## Implementeringsleveranser og akseptansekriterier

[5E-plan §12](../status/PHASE_5E_IMPLEMENTATION_AND_TEST_PLAN_2026-10-13.md#12-etappevis-leveranseplan) beskriver 6A, 6B, 6C, parallell storage og 7A–7E med brukerreise/garanti, inngangsporter, liten sammenhengende PR-oppdeling, berørte kodeområder, tester, data-/rollbackgrenser og stoppunkt.

Importetappene er 7A kilde/mapping/jobbregler, 7B analyse/berikelse/bilder, 7C gjennomgang, 7D sluttkontroll/fullføring og 7E Google Sheets/v1-lukking. De følger verifisert 6A deling/tilgang, 6B kontakter/relasjoner og 6C stedskjerne; privat storage har sin parallelle, men bindende før-reell-lagring-port.

Kode levert, funksjon aktivert og stagingverifisert er ulike statuser. Ingen ny etappe er levert, aktivert eller testet av denne dokumentasjonen. Ingen framtidige PR-/migrasjonsnumre eller datoer reserveres.

## Testkrav

Planens §10 gir den samlede matrisen: domain-/membership-/agreement-/capability-negativtester, private data i API/matching/eksport/PUBLIC, ID-/image-home-bevaring, CASCADE og backfill, flerkontakt/samtidig primær/relasjonsspesifikk offentlig projeksjon, fire ark/referanser/blank-false, O-24 på tvers av sider, workerrestart/sene svar/forsøk/providerpayload, bilder med null CRM-aktører, lagringsfeil/to faner/kø/fokus, full offentlig plan og atomisk/idempotent fullføring, filfeil/backup/sletting/restore og ADR-012s sted/geografiske regelutfall.

Eksisterende Django/API, Vitest og Playwright videreføres; minst én sammenhengende importreise mot ekte backend kreves. Mocktester alene beviser ikke lagring. Telefon-/bilde-/PUBLIC-/tenant-/safety-regresjoner består. Teknisk UI-verifikasjon dekker **1366 × 768**, **1440 × 900**, lange navn/kilder og representative **100 og 500 kandidater** i navngitt miljø. API-tid, datamengde, kørespons og fullføring måles før produksjonsgrense fastsettes.

Ingen ny formell brukertest, manuell prototyperunde eller obligatorisk kollegatest. Senere teknisk staging- og relevant eiergodkjenning består. Historisk **45/45** og separat **8/8** er prototypeartefaktevidens, ikke summert runtime-testkjøring. Alle nye testkrav er planlagt, ikke bestått.

## Rollback

Før nye semantiske writes kan additive endringer reverseres når dette er testet. Etter delt skriving eller v2-fullføring stoppes relevante skrivetjenester og bakgrunnsoppgaver; data, filer, audit og kvitteringer bevares og feil rettes fremover. Legacylesing brukes bare der den kan representere ny data sikkert.

Ingen automatisk retur til ett-tenant-eierskap etter multiassignment, global kontaktpublisering etter relasjonsvalg eller gammelt image-home etter transfer. «Avbryt import» sletter ikke fullførte profilendringer eller uttrykkelig opprettede Places. Denied image state og ledgerens forward-only-vern består over DB-/mediarestore. Retensjon og restore er egne avklarte operasjonelle porter, ikke en falsk totalrollbackgaranti.

## Åpne operative porter

Legacytag-/privatdatapolicy, tittel-/kontaktpubliseringsmapping og retensjon har sine navngitte senere dataporter. Gjeldende avtale, personvern, providerrettigheter, produksjonsmålinger og staging-/restorebevis må oppfylles ved relevant aktivering. Godkjent målretning er ikke bevis på at disse er gjennomført.
