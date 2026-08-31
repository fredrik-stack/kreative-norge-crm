# ADR-011: Sharing domain, canonical identity og tenantassignments

## Status

Godkjent målarkitektur – ikke implementert

**Beslutningsdato:** 2026-08-31

ADR-et formaliserer den godkjente retningen fra fase 5A. Denne leveransen endrer
bare dokumentasjon. Den innfører ingen modeller, migrasjoner, API-er,
featureflagg, frontend, dataendringer eller stagingaktivering.

## Relasjon til tidligere og senere ADR-er

ADR-011 presiserer eller viderefører følgende beslutninger:

- [ADR-001](ADR-001-TENANT_ARCHITECTURE.md): tenant forblir arbeids-, medlemskaps-
  og privat sikkerhetsscope, men er ikke lenger framtidig canonical eier av
  Organization og Person. SharingDomain blir en ny eksplisitt grense over
  samarbeidende tenants; dette opphever aldri tenantisolasjon for overlays.
- [ADR-003](ADR-003-PUBLICATION_MODEL.md): intern og offentlig tilstand skal
  fortsatt skilles. Én canonical Organization får én global publication state
  og én offentlig identitet, uavhengig av antall assignments.
- [ADR-004](ADR-004-IMPORT_ARCHITECTURE.md): preview, review, eksplisitte
  beslutninger og sporbar commit består. ADR-011 legger til separate typed
  beslutninger for canonical core, overlay, relation, assignment og publication.
- [ADR-005](ADR-005-CONTACT_ARCHITECTURE.md): PersonContact skal senere følge
  canonical Person og SharingDomain, mens person- og kontaktpublisering fortsatt
  er relasjonsspesifikk. ADR-011 implementerer ikke resten av ADR-005.
- [ADR-007](ADR-007-IMAGE_ASSET_ARCHITECTURE.md): historisk tenant-scope,
  immutable selections/revisjoner og privat original beholdes. ADR-011 legger
  bare til image-home-assignment som bro til canonical Organization.
- [ADR-009](ADR-009-PUBLIC_IMAGE_RUNTIME_RELEASE_DELIVERY_AND_RESTORE_SAFE_DENY_STATE.md):
  release-identitet, ledger, deny, takedown, restore og serving-invariantene
  består. Historisk image state skal aldri reassosieres ved canonicalisering.
- [ADR-010](ADR-010-INTERNATIONAL_PHONE_IDENTITY_AND_NORMALIZATION.md): E.164 er
  et sterkt matchsignal, ikke personidentitet, og samme telefon kan tilhøre flere
  personer. Normalisering endrer aldri publication.

[ADR-012](ADR-012-PLACE_IDENTITY_GEOGRAPHIC_CLASSIFICATION_AND_ACTOR_ONLY_MAPS.md)
er senere godkjent som separat målarkitektur for provider-nøytral Place,
OrganizationPlace, PersonPlace, geografiske tenantregler, providerreferanser,
koordinater og actor-only kart. Den er ikke runtimeimplementert og endrer ikke
ADR-011s identity-, assignment- eller autorisasjonsbeslutninger. Senere
henvisninger i ADR-011 om at ADR-012 «skal beslutte» eller «må godkjennes»
beskriver denne beslutningens opprinnelige avhengighet; dokumentasjonsporten er
nå oppfylt av ADR-012, mens alle implementeringsporter fortsatt er åpne.

## Bakgrunn

Dagens implementasjon eier `Organization`, `Person`, `OrganizationPerson`,
`PersonContact`, `Tag`, importjobber og bildeobjekter direkte gjennom én tenant.
Det er riktig beskrivelse av aktiv kode og migrasjoner. Den modellen gjør samme
reelle aktør eller person til separate mulige objekter når flere av de sju
Musikkontorene skal arbeide med dem.

Fase 5A gjennomførte en skrivebeskyttet konsekvenskartlegging mot kode,
migrasjoner og staging. Kartleggingen fant at eksisterende Organization- og
Person-PK-er kan beholdes og at direkte canonicalisering er mulig uten en ny
permanent hubmodell. Den fant ingen observerte cross-tenant-dublettgrupper i
det undersøkte datagrunnlaget. Dette er et godt migreringsutgangspunkt, men
ikke et generelt bevis på at framtidige data er duplikatfrie.

Kartleggingen fant samtidig at en enkel ForeignKey-omlegging ville bryte viktige
grenser: private tenantdata må skilles fra delt core, tilgang krever mer enn en
global rolle, og historisk bilde-, release-, ledger-, takedown- og restorestate
kan ikke flyttes til en annen tenant. Importfilene er heller ikke persistente i
dagens stagingmiljø, og full Import 2.0 kan derfor ikke aktiveres på dagens
storagekontrakt.

Den korte, PII-frie kartleggingsevidensen ligger i
[Phase 5 sharing-domain impact](../status/PHASE_5_SHARING_DOMAIN_IMPACT_2026-08-30.md).

## Problem

Systemet trenger én stabil identitet for samme Organization eller Person i det
avtalte Musikkontoret-samarbeidet, samtidig som det må:

- bevare tenant som sikkerhetsgrense for medlemskap og privat arbeidsdata
- unngå kopier som driver fra hverandre
- hindre at «shared» betyr globalt på hele plattformen
- gjøre alle delte writes og offentlige konsekvenser eksplisitte
- bevare privatliv, avtalegrunnlag, audit og stale-kontroll
- migrere additivt uten å omskrive historisk image state
- gi trygg rollback også etter at nye lesestier er aktivert

Uten en formell beslutning kan import, PUBLIC, roller, tags, kontakter, bilder og
senere stedsdata utvikle ulike og uforenlige eierskapsregler.

## Scope

ADR-011 eier målkontrakten for:

- SharingDomain og binding mellom tenant og domain
- canonical Organization og Person
- OrganizationTenantAssignment og PersonTenantAssignment som konsepter
- shared canonical core og tenantprivate overlays
- shared editorial tags og private internal tags
- capabilities, server-side autorisasjon og versjonert delingsavtale
- én canonical PUBLIC-identitet og én publication authority
- image-home-overgangen uten reassosiering
- grensen mot contacts, relations, import og senere structured places
- additiv migrering, shadow gates, testkrav, staginggater og rollback

## Ikke-mål

Denne beslutningen:

- implementerer ikke kode, schema, migrasjoner, data, API, frontend eller drift
- oppretter ikke ADR-012 og beslutter ikke Place-felter, koordinatprovider eller
  Google Maps-integrasjon
- gir ikke personer kartmarkører, kartendepunkter eller PUBLIC-kartprojeksjon
- implementerer ikke full ADR-005 eller et nytt personkontakt-API
- implementerer ikke firearksformatet `AKTØRER` / `PERSONER` / `KOBLINGER` /
  `STEDER`; dette tilhører senere Import 2.0
- løser ikke persistent import storage, backup, retensjon eller
  database–fil-konsistens
- gjør ikke private image assets delte og flytter ikke historisk image state
- innfører ikke automatisk canonical merge, automatisk assignment eller
  automatisk publication
- innfører ikke en permanent canonical hubmodell eller en parallell
  sannhetsmodell for aliaser
- utformer ikke endelig avtaletekst, personvernerklæring, behandlingsgrunnlag,
  interne ansvars-/arbeidsrutiner eller juridisk produksjonskontroll;
  behandlingsansvarlig er besluttet som MUSIKKONTORET AS

## Begreper

**SharingDomain** er en eksplisitt samarbeids- og sikkerhetsgrense som inneholder
et avgrenset sett tenants. Domain-wide tilgang krever eksakt domain-likhet.

**Canonical objekt** er den ene autoritative Organization- eller Person-raden
innen ett SharingDomain. Eksisterende PK beholdes i den valgte strategien.

**Tenantassignment** er en eksplisitt relasjon mellom et canonical objekt og en
tenant som arbeider med objektet. En assignment er ikke en kopi eller et
eierskap til canonical core.

**Canonical core** er delte, autoritative aktør-/personfelt som beskriver det
samme objektet på tvers av assignments.

**Tenantprivate overlay** er arbeidsdata som bare tilhører én tenant og aldri
skal serialiseres til andre tenants eller PUBLIC.

**Shared editorial tag** beskriver canonical objekt og kan deles innen eksakt
SharingDomain. **Internal tag** beskriver tenantlokal workflow eller vurdering
og ligger i privat overlay.

**Image-home-assignment** er den ene aktive assignmenten som autoriserer
framtidige private image writes for en canonical Organization. Hver canonical
Organization skal til enhver tid ha nøyaktig én slik assignment, og den må
peke til samme Organization og samme SharingDomain. Begrepet etablerer ikke et
separat eller shared assetdomene.

**Gjeldende acceptance** er en ikke-tilbakekalt aksept av den agreementversjonen
som gjelder for domain på handlingstidspunktet.

## Beslutning

### 1. Direkte canonicalisering med additiv overgang

Eksisterende Organization- og Person-rader blir canonical objekter. Eksisterende
primærnøkler beholdes. Det innføres ingen permanent hubmodell mellom dagens rad
og canonical identitet.

`SharingDomain`, nullable domain-binding på canonical objekter og separate
tenantassignment-tabeller legges til additivt i senere implementeringsleveranser.
Dagens direkte `tenant`-felter beholdes midlertidig som legacy/home-scope. Hvert
eksisterende objekt backfilles med én assignment fra legacytenanten før nye
lesestier kan aktiveres.

Et eventuelt framtidig loser-objekt etter kontrollert duplikatsammenslåing kan
få alias eller tombstone til winner-identiteten. Aliaset er kun redirect,
proveniens og idempotens; det blir aldri en skrivbar parallell sannhetsmodell.

### 2. Ett eksplisitt Musikkontoret-domain

Første SharingDomain heter `Musikkontoret` og omfatter eksakt:

- Musikkontoret Nord
- Musikkontoret Tempo
- Musikkontoret Brak
- Musikkontoret STAR
- Musikkontoret SØRF
- Musikkontoret ØKS
- Musikkontoret MØST

Alle domain-wide queries, matchere, assignments og capabilities skal kreve
eksakt SharingDomain-likhet. Datamodellen skal kunne støtte andre fullstendig
isolerte domains senere. Ingen default eller global fallback kan tolke «shared»
som alle tenants på plattformen.

### 3. Canonical Organization og Person

Organization og Person er canonical innen nøyaktig ett SharingDomain når
sharing er aktivert. Ett canonical objekt kan ha én eller flere assignments.
Geografi kan senere foreslå assignments, men er aldri eksklusivt eierskap eller
automatisk autorisasjon.

Canonical core har ingen redaksjonell home tenant. En assigned tenant får ikke
sin egen kopi av canonical felt. Endring av core gjelder alle assignments.

### 4. Assignments

En aktiv bruker kan legge et eksisterende canonical objekt til sin egen aktive
tenant når alle følgende vilkår er oppfylt:

- brukeren er aktiv
- brukeren har aktiv TenantMembership i måltenanten
- måltenanten tilhører samme eksakte SharingDomain som objektet
- brukeren har gjeldende agreement acceptance
- brukeren har relevant create/edit/import-capability og den konseptuelle
  capabilityen `ADD_EXISTING_SHARED_ENTITY_TO_OWN_TENANT`
- serveren har returnert en privacy-minimert matchprojeksjon og brukeren har
  bekreftet den typed assignmentbeslutningen

Brukeren kan ikke tildele objektet til en vilkårlig annen tenant. Plattform-
superadmin kan opprette et nytt objekt med flere assignments. Tenant-`SUPERADMIN`,
`GRUPPEADMIN` og `REDIGERER` kan opprette et nytt objekt bare i egen aktive
tenant. Tenant-`SUPERADMIN` er ikke plattform-superadmin.

Assignment må være eksplisitt, auditerbar og idempotent. Den kan aldri oppstå
som skjult bivirkning av matching, core-edit, import eller publication.

Tenant deletion eller `CASCADE` skal aldri slette et canonical objekt som har en
annen aktiv assignment. Før assignment write eller multiassignment aktiveres,
må dagens direkte cascade-semantikk erstattes eller omgis av eksplisitt
beskyttet deletion-workflow, constraints og negative tester. Fjerning av siste
assignment og sletting av canonical objekt er en separat, autorisert beslutning.

### 5. Canonical core og writes

Aktive brukere med gjeldende acceptance og edit-capability i minst én assigned
tenant kan redigere canonical core. Første rollemapping er:

| Rolle | Redigere shared core |
| --- | --- |
| Plattform-superadmin | Ja, med samme agreementkrav som andre mennesker |
| Tenant-superadmin | Ja, i assigned tenant |
| Gruppeadmin | Ja, i assigned tenant |
| Redigerer | Ja, i assigned tenant |
| Leser | Nei |

Alle core-writes skal:

- være server-side autorisert per handling, objekt, domain og assignment
- forklare i UI/API at endringen gjelder det felles canonical objektet
- lagre actor, tidspunkt, assignment-/tenantkontekst og revisjon i audit
- kreve expected revision eller tilsvarende stale-kontroll
- avvise eller sende til eksplisitt review når importert ikke-tom verdi avviker
  fra eksisterende ikke-tom canonical verdi
- aldri lese eller skrive andre tenanters private overlays

Capabilities for vanlig shared-core-edit, endring av felt på en allerede
publisert aktør og publish/unpublish skal være separate selv om første
rollemapping er lik.

### 6. Tenantprivate overlays

Minst følgende data skal ligge i assignment-scopet eller i en entydig
canonical-object-plus-tenant-overlay:

- interne notater
- interne tags
- arbeidsstatus
- lokal oppfølging
- tenantspesifikke vurderinger
- lokale kontakt- og samtykkenotater

Overlays skal alltid ha eksakt tenant- og canonical-scope. Vanlige Editor-,
importmatch- og PUBLIC-serializers skal ikke kunne serialisere et annet
tenant-scope. Domain-wide matching kan bare bruke en egen privacy-minimert
projeksjon uten private notater, private tags, arbeidsstatus eller unødvendige
personopplysninger.

### 7. Shared editorial tags og private internal tags

Category og Subcategory forblir global/shared taxonomy. Innen ett SharingDomain
skal det finnes shared editorial tags som beskriver den canonical aktøren eller
personen, og tenantprivate internal tags som beskriver workflow, administrasjon
eller lokale vurderinger.

PUBLIC kan bare bruke eksplisitte shared editorial tags. Dagens tenantbundne
`Tag`-rader er legacydata og skal ikke automatisk klassifiseres som shared/public
eller internal/private. Migreringen krever eksplisitt mapping, policy eller
redaksjonell kontroll. Workflow- og admin-tags er alltid private.

### 8. Versjonert sharing agreement

Målmodellen har konseptene `SharingAgreement` og
`SharingAgreementAcceptance`:

- Agreement tilhører nøyaktig ett SharingDomain og har immutable versjoner.
- Acceptance binder bruker, domain, agreementversjon, tidspunkt og status.
- Acceptancehistorikk er immutable; tilbakekalling registreres uten sletting.
- Alle menneskelige brukere, også plattform-superadmin, må ha gjeldende
  acceptance for domain-wide shared read, matching eller assignment.
- Aktiv TenantMembership og capability kreves i tillegg til acceptance.
- En vesentlig avtaleendring gir ny versjon og krever ny aksept.
- En ny versjon kan ha framtidig `effective_at`. Fra effective-at finnes ingen
  skjult grace for shared funksjoner.
- Manglende, utgått eller tilbakekalt acceptance feiler lukket.

MUSIKKONTORET AS er juridisk behandlingsansvarlig for CRM-behandlingen og det
felles SharingDomainet. Dette er en godkjent beslutning, ikke en åpen ekstern
gate. Fredrik Forssman er produkteier, faglig ansvarlig og operativ
kontaktperson, ikke juridisk behandlingsansvarlig.

Før delte persondata kan aktiveres i produksjon, består den eksterne
juridiske/personvernmessige gaten av:

- endelig ordlyd og versjonering av avtalen for tilgang til delte CRM-data
- nødvendige oppdateringer i personvernerklæringen
- dokumentasjon av behandlingsgrunnlag, formål, rettigheter og interne
  ansvars-/arbeidsrutiner
- juridisk kontroll før delte persondata aktiveres i produksjon

### 9. Permissions og capabilities

Hver shared handling skal kontrollere server-side:

1. `user.is_active`
2. aktiv TenantMembership
3. eksakt SharingDomain-likhet
4. gjeldende agreement acceptance
5. eksplisitt capability for handlingen
6. objekt-, assignment- og eventuelt image-home-scope

Frontend-skjuling er aldri en sikkerhetsgrense. Dagens globale Django-
gruppefallback skal fjernes eller begrenses før shared capabilities aktiveres,
slik at et globalt gruppenavn aldri automatisk gir en rolle i en vilkårlig
tenant.

Konseptuelle capabilitygrenser omfatter minst:

- lese privacy-minimert shared match
- legge eksisterende canonical objekt til egen aktive tenant
- redigere shared core
- redigere public-relevante felt på publisert aktør
- publish/unpublish canonical aktør
- lese/skrive eget privat overlay
- utføre private image writes i image-home-scope
- overføre image home gjennom en separat capability

Endelige navn kan tilpasses repoets capabilitystandard uten å svekke denne
semantikken.

### 10. Én PUBLIC-identitet og publication authority

Én canonical Organization har én offentlig identitet, én PUBLIC-side og én
global publication state. Den bevarte canonical Organization-PK-en er primær
offentlig identitet i den direkte canonicaliseringsstrategien. Et eksplisitt
`canonical_id`-felt skal legges additivt til i public API som kontraktsnavn før
cutover, peke på samme bevarte identitet og ikke skape en ny hub.

Organisasjonsnummer er et søke- og aliasfelt, ikke primær identitet.
Org.nr.-route kan bare svare når treffet er entydig. Organization uten org.nr.
bruker canonical ID. Public projection skal returnere én Organization én gang
uavhengig av antall assignments og skal ikke automatisk eksponere interne
assignments.

Publication state og publish/unpublish krever en separat capability. Første
rollemapping tillater plattform-superadmin, tenant-superadmin, gruppeadmin og
redigerer å publisere når øvrige porter er oppfylt; leser kan ikke publisere.
UI/API skal gjøre den globale effekten tydelig. Import får en samlet PUBLIC-
sluttkontroll før commit og kan aldri publisere som skjult bivirkning.

`Organization.email` er offisiell, delt aktøre-post. Personlig e-post skal ikke
lagres der. Når canonical aktør er PUBLIC, inngår Organization.email i den
offentlige projeksjonen uten et nytt `publish_email`-flagg. Endring av feltet på
en publisert aktør skal presenteres og auditeres som en PUBLIC-endring. Telefon
beholder eget eksplisitt publish-valg. Personkontakt følger senere ADR-005s
relasjonsspesifikke kontrakt.

PUBLIC bruker bare shared editorial tags og aldri private overlays. Structured
places og actor-only Google Maps følger den senere godkjente ADR-012, men er
ikke implementert. Personer får aldri egne PUBLIC-kartpunkter.

### 11. Image-home uten reassosiering

Hver canonical Organization skal til enhver tid ha nøyaktig én aktiv,
eksplisitt image-home-assignment. Image home må være en aktiv assignment til
samme Organization og samme SharingDomain. Private image writes skal feile
lukket dersom en gyldig image home mangler.

Image home etableres slik:

- Ved backfill blir assignmenten fra legacytenanten image home.
- Ved opprettelse av en ny Organization med én assignment blir denne
  assignmenten automatisk image home.
- Når plattform-superadmin oppretter en ny Organization med flere assignments,
  skal image home velges eksplisitt som del av samme typed og atomiske
  opprettelsesbeslutning. Den operative/aktive opprettelsestenanten kan være
  forhåndsvalgt i UI, men serveren skal kreve et eksplisitt og gyldig
  image-home-valg ved multiassignment.
- Opprettelse av en senere assignment endrer aldri image home automatisk.

Følgende beholder alltid historisk tenant-scope og immutable identitet:

- ImageAsset og privat original
- ImageRenditionSet og ImageRendition
- OrganizationImageSelection og review events
- OrganizationImageRelease og konkrete release-renditions
- ledger, public keys, deny/takedown og snapshots

En ny assignment oppretter ingen nye imageobjekter. Alle assigned tenants kan se
canonical aktørens godkjente PUBLIC-image projection. Bare plattform-superadmin
eller brukere med eksisterende image-write-capability i image-home-tenanten kan
utføre private image writes. Andre tenants får ikke private originaler,
approvalhistorikk, proveniens eller private credentials.

Image-home-assignment kan ikke fjernes eller deaktiveres slik at Organization
står uten nøyaktig én gyldig image home. Overføring av image home er en separat,
atomisk, capabilitykontrollert og auditert handling. En transfer endrer bare
framtidig private-write-scope og skal aldri reassosiere eller omskrive
historiske assets, originals, rendition sets, renditions, selections, review
events, releases, public keys, ledgerstate, deny/takedown eller snapshots.
Fullt shared asset-scope er eksplisitt utsatt.

### 12. Personer, OrganizationPerson og PersonContact

Person kan deles canonically mellom tenants. OrganizationPerson skal langsiktig
være én canonical relasjon per Organization, Person og SharingDomain. Rolle og
tittel hos en aktør tilhører denne relasjonen. Tenantlokal arbeidsstatus rundt
relasjonen ligger i overlay/workstate og skal ikke duplisere relasjonen.

PersonContact skal senere følge canonical Person og SharingDomain i samspill
med ADR-005. ADR-010s E.164-kontrakt består. Telefon er kun et sterkt
matchsignal; samme canonical telefon kan legitimt brukes av flere personer og
skal aldri være global unik personidentitet eller automatisk mergegrunnlag.
Publication av person og kontakt er relasjonsspesifikk etter ADR-005.

### 13. Grense mot ADR-012 og personsteder

Personer skal senere kunne ha strukturerte steder gjennom en enkel PersonPlace-
relasjon mot provider-nøytral Place. Flere norske og utenlandske steder skal
kunne brukes til profil, matching og tenantforslag. Personer skal ikke ha
koordinater som krav, sendes til Google for kartformål eller få kartmarkører,
kartendepunkter eller PUBLIC-kartprojeksjon.

ADR-012 beslutter felt, relasjoner, providerreferanser, geografiske
tenantregler, koordinater og actor-only kart. Dokumentasjonsporten er oppfylt;
ingen structured place- eller kartimplementasjon kan starte før den relevante
implementeringsporten er godkjent.

### 14. Importgrense

ADR-011 beslutter bare identity- og assignmentkontrakten som senere Import 2.0
skal bruke:

- ImportJob har fortsatt én operativ tenant og én reviewer.
- Matching kan søke i hele eksakt SharingDomain gjennom privacy-minimert
  projection når agreement, membership og capability er gyldige.
- Assignment er en eksplisitt typed beslutning.
- Canonical core, privat overlay, relation, assignment og publication er
  separate beslutningstyper.
- Ingen assignment eller publication oppstår som skjult bivirkning.
- Commit krever revision-/stale-kontroll og eksplisitt konfliktreview.
- ImportImageDecision forblir tenant- og image-home-sikker.
- Import-commit gjør ingen søk, fetch, bildeprocessing eller automatisk
  publisering.

Firearksformatet `AKTØRER` / `PERSONER` / `KOBLINGER` / `STEDER` tilhører fase
7 og implementeres ikke her.

### 15. Persistent import storage er hard framtidig gate

Før Import 2.0 kan aktiveres, må en separat beslutning og implementering dekke:

- original import package
- preview-, error- og commitrapporter
- proveniens
- persistent storage
- backup og restore
- retensjon
- database–fil-konsistens

Denne gaten er ikke løst av ADR-011. Den skal senere avklares mot
[ADR-008](ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md) og faktisk
stagingdrift. Fase 5A fant 53 ImportJob-filreferanser, men ingen tilgjengelige
kildefiler i default storage, og én feilrapportreferanse uten tilgjengelig fil.

## Arkitekturinvarianter

Følgende må være sanne i alle implementeringsetapper:

1. Canonical Organization eller Person tilhører maksimalt ett SharingDomain.
2. Shared tilgang krysser aldri SharingDomain-grensen.
3. Assignment er relasjon, ikke kopi eller tenant-eierskap til core.
4. Canonical core har ingen redaksjonell home tenant.
5. Private overlays er alltid tenant-scopede og eksponeres aldri cross-tenant.
6. Alle shared writes har aktiv bruker, membership, acceptance, capability,
   assignment-scope, audit og stale-kontroll.
7. Global Django-gruppe alene gir aldri tenant- eller shared tilgang.
8. Tenant deletion kan ikke cascade-slette canonical objekt med annen assignment.
9. Én canonical Organization har én PUBLIC-identitet og publication state.
10. Organization.email følger aktørens PUBLIC-state; personlig e-post gjør ikke.
11. Telefon er ikke personidentitet og blir ikke globalt unik.
12. PUBLIC bruker bare shared editorial tags, aldri internal tags eller overlays.
13. Historisk image state, releases og ledger reassosieres eller omskrives aldri.
14. Hver canonical Organization har nøyaktig én aktiv image-home-assignment til
    samme Organization og SharingDomain; manglende eller ugyldig home avviser
    private image writes.
15. Image-home-transfer er separat, atomisk, capabilitykontrollert og auditert,
    og endrer bare framtidig private-write-scope.
16. En senere assignment endrer aldri image home automatisk.
17. Importmatching, assignment og publication er separate, eksplisitte handlinger.
18. Defaults for alle nye shared read/write-gater er avslått til verifisert.

## Migreringsstrategi

Overgangen gjennomføres i følgende små, additive leveranser og i denne
rekkefølgen:

1. SharingDomain og tenant-domain binding.
2. Nullable canonical domain fields.
3. OrganizationTenantAssignment og PersonTenantAssignment.
4. Backfill én assignment fra legacy tenant.
5. Read-only duplicate inventory og migration manifest.
6. Shadow read som sammenligner legacy tenant og assignments.
7. Tenantprivate overlays.
8. Agreement, capabilities og audit.
9. Canonical writer-services og revision/stale-kontrakt.
10. Canonical PUBLIC identity/projection.
11. Image-home bridge uten reassosiering.
12. Canonical contacts og relations i samspill med ADR-005.
13. Structured places gjennom ADR-012.
14. Import 2.0 etter persistent storage.
15. Legacy read/write deprecation.
16. Fysisk cleanup bare gjennom egen senere gate.

Hver leveranse skal ha eget avgrenset scope, migrasjons- og datainvariant,
negative tester, featureflag/shadow-gate, stagingbevis og rollback. Et senere
felt- eller modellnavn kan tilpasses kodebasen, men rekkefølgen og invariantene
kan ikke svekkes uten ny arkitekturreview.

## Featureflagg og shadow-prinsipp

Implementasjonen skal ha separat, fail-closed aktivering for minst:

- sharing-domain shadow
- assignment read
- assignment write
- private overlays
- agreement/capabilities
- canonical writer
- canonical PUBLIC projection
- image-home bridge

Endelige settingsnavn avgjøres i implementeringen. Alle kode- og
eksempeldefaults er avslått til aktuell gate er testet. En write-gate kan ikke
aktiveres bare fordi tilhørende frontend er skjult eller en read-gate er grønn.
Shadow sammenligner ny og gammel lesing uten å endre autoritativ state og må
rapportere aggregert, tenant-/domain-scopet og uten unødvendig PII.

## Implementeringsleveranser og avhengigheter

Den detaljerte implementeringsplanen godkjennes i fase 5E, men skal følge disse
avhengighetene:

- Ingen kodeimplementasjon inngår i denne PR-en.
- Deletion/`CASCADE` må herdes før multi-tenant assignment aktiveres.
- Global role fallback må fjernes før shared capabilities aktiveres.
- De gjenværende juridiske/personvernmessige portene for avtale,
  personvernerklæring, behandlingsgrunnlag og juridisk kontroll må være
  godkjent før delte persondata aktiveres i produksjon.
- Image-home-opprettelse, legacybackfill, single-/multiassignment-valg,
  fail-closed validering og kontrollert transfer må være implementert og
  verifisert før `Organization.tenant` mister semantisk betydning.
- ADR-012 er godkjent; dens trinnvise implementeringsporter må oppfylles før
  structured places eller maps bygges.
- Contact-/relationship-målarkitekturen må være klar før full Import 2.0.
- Persistent import storage må være aktiv og restore-verifisert før Import 2.0.
- Browser-aktiv Codex er ikke nødvendig for ADR/backendgrunnmur, men er en hard
  gate for senere Import 2.0- og kart-UI.

## Testkrav

Hver relevant leveranse skal minst dekke:

- eksakt domain-likhet og avvisning av cross-domain lesing, matching og writes
- alle roller, inaktiv bruker, manglende/inaktiv membership, manglende/utgått/
  tilbakekalt acceptance og manglende capability
- at global Django-gruppe alene aldri gir tenanttilgang
- create i egen tenant og avvisning av create/assignment i vilkårlig annen tenant
- idempotent assignment og konflikt-/stale-avvisning
- tenant deletion, siste assignment og canonical objekt med flere assignments
- full serializersperre for andre tenanters overlays og internal tags
- avvikende ikke-tom importverdi krever eksplisitt review
- én PUBLIC-rad/-side per canonical Organization og entydig org.nr.-alias
- Organization.email på publisert aktør og separat phone toggle
- relasjonsspesifikk person-/kontaktpublication etter ADR-005
- samme E.164 på flere personer uten automatisk merge
- legacybackfill gir nøyaktig én image home fra korrekt legacyassignment
- ny Organization med én assignment får denne assignmenten som image home
- ny Organization med flere assignments krever et eksplisitt, typed og atomisk
  image-home-valg; UI-forvalg alene er ikke gyldig serverbeslutning
- image home er en aktiv assignment til samme Organization og SharingDomain
- en ny senere assignment endrer ikke image home
- private image writes uten gyldig image home avvises server-side
- image-home-transfer er atomisk, capabilitykontrollert og auditert og endrer
  bare framtidig private-write-scope
- historisk asset-, original-, rendition-, selection-, review-, release-,
  public-key-, ledger-, deny-/takedown- og snapshotidentitet forblir byte- og
  scopeuendret ved opprettelse eller transfer
- manglende private credentials i andre tenants og uendret PUBLIC-projeksjon
- featureflagg av/på, shadow-samsvar, rollback og ingen skjult write
- backup/restore og database–fil-konsistens før Import 2.0-aktivering

Alle permissionskontroller skal ha negative server-side tester. UI-tester alene
er ikke sikkerhetsbevis.

## Staginggater

Staging skal aktiveres trinnvis med eksakt commit og dokumentert pre-/poststate:

1. schema og backfill uten endret runtimeadferd
2. read-only inventory og migration manifest uten PII i Git
3. shadow read med likt resultat eller forklarte avvik
4. deletion- og rollehardening før assignment write
5. agreement/capabilities med negative domain- og rolletester
6. overlays og canonical writer med revision-/auditbevis
7. canonical PUBLIC shadow, additiv API-identitet og kontrollert cutover
8. image-home bridge med legacybackfill, single-/multiassignment-opprettelse,
   fail-closed ugyldig/manglende home, kontrollert transfer og byte-/scopeuendret
   historisk image-, release- og ledgeridentitet
9. contacts/relations etter ADR-005 og places etter ADR-012
10. Import 2.0 først etter persistent-storage-, backup-/restore- og UI-gatene

Hver gate skal bevare eksisterende PUBLIC-, image-, ledger-, takedown-, import-
og kontaktinvarianter som ikke eksplisitt endres av den aktuelle leveransen.

## Rollback

Før første shared write kan additive schema og shadowlesing normalt reverseres
etter egne migrasjonstester, så lenge ingen ny semantisk state går tapt.

Etter første semantiske shared write er normal rollback:

- slå av aktuell featuregate
- rulle read path tilbake
- deaktivere canonical/assignment writer
- bruke kontrollert dual-read mot legacy der det er trygt
- bevare assignments, acceptance, audit, overlays, aliases og canonical state
- rette framover etter inventory og review

ADR-et lover ikke destruktiv reverse migration etter at assignments,
agreementacceptance, canonical merges eller overlays er tatt i bruk. Gamle image
releases, keys, events, snapshots og ledgerstate skal aldri omskrives eller
reassosieres som rollback.

Etter at image home er etablert eller overført, kan rollback slå av nye private
image writes eller rulle lesestien tilbake, men den kan ikke automatisk velge
legacytenant, operativ tenant eller nyeste assignment som home. Rollback skal
bevare nøyaktig én aktiv image-home-assignment, transferaudit og all historisk
image-/release-/ledgeridentitet byte- og scopeuendret. En feil home rettes
framover gjennom den samme separate, atomiske og auditerte transferhandlingen.

## Alternativer vurdert

### Permanent canonical hubmodell

Avvist fordi eksisterende Organization- og Person-rader kan være canonical
direkte. En hub ville gitt ekstra joins, identitetsmapping og en parallell
sannhetsmodell uten en konkret blocker.

### Beholde én kopi per tenant

Avvist fordi delt redaksjonell informasjon og én offentlig aktør ellers driver
mellom kopier. Synkronisering mellom kopier blir en skjult merge- og
konfliktmotor.

### Én redaksjonell home tenant for canonical core

Avvist fordi canonical core er felles i SharingDomain. En home tenant ville gi
tilfeldig eller organisatorisk feil skriveautoritet. Image-home beholdes kun som
en smal bro for historisk privat image scope.

### Global deling mellom alle plattformtenants

Avvist av sikkerhets- og personvernhensyn. SharingDomain må alltid være eksplisitt
og eksakt.

### Automatisk assignment ved match eller geografi

Avvist fordi match og geografisk relevans er forslag, ikke autorisasjon eller
eierskap. Assignment krever en eksplisitt typed beslutning.

### Klassifisere alle dagens tags automatisk som shared

Avvist fordi tenantbundne legacytags blander redaksjonell beskrivelse og intern
workflow. Automatikk kan publisere privat eller administrativ informasjon.

### Flytte imagehistorikk til canonical domain

Avvist fordi ADR-007/009 binder historisk state, releases, public keys, deny og
restore til immutable tenant-scopede identiteter. Image-home gir nødvendig
framtidig write-scope uten reassosiering.

### Big-bang cutover og destruktiv cleanup

Avvist fordi permissions, overlays, PUBLIC, bilder, kontakter og import har
ulike risikoer og rollbackbehov. Additive gates og shadowlesing gir kontrollerbar
overgang.

## Begrunnelse

Direkte canonicalisering gjenbruker stabil eksisterende identitet og er den
minste modellen som løser det konkrete samarbeidsbehovet. Assignments gjør
tenanttilknytning eksplisitt uten å kopiere objektet. SharingDomain forhindrer at
deling blir plattformglobal. Overlays, agreement og capabilities bevarer private
og juridiske grenser. Additiv migrering og image-home beskytter historikk og gir
reell rollback uten å love en utrygg reverse.

## Konsekvenser og tradeoffs

Positive konsekvenser:

- én stabil Organization-/Person-identitet innen samarbeidet
- én offentlig aktørside og færre framtidige duplikater
- eksplisitt assignment i stedet for skjult kopiering
- tydelig skille mellom shared editorial core og privat tenantarbeid
- server-side avtalebasert og capabilitybasert tilgang
- gjenbruk av eksisterende PK-er, imagehistorikk og importgrunnlag

Kostnader og risiko:

- autorisasjon blir mer sammensatt enn dagens direkte tenantfilter
- core-writes fra én tenant påvirker andre og krever god UX, audit og revision
- legacytags og eventuelle framtidige duplikater krever menneskelig review
- deletion, global gruppefallback og storage må herdes før aktivering
- kontakt-, relasjons-, place- og image-home-overganger krever egne porter
- rollback etter shared writes er operativ feature/read rollback, ikke alltid
  schema-reverse

## Personvern og sikkerhet

Canonical personer og privacy-minimert domainmatching øker muligheten for
sammenkobling av persondata. Dataminimering, formålsbegrensning og eksakt scope
er derfor del av arkitekturen, ikke bare UI-policy.

Shared match skal vise minst mulig informasjon som trengs for å velge riktig
objekt. Rå kontaktdata, notater, internal tags, samtykkenotater, arbeidsstatus,
image credentials og auditdetaljer skal ikke inngå uten separat autorisert
behov. Logger og migreringsrapporter skal bruke aggregater eller interne ID-er
og unngå rå PII.

Agreement acceptance er en teknisk adgangsport, men erstatter ikke gyldig
juridisk grunnlag. Aktiv bruker, membership, domain equality, acceptance,
capability og objektscope må alle være oppfylt. Feil eller manglende state skal
feile lukket.

## Åpne eksterne porter

Behandlingsansvaret er avklart: MUSIKKONTORET AS er juridisk
behandlingsansvarlig for CRM-behandlingen og det felles SharingDomainet.
Følgende må fortsatt avklares utenfor denne ADR-leveransen:

- endelig ordlyd og versjonering av avtalen for tilgang til delte CRM-data
- nødvendige oppdateringer i personvernerklæringen
- dokumentasjon av behandlingsgrunnlag, formål, rettigheter og interne
  ansvars-/arbeidsrutiner
- juridisk kontroll før delte persondata aktiveres i produksjon
- redaksjonell mapping/policy for legacytags
- implementering av den godkjente ADR-012 for structured places og actor-only
  maps
- persistent import storage, backup/restore, retensjon og konsistens mot ADR-008
- browser-aktiv Codex før senere Import 2.0- og kart-UI

## Ferdigdefinisjon

### ADR-011 er varig besluttet når

- ADR-et, ADR-indeksen, roadmap, prosjektstatus, impactrapport og berørte
  arkitekturdokumenter er konsistente
- statusen er «Godkjent målarkitektur – ikke implementert»
- beslutning, non-goals, 16 migreringstrinn, tester, gates og rollback er
  eksplisitte
- dokumentasjons-PR-en er CI-grønn og uten åpne P0/P1-funn etter frozen-head
  review

### Målarkitekturen er implementert først når

- alle nødvendige schema-, data-, permission-, agreement-, overlay-, writer-,
  PUBLIC-, image-home-, contact/relation- og storagegater er levert separat
- ADR-012-avhengige structured places er levert i sin godkjente etappe
- negative domain-/rolle-/privacytester og stagingbevis er grønne
- historisk image- og auditstate er bevart
- legacy read/write er kontrollert avviklet og eventuell fysisk cleanup er
  godkjent i egen senere gate

Godkjenning av dette ADR-et betyr ikke at noen av disse runtimekravene allerede
er implementert.
