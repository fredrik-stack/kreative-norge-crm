# ADR-007: Tenant-eid bildeassetarkitektur

## Status

Godkjent som arkitekturgrunnlag. Fase 3A, de isolerte fase 3B.1- og 3B.2-prototypene og fase 3B.1R med representativ kvalitetsvalidering er gjennomført. Fase 3B.3 har fastsatt separat UUIDv4-basert public release identity, canonical public release keys og varig release-reservasjon. Fase 3B.3-A har implementert den additive organization-typed release-aggregaten, canonical key-builderen, immutable historisk mapping og atomisk feature-gated opprettelse i databasedomenet. Fase 3C.7 har implementert intern processing/storage, og fase 3D.1 har implementert første offisielle website/Open Graph-kandidatflyt til eksplisitt Organization-selection bak det fortsatt avslåtte kode-default-flagget. Fase 3D.2 er implementert, fullverifisert lokalt, CI-grønn, teknisk stagingverifisert, live-provider-verifisert og visuelt eiergodkjent med Brave, limt URL, upload, fokus-/zoom-UX og valgfri asset-alttekst. Brave-integrasjonen er likevel **operativt ikke aktiv** for ordinære Editor-sluttbrukere: staging-credentialen er deaktivert etter live-testen, og senere reaktivering krever at den manuelle sluttbrukeravtalegaten nedenfor er dokumentert oppfylt. [ADR-008](ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md) velger lokal one-server media og kryptert Hetzner Storage Box-backup som operasjonell MVP. [ADR-009](ADR-009-PUBLIC_IMAGE_RUNTIME_RELEASE_DELIVERY_AND_RESTORE_SAFE_DENY_STATE.md) formaliserer den godkjente fase 3E-runtimearkitekturen; 3E.1A-journalen er `ACTIVE` i staging og 3E.1B-kontrakten er godkjent, mens materialisering, controlled serving, projection, API/PUBLIC-cutover og takedown fortsatt ikke er implementert.

**Beslutningsdato:** 2026-07-30

**Fase 3B.1-valg godkjent:** 2026-07-31

**Fase 3B.2-valg godkjent:** 2026-08-01

**Fase 3B.1R-valg godkjent:** 2026-08-07

**Fase 3B.3-valg godkjent:** 2026-08-07

**Fase 3D.2 gjennomført og merget:** 2026-08-11; PR #33 er merget til `main` som `48f23f183dacb8331a64b86f1d7574250cbfbe02`, med grønn main-CI-run `31535260891`

**Dokumentert i repo:** 2026-08-13

Fase 3B.3-dokumentasjonsleveransen innebærer ingen applikasjonskode, datamodell, migrasjon, storage-konfigurasjon, API-endring, frontendendring, dataendring eller deploy. Dagens legacyflyt med eksterne bilde-URL-er gjelder fortsatt frem til en kontrollert overgang er implementert og verifisert.

## Forhold til tidligere ADR-er

ADR-007 viderefører:

- [ADR-001](ADR-001-TENANT_ARCHITECTURE.md): kandidater, assets, selections, renditions, events og alle bildekommandoer skal være tenant-isolerte
- [ADR-003](ADR-003-PUBLICATION_MODEL.md): private originaler, intern proveniens og audit skal være adskilt fra offentlig bildeleveranse
- [ADR-004](ADR-004-IMPORT_ARCHITECTURE.md): import skal bruke preview, review og eksplisitt commit, også når et bilde inngår
- [ADR-005](ADR-005-CONTACT_ARCHITECTURE.md): én felles offentlig projeksjon skal hindre at Editor-preview, HTML og API får egne regler
- [ADR-006](ADR-006-SESSION_WORKFLOW.md): godkjent retning skal lagres varig før større implementering starter

ADR-007 endrer ikke kontaktmodellen eller publiseringsreglene i ADR-003 og ADR-005. Et bilde kan være godkjent og låst uten at aktøren er publisert. En bildehandling skal aldri aktivere eller endre aktør-, person- eller kontaktpublisering.

ADR-009 presiserer public runtimeen som bygger videre på dette ADR-et: lokal append-only SQLite-ledger med restore-sikkert off-server anker, separat public delivery-root, create-only materialisering, kontrollert serving, én `PublicImageProjection` og trinnvis aktivering før formell takedown.

## Bakgrunn

Dagens `Organization` lagrer eksterne URL-er i blant annet `thumbnail_image_url`, `auto_thumbnail_url` og `og_image_url`. Editor-preview kan i tillegg falle tilbake til en ekstern favicon-tjeneste. URL-ene kan endres, forsvinne, blokkere hotlinking eller peke på et lite, irrelevant eller teknisk ugyldig bilde. En kandidat kan bli valgt uten faktisk dekoding, varig original, renditions, redaksjonell låsing eller en komplett godkjenningshistorikk.

Dagens løsning har heller ikke en eksplisitt media-/objektlagringskontrakt for aktørbilder. PUBLIC, public API og Editor bruker beslektede, men ikke identiske bildekilder og fallbackregler. Kortene har forskjellige størrelser og dupliserte visningsregler, og detaljsiden mangler komplett canonical-, Open Graph- og Twitter Card-metadata.

Fase 3A kartla backend, frontend, PUBLIC, API, import, storage, drift og kortvarianter. Kartleggingen viste at URL-flyten kan brukes som midlertidig kandidat- og migreringsgrunnlag, men ikke som målarkitektur.

## Beslutning

### 1. Ansvarsdelingen

Målarkitekturen er:

```text
ImageCandidate
    → kontrollert fetch og teknisk validering
    → tenant-eid ImageAsset
    → OrganizationImageSelection
    → ImageRendition
    → én felles public image projection
```

Viktige overganger registreres i en append-only `ImageReviewEvent` eller en modell med tilsvarende ansvar.

Pilen beskriver ansvarsdeling, ikke at alle rader alltid må opprettes i samme transaksjon eller i samme øyeblikk. Et validert og godkjent asset kan for eksempel finnes før en ny `Organization` opprettes i import. Obligatoriske filer og renditions skal likevel være ferdige før et bilde kan kobles inn av en kort database-commit.

Modellnavn kan justeres etter repoets navnestandard. Ansvarsdelingen og invariantene i dette ADR-et skal beholdes.

### 2. Konseptuelle modeller

#### `ImageCandidate`

En midlertidig, tenant-avgrenset kandidat fra en godkjent kilde.

Kandidaten skal minst kunne dokumentere:

- tenant
- kandidatstatus
- kildetype og provider
- kilde-URL og eventuell kildeside
- oppdagelses- og utløpstidspunkt
- teknisk resultat og varsler
- eventuell kobling til review, `ImportJob` eller `ImportRow`

En kandidat er aldri et aktivt offentlig bilde. Nødvendig proveniens kopieres til asset og godkjenningshendelse før kandidaten slettes.

#### `ImageAsset`

Et tenant-eid, teknisk validert bildeasset med privat original.

Assetet skal minst kunne dokumentere:

- tenant
- privat storage key
- checksum
- faktisk format, MIME-type, dimensjoner og filstørrelse
- prosesserings- og valideringsversjon
- teknisk status og relevante varsler
- nødvendig proveniens for valgt kandidat
- eventuell pålitelig registrert kreditering

Assetet eies ikke direkte av `Organization` og kan eksistere før en aktør opprettes. Asset-bytes er immutable. Ny prosessering, endret fokus eller endret fit skal gi en ny selection-/renditionversjon, ikke overskrive historiske filer.

Det skal ikke finnes logisk eller synlig cross-tenant-gjenbruk. Eventuell fysisk byte-deduplisering må være helt skjult, må ikke svekke tenant-isolasjonen og er ikke nødvendig i første MVP.

#### `OrganizationImageSelection`

En typed kobling mellom én aktør og enten et godkjent asset eller Kreative Norge-fallback.

Selection skal minst kunne bære:

- tenant og aktør
- selection-kind: asset eller systemfallback
- assetreferanse når kind er asset
- fit-modus
- ett normalisert fokuspunkt
- alt-tekst; valgfri for asset-selection, men påkrevd for eksplisitt systemfallback-selection
- offentlig kreditering når den er relevant eller påkrevd
- status, revisjon og tidspunkt
- hvem som godkjente og låste valget

Det skal bare finnes ett aktivt bildevalg per aktør. Dette håndheves i domenekommando og databaseconstraint.

En selection er et eksklusivt valg:

- asset-selection skal peke på nøyaktig ett asset i samme tenant
- fallback-selection skal ikke peke på et tenantasset

Et godkjent og låst valg overskrives aldri automatisk. «Godkjenn og erstatt bilde» oppretter en ny aktiv revisjon, arkiverer forrige selection og registrerer hendelsen. Gjenoppretting av et ordinært arkivert bilde oppretter også en ny revisjon, slik at historikken ikke omskrives.

Asset-alttekst kan være eksakt tom streng. Tom verdi er en eksplisitt redaksjonell verdi og skal ikke omskrives eller fylles skjult med aktørnavn; en ikke-tom verdi som bare består av whitespace er ugyldig. Eksplisitt systemfallback-selection beholder krav om ikke-tom tekst i domenetjenesten og databaseconstraintet. `ImageReviewEvent.alt_text_snapshot` følger selectionverdien og kan derfor også være tom for asset-events.

Schema-migrasjon `0027` er uten datarewrite og kan reverseres mens alle selection- og event-altverdier fortsatt er ikke-tomme. Etter første blanke asset-/event-alt er migrasjonen forward-only fordi de gamle nonempty-constraintene blokkerer reverse. Operativ rollback er da feature-off og en fremoverrettet retting; en pre-deploy-backup må tas og verifiseres før aktivering. Eksisterende verdier skal ikke omskrives, og aktørnavnet skal aldri brukes som skjult alttekstfallback for å tvinge schemaet bakover.

Fit og ett fokuspunkt lagres på selection i første MVP. En egen `ImagePlacement` og flere fokuspunkter utsettes til fase 3B viser et faktisk behov.

#### `ImageRendition`

En kontrollert, avledet rasterfil for en bestemt variant og prosesseringsversjon.

Første kontrakt omfatter:

- `square`
- `landscape`
- `share` på 1200 × 630

Rendition skal minst dokumentere variant, bredde, høyde, format, checksum, prosesseringsversjon og immutable storage key. Processing profile v1 bruker `square` 512 × 512, `landscape` 800 × 450 og `share` 1200 × 630. Formatmapping og nøkkelkontrakt er fastsatt i punkt 23.

Et rendition-sett identifiseres av asset, fit, fokuspunkt og prosesseringsversjon. Det kan forberedes fra en typed og godkjent presentasjonsoppskrift før `Organization` finnes. Den senere selection-revisjonen peker til nøyaktig dette immutable settet; endret fit, fokus eller prosesseringsversjon gir et nytt sett.

Eksakt modellering av `rendition_set` eller tilsvarende kan følge repoets navnestandard, men referanseintegriteten kan ikke bare ligge i JSON. Nye størrelser eller formater utover processing profile v1 krever en ny versjonert profil og nye immutable keys.

#### `ImageReviewEvent`

Det append-only sporet for blant annet:

- oppdagelse og teknisk review
- godkjenning og låsing
- eksplisitt erstatning
- ordinær arkivering og gjenoppretting
- valg av fallback
- formell takedown og eventuell gjenoppretting
- kontrollert sletting eller anonymisering etter retensjonsreglene

Et event skal ikke kunne redigeres eller regenereres som eneste historikkilde. Det skal beholde nødvendige snapshots selv om en kandidat, fil, bruker eller aktør senere slettes. Rollback skjer med en ny kompenserende hendelse, ikke ved å omskrive tidligere events.

For uvalgte kandidater lagrer eventet bare minimal, ikke-gjenopprettbar overgangsinformasjon som kandidat-ID, tenant, status og tidspunkt. Kilde-URL, providerpayload og detaljert kandidatmetadata følger kandidatens retensjon. Nødvendig proveniens snapshots først i asset-/approval-event når kandidaten velges. Utløp kan registreres med et nytt tombstone-event uten å redigere den gamle hendelsen.

#### Godkjenningstekst

Godkjenningstekster skal ha en stabil og immutable versjon. Godkjenningshendelsen lagrer både versjonsidentifikasjon og eksakt tekstsnapshot. Dermed beholder tidligere godkjenninger opprinnelig ordlyd selv om produktteksten får en ny versjon.

#### Public image projection

Den offentlige bildeprojeksjonen er en read-only resolver eller DTO, ikke en ny lagret sannhetskilde.

Den skal:

- motta en allerede autorisert eller offentlig aktør
- velge den ene aktive selection eller systemfallback
- returnere kontrollerte renditions, fit, alt-tekst og eventuell offentlig kreditering
- brukes av Editor-preview, PUBLIC HTML, public API og delingsmetadata
- aldri gjøre DNS-oppslag, ekstern fetch, dekoding eller bildegenerering under lesing
- aldri returnere intern kilde, proveniens, audit, karanteneinformasjon eller privat original

Projection lager ingen alternativ aktør- eller kontaktpubliseringsregel. `Organization.is_published` og øvrige etablerte publiseringsgater gjelder fortsatt.

### 3. Tenant- og referanseinvarianter

- Alle kandidater, assets, selections, renditions og events har eksplisitt tenant.
- Alle relasjoner og kommandoer avviser tenant-mismatch.
- Plattformvid superadminhandling skal fortsatt angi og auditere måltenant.
- En rolle med navnet `superadmin` i én tenant gir ikke i seg selv plattformvid tilgang. I dette ADR-et betyr plattform-superadmin dagens Django `is_superuser` eller en senere uttrykkelig global principal.
- `TenantMembership.Role.SUPERADMIN` forblir tenant-avgrenset og får samme image-scope som gruppeadmin inntil en egen global principal eventuelt er etablert.
- Ingen `GenericForeignKey` brukes i første implementering.
- Det opprettes ikke en generell selection-modell for alle objekttyper i første implementering.
- Første implementering gjelder `Organization`. Personer og prosjekter kan få egne typed selection-modeller senere.
- Ingen fil slettes mens den er referert av en gyldig selection, importbeslutning, aktiv review eller eksplisitt legal hold/file-pinning-status.
- Et historisk event som bare beholder asset-ID, checksum eller annet minimalt snapshot, pinner ikke i seg selv bildefilen.
- Hvis samme tenantasset senere tillates brukt av flere aktører, skal hver aktør ha egen selection og aktørspesifikk godkjenning. Takedown og garbage collection skal da være referansebevisst. Fase 3B avgjør om første MVP i stedet forbyr slik logisk gjenbruk for å redusere kompleksitet.

#### Tekniske og redaksjonelle tilstander

Følgende er forskjellige tilstander og skal ikke slås sammen:

- teknisk valid asset
- redaksjonelt godkjent asset eller presentasjonsoppskrift
- aktiv og låst selection
- publisert aktør

Et asset kan godkjennes i en tenant-avgrenset importreview før aktøren finnes. Godkjenningen registreres da i append-only event og en typed importbeslutning med fit-/fokusoppskrift og immutable rendition-sett. Den gjør ikke assetet offentlig og oppretter ikke en aktør-selection før `Organization` finnes.

Fase 3B skal bevise hvordan et immutable rendition-sett kan gjøres klart fra asset og godkjent presentasjonsoppskrift før den korte import-committen, uten løs JSON-referanse eller ekstern I/O i transaksjonen.

### 4. Teknisk validering før redaksjonell godkjenning

Ekstern URL er bare en kandidat. Vanlig lagring av en aktør skal ikke hente, dekode, velge eller aktivere bilder.

Kontrollert ingest skal minst støtte:

- bare tillatte HTTP-/HTTPS-kilder
- SSRF- og redirectbeskyttelse
- timeout og eksplisitte byte-/pixelgrenser
- kontroll av MIME-type mot faktiske bytes
- faktisk dekoding og dimensjonskontroll
- beskyttelse mot korrupte filer og decompression bombs
- checksum og idempotent behandling
- orienteringshåndtering og kontrollert EXIF-fjerning
- eksplisitt SVG-policy og trygg rasterisering eller avvisning
- blokkering av favicons, sosiale medie-/plattformlogoer og andre generiske plattformikoner

Processingbibliotek, første formatsett, kildefilstørrelse, decoded pixelgrense, dimensjons-/no-upscale-regler, advisory kvalitetsmål og sRGB-outputkontrakt er godkjent i punkt 23. SVG-policy, eventuell skadevarekontroll, workergrense og øvrig runtimeplassering avgjøres fortsatt gjennom senere fase 3B-gater.

Relevans, vannmerke, plakat-/datoinnhold, mye tekst, usikker aktørmatch og lignende kan være review-varsler. En kjent plattformlogo kan ikke godkjennes som aktørbilde.

### 5. Rask og sporbar bildegodkjenning

Standardhandlingen er:

> Godkjenn og lås bilde

Brukeren skal normalt ikke måtte fylle ut fotograf, kreditering, lisens, rettighetshaver, juridisk grunnlag eller juridiske merknader.

Godkjenningstekst versjon 1 er:

> Jeg bekrefter at bildet er relevant for aktøren, at det kommer fra aktøren selv, en offisiell kilde eller en annen kilde som tillater bruken, og at det kan publiseres i Kreative Norge og tilhørende kort- og delingsvisninger.

Ordlyden er et produktutgangspunkt, ikke en juridisk konklusjon.

Godkjenningshendelsen skal konseptuelt lagre:

- tenant
- bruker
- tidspunkt
- tekstversjon
- eksakt tekstsnapshot
- eksisterende aktør-ID og snapshot, eller et immutable proposed-actor-/ImportRow-snapshot når aktøren ikke finnes ennå
- asset-ID
- checksum
- kilde-URL
- kildeside
- provider eller søkekilde
- teknisk kvalitetsresultat
- varsler
- tidligere selection ved erstatning

Fetch, dekoding, rendition-generering og storage-upload skal være ferdig før brukeren bekrefter. Selve approval-/selection-kommandoen skal være en kort, atomisk databaseoperasjon med append-only event.

### 6. Personvern, bruksvilkår og konkret godkjenning

Tre mekanismer holdes adskilt:

1. Personvernerklæringen forklarer behandling, offentlig visning, protest og fjerning.
2. Bruksvilkårene beskriver brukerens ansvar ved opplasting og bildegodkjenning.
3. Den konkrete bildegodkjenningen er den raske og sporbare bekreftelsen knyttet til ett asset og eventuelt én aktør.

De skal ikke være samme databasefelt, samme aksepttidspunkt eller samme juridiske mekanisme.

### 7. Kreditering

- Kreditering er ikke obligatorisk i standardflyten.
- Pålitelig kreditering registreres automatisk når den finnes.
- Brukeren kan legge inn eller korrigere kreditering.
- Kreditering vises offentlig bare når den er relevant eller kreves.
- Et konkret kjent krediteringskrav må oppfylles eller gå til særskilt review før godkjenning.
- Manglende kreditering uten kjent krav blokkerer ikke standardflyten.
- Intern kilde og proveniens blir ikke offentlig bare fordi den er lagret.

Redigerer kan oppfylle et kjent krav ved å registrere den nødvendige krediteringen, men kan ikke fravike eller overstyre kravet. Særskilt vurdering av unntak eller uklar rettighets-/krediteringssituasjon krever gruppeadmin i egen tenant eller plattform-superadmin. Vurderingen er fortsatt en produktbeslutning, ikke en juridisk konklusjon.

### 8. Roller og capabilities

Rettighetene skal håndheves server-side per handling og objekt. Dagens generelle read/write/delete-regel er ikke tilstrekkelig.

| Handling | Plattform-superadmin | Gruppeadmin og tenant-superadmin | Redigerer | Leser |
| --- | --- | --- | --- | --- |
| Se bilde og vanlig status | Alle tenants | Egen tenant | Egen tenant | Egen tenant |
| Finne kandidater og laste opp | Alle tenants | Egen tenant | Egen tenant | Nei |
| Velge systemfallback | Alle tenants | Egen tenant | Egen tenant | Nei |
| Godkjenne og låse | Alle tenants | Egen tenant | Egen tenant | Nei |
| Godkjenne og erstatte låst bilde | Alle tenants | Egen tenant | Egen tenant | Nei |
| Ordinær arkivering, fjerning til fallback og gjenoppretting | Alle tenants | Egen tenant | Egen tenant | Nei |
| Se nødvendig bildehistorikk | Alle tenants | Egen tenant | Egen tenant | Nei |
| Hente privat original | Alle tenants | Egen tenant | Nei; bare kontrollert review-preview | Nei |
| Løse særskilt krediterings-/rettighetsreview | Alle tenants | Egen tenant | Nei | Nei |
| Formell takedown og gjenoppretting etter takedown | Alle tenants | Egen tenant | Nei | Nei |
| Administrere retensjon og karantene | Alle tenants | Egen tenant | Nei | Nei |
| Arbeide på tvers av tenants | Ja | Nei | Nei | Nei |

Leser kan ikke se sensitiv audit, kilde, godkjenningstekst, takedownårsak, privat original eller karanteneinformasjon. Redigerer kan se nødvendig kilde, teknisk reviewgrunnlag og en kontrollert review-preview, men kan ikke laste ned privat original eller administrere særskilt rettighetsreview, formell takedown, retensjon eller karantene.

Disse bilde-capabilities avgjør ikke de fortsatt separate rollespørsmålene for kontaktpublisering og full kontakteksport i ADR-005.

### 9. Låsing, erstatning og ordinær fjerning

Et låst bilde kan bare erstattes gjennom en eksplisitt handling tilsvarende:

> Godkjenn og erstatt bilde

Handlingen skal:

1. kontrollere rolle, tenant, teknisk status og nødvendig godkjenning
2. arkivere tidligere selection
3. opprette og aktivere ny selection-revisjon
4. registrere tidligere og ny selection i append-only event
5. la alle publiseringsflagg være urørt

En redigerer kan ordinært fjerne et bilde og gå tilbake til fallback. Et ordinært arkivert bilde kan gjenopprettes gjennom en ny selection-revisjon.

En ny kandidat, et varsel, en ny Open Graph-verdi eller en import uten eksplisitt bildevalg kan aldri erstatte et låst bilde.

### 10. Aktivt bilde under ny review

Et aktivt godkjent bilde beholdes offentlig ved vanlige varsler eller ny review.

Bildet fjernes straks fra den aktive projeksjonen bare ved:

- teknisk sikkerhetsproblem
- alvorlig bekreftet feil
- formell takedown
- eksplisitt autorisert administratorhandling

Ordinær usikkerhet eller et nytt kandidatfunn fører til review, ikke automatisk avpublisering.

### 11. Retensjon

#### Uvalgte kandidater

- beholdes normalt maksimalt 30 dager; valgt kandidat eller dokumentert aktiv review er de eneste unntakene
- slettes automatisk når de ikke er valgt og ikke lenger inngår i aktiv review
- får et eksplisitt utløpstidspunkt eller tilsvarende sporbar regel
- aktiv review kan sette en ny eksplisitt `expires_at` med ansvarlig bruker og begrunnelse; inaktiv review kan ikke brukes som permanent unntak

#### Godkjente assets

- aktiv original og nødvendige renditions beholdes så lenge bildet er i bruk
- erstattede og ordinært arkiverte assets beholdes sammen med aktøren i første MVP
- godkjente arkivbilder slettes ikke automatisk i første MVP
- et forhåndsgodkjent asset for en ny importaktør skal overleve midlertidig commit-feil
- et godkjent, men forlatt og aldri tilknyttet asset skal ha eksplisitt retensjonsstatus og referansebevisst cleanup; eksakt frist avgjøres før denne importflyten aktiveres

#### Slettet aktør

- tilknyttede bildefiler får en 30 dagers sikkerhetsperiode før kontrollert sletting
- slettingen skal være en eksplisitt livssyklus og kan ikke avhenge av ukontrollert cascade
- minimal auditinformasjon og nødvendige snapshots kan beholdes etter at bildefilen slettes

#### Formell takedown

- har ikke én automatisk slettedato for alle saker
- avsluttes med gjenoppretting, erstatning eller kontrollert sletting
- beholder årsak, bruker, tidspunkt og beslutningshistorikk

Automatisk cleanup skal være idempotent. Fase 3B avgjør om den kjøres med management job, scheduler eller bakgrunnskø.

### 12. Formell takedown og karantene

Formell takedown skal:

1. fjerne aktiv offentlig selection og la projection gå til systemfallback
2. stoppe nye offentlige referanser til alle berørte renditions
3. blokkere eller fjerne offentlig origin-tilgang
4. utløse og verifisere nødvendig lokal cache-/media-origin-purge, og eventuell CDN-invalidering dersom CDN senere innføres
5. flytte eller merke originalen som begrenset privat karantene
6. registrere årsak, bruker, tidspunkt og berørte referanser
7. hindre at samme checksum stille lastes opp og godkjennes på nytt av en redigerer

Checksum-deny er tenant-avgrenset som standard. En gruppeadmin i tenant A kan ikke påvirke eller få vite om identiske bytes i tenant B. En global checksum-blokkering er en separat plattform-superadminhandling med eget scope og audit.

Offentlige rendition-nøkler er immutable og cachevennlige, men skal ikke være uoppsigelige. Lokal storage/serving må støtte kontrollert origin-fjerning og purge; en eventuell senere storage-/CDN-provider må bevise samme invariant. Gjenoppretting etter takedown skal bruke ny offentlig rendition-nøkkel.

Takedown skal også invalidere eller korte ned alle cachede PUBLIC HTML-, API-, Open Graph- og projection-responser som fortsatt peker på renditionen.

Systemet kan ikke garantere sletting fra kopier som allerede er lagret i tredjeparts- eller klientcache. Det skal derimot stoppe projection, origin-tilgang og nye leveranser gjennom infrastrukturen under Kreative Norges kontroll.

Ingen formell takedownhandling eller UI aktiveres før både dagens legacygetter/API/Editor-preview og den nye projection respekterer samme deny-status. Kompatibel deny-guard skal innføres og verifiseres før første takedown kan utføres.

### 13. Grafisk Kreative Norge-fallback

Kreative Norge skal ha en deterministisk, systemeid fallback som:

- er tilgjengelig uten ekstern kilde
- kan inneholde aktørnavn, hovedkategori og Kreative Norge-identitet
- bruker kontrollert bakgrunn, font og typografi
- aldri inneholder sosiale medie- eller plattformlogoer
- finnes som square-, landscape- og 1200 × 630-sharevariant
- leveres gjennom samme public image projection som ordinære assets
- brukes automatisk når ingen godkjent aktiv selection finnes
- kan velges eksplisitt i Editor og senere Import 2.0
- ikke krever egen rettighetsgodkjenning per aktør

Automatisk fallback er en resolverregel og skal ikke late som en bruker har godkjent et asset. Et eksplisitt fallbackvalg kan lagres som selection og auditeres.

Fallback-nøkkelen skal versjoneres når navn, hovedkategori, renderer eller design endres. Fase 3B skal også bevise at en statisk nød-fallback finnes dersom dynamisk fallback-generering feiler.

### 14. Fit, fokus og visningskontrakt

- Logo og navnetrekk bruker `contain` og skal ikke kuttes.
- Foto bruker `cover` og det lagrede fokuspunktet.
- Sentrum er standard fokus når et bedre punkt ikke er valgt.
- Editor tilbyr for Foto de diskrete fokusforvalgene Venstre/Midt/Høyre og Topp/Midt/Bunn, tilsvarende normaliserte verdier `0`, `0.5` og `1` per akse.
- Editor tilbyr i tillegg presis X/Y-finjustering og Foto-zoom fra `1.0000` til `3.0000`, der `1.0000` er det største cover-utsnittet uten tom flate og høyere verdi zoomer inn.
- Fokus og zoom er én immutable Foto-renderoppskrift. Hurtigvalgene endrer de samme normaliserte fokusverdiene som presisjonskontrollene; Logo/contain avviser fokus og zoom.
- Klientens live crop-preview bruker samme kantklampede cover-geometri per aspect ratio som serveren. Etter eksplisitt processing er serverens faktiske `square`-, `landscape`- og `share`-renditions autoritativ fasit før approval.
- Bilder skal ikke strekkes eller skaleres opp automatisk for å skjule for lav kildeoppløsning.
- Når nødvendig rendition ikke kan produseres uten oppskalering, skal flyten be om en bedre kilde, velge et annet bilde eller bruke en kontrollert Kreative Norge-komposisjon eller fallback.
- Square, landscape og share bruker samme godkjente original, fit og fokusintensjon.
- Ulike aspect ratios kan ikke ha identisk pikselutsnitt; tilsvarende visninger med samme ratio skal bruke samme cropkontrakt.
- Asset-alttekst er valgfri. Eksakt tom streng bevares som tom streng uten skjult fallback; whitespace-only er ugyldig. Dette endrer ikke kravet om tekst for en eksplisitt systemfallback-selection.

### 15. Kort og PUBLIC

Fase 3 er ikke en generell redesign. Godkjent visuell retning fra dagens Editor- og PUBLIC-forsider beholdes.

| Visning | Mål |
| --- | --- |
| Editor oversikt, desktop og mobil | Behold 84 × 84 kvadrat |
| PUBLIC oversikt, desktop og mobil | Behold 90 × 90 kvadrat |
| Editor detalj/modal, desktop | Behold 160 × 160 kvadrat |
| PUBLIC detalj, desktop | Endres til 160 × 160 kvadrat |
| Editor og PUBLIC detalj, mobil | Rektangulær visning; felles høyde avgjøres i fase 3B |
| Delingsvisning | 1200 × 630 |

Kortkontrakten skal i tillegg sikre:

- samme aktive selection og cropkontrakt i tilsvarende Editor- og PUBLIC-visninger
- grønn semantisk tagfarge i PUBLIC; dagens brune detaljtag fases ut
- robuste navn, kommuner, tags, status og knapper uten horisontal overflow
- kontrollert wrapping av lange ord og enkelt-tags
- uendret bildeplassering når tekstmengden øker
- CRM-kontrollert fallback ved manglende eller ødelagt rendition, uten feilløkke
- felles variant- og designtokens selv om React og Django-template ikke deler samme runtimekomponent

### 16. Public API-overgang

Overgangen er additiv og bakoverkompatibel.

Public API får et strukturert bildeobjekt med:

- `kind`
- alt-tekst
- eventuell offentlig kreditering
- renditions for `square`, `landscape` og `share`
- absolutt HTTPS-URL, bredde og høyde per rendition

Det eksakte toppnivåfeltnavnet og den endelige schemaformen kan finjusteres før API-leveransen.

Følgende er besluttet:

- bare CRM-kontrollerte renditions eller systemfallback eksponeres som aktivt bilde etter cutover
- intern kilde, proveniens, review og audit eksponeres ikke
- kreditering eksponeres bare når den finnes og skal vises
- `thumbnail_image_url` og `preview_image_url` beholdes midlertidig som deprecated kompatibilitetsaliaser
- aliasene peker etter cutover til dokumenterte rendition-URL-er fra samme resolver
- ADR-009 har senere fastsatt at begge deprecated aliasene peker til `image.square.url` fra samme projection
- aliaser og strukturert objekt kan ikke divergere
- fjerning skjer bare i en senere eksplisitt API-versjon eller integrasjonsfase
- alle offentlige URL-er er absolutte HTTPS-URL-er i eksterne miljøer
- rendering av PUBLIC eller API gjør ingen ekstern bildefetch

Eksterne URL-er skal bygges fra miljøkonfigurerte og allowlistede origins:

- én autoritativ public site origin for canonical og `og:url`
- én kontrollert public media origin fra storage-/CDN-kontrakten for rendition-URL-er

De kan være samme host, men trenger ikke være det. Vilkårlig `Host` eller `X-Forwarded-Host` fra requesten skal ikke kunne bestemme canonical eller offentlig bilde-URL.

Internt skrivbart `thumbnail_image_url` er legacy migreringsstøtte og skal aldri tolkes som automatisk godkjenning.

### 17. Canonical, Open Graph og Twitter Card

Den kanoniske PUBLIC-ruten for en aktør forblir `/public/actors/id/<actor_id>/`. Legacy orgnummerrute kan fortsatt gi permanent redirect ved ett entydig publisert treff.

Canonical og `og:url` bygges fra den konfigurerte autoritative public site origin, ikke direkte fra en vilkårlig request-host. Ekstern staging og produksjon skal bruke HTTPS.

Den offentlige detaljsiden skal serverrendre:

- absolutt HTTPS canonical-URL
- `og:title`
- `og:type`
- `og:url` lik canonical
- offentlig `og:description` eller kontrollert fallbacktekst
- `og:image` fra 1200 × 630-share-rendition eller share-fallback
- `og:image:width`, `og:image:height` og `og:image:alt`
- `twitter:card=summary_large_image`
- tilsvarende Twitter title, description, image og image-alt

Upubliserte aktører skal ikke lekke bilde eller metadata. Intern proveniens skal ikke legges i HTML-head.

Arkitekturen lover korrekte metadata og kontrollerte bildefiler. Den lover ikke at alle meldings- eller delingsklienter alltid viser preview.

### 18. Storage-kontrakt

Målretningen er:

- `FileSystemStorage` eller tilsvarende i lokal utvikling, staging og første produksjons-MVP
- lokale, navngitte Django `STORAGES`-aliaser med host-persistente områder for default, private originaler og public renditions
- app, database og aktiv media på samme Hetzner Cloud-server, med kryptert off-server Borg-backup til separat Hetzner Storage Box
- Djangos `STORAGES`-grensesnitt beholdes slik at senere leverandørmigrering ikke endrer domenekontrakten

[ADR-008](ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md) utsetter S3-, AWS-, Backblaze-, CDN- og flerleverandørløpet. Objektlagring vurderes på nytt bare ved dokumentert vekst, tilgjengelighetskrav eller operasjonell belastning. Fase 3B.2s leverandøruavhengige invarianter i punkt 24 gjelder fortsatt.

Storage-kontrakten er:

- originaler er private
- aktive offentlige renditions har immutable, cachevennlige public release keys i en dedikert, unversioned delivery-store eller et likeverdig namespace
- offentlig delivery skjer gjennom en kontrollert same-origin/media-origin på dagens server i MVP; intern filesystempath eksponeres ikke
- originaler krever autentisert og rollebeskyttet administrativ tilgang
- database og bildefiler inngår begge i backup og restore
- restore skal kontrollere konsistens mellom database, originaler og aktive renditionreferanser
- filer lagres ikke som databaseblob
- host-persistent filesystem eller bind mount brukes for lokal media; et uidentifisert containerlag er ikke akseptabelt varig lager
- eventuell fysisk deduplisering er usynlig og kan aldri bryte tenant-isolasjonen
- lokal serving og cache må støtte takedown, origin-fjerning, idempotent purge og verifikasjon; eventuell senere storage-/CDN-provider må bevise samme kontrakt

Private originaler og offentlige renditions skal bruke egne navngitte `STORAGES`-aliaser, host-paths og tilgangspolicyer. Eksisterende import- og eksportfiler bruker allerede Djangos default storage; bildearbeidet skal ikke endre deres backend eller filplassering uten en separat kompatibilitets- og migreringsplan. ADR-008s backupmodul beskytter dagens containerpaths når de finnes, men flytter dem ikke.

Aktive public rendition-bytes inngår i en godkjent hybridbackup sammen med private originaler, canonical metadata, eksakt processing-version/-profil, nødvendige selection-/release-referanser og audit-/approvalhistorikk. Deterministisk regenerering beholdes som sekundær reparasjonsvei, ikke eneste katastrofeplan. Privat original og nødvendig audit/proveniens skal alltid kunne gjenopprettes etter den vedtatte retensjonen.

Restore kan ikke publisere media før en separat, varig takedown-/deny-journal er avstemt mot den restaurerte databasen og aktive mediaområdet. Takedown som skjedde etter et eldre backup-punkt skal fortsatt vinne. Inntil avstemmingen er verifisert, leverer public image projection systemfallback. Gamle release keys kan aldri reaktiveres automatisk; dersom objektlagring senere innføres, gjelder dette også historiske objektversjoner.

### 19. Bildekilder og providergrense

Editor presenterer kildereisen i denne prioriterte rekkefølgen:

1. offisiell nettside, inkludert Open Graph og vanlige bilder på nettsiden
2. Brave Image Search
3. manuelt limt direkte bilde-URL
4. manuell upload

Systemfallback er et separat selectionvalg, ikke et eksternt kandidatsøk. Ingen kilde kan godkjenne, låse eller erstatte automatisk.

#### Deterministisk Brave-query

Fase 3D.2s foreslåtte query bygges bare fra eksplisitte CRM-fakta:

- lagret aktørnavn er alltid basis i det automatiske forslaget
- nøyaktig én lagret kommune legges automatisk til
- ingen eller flere kommuner gir ikke automatisk sted; ved flere kommuner velger redaktøren én eksplisitt
- kategori og aktivt tilknyttet person er eksplisitte tillegg
- tags brukes aldri
- det brukes ingen AI til querybygging, utvidelse eller lokal rangering
- eksakt query og kildene den bygger på vises før søket og kan redigeres manuelt

Manuelt redigert query sendes eksakt videre innenfor den validerte grensen på 400 tegn og 50 ord. Resultater rangeres lokalt og deterministisk med offisielt domene som sterkeste signal, deretter aktørnavn, eksplisitte refinements og til slutt providerrekkefølge.

Strukturerte kommune-/kategori-/person-refinements gjelder bare det urørte deterministiske forslaget. Ved første manuelle tekstendring skal klienten nullstille alle chips og refinement-ID-er. Backend skal avvise `query_edited=true` kombinert med et nonempty refinement og signere queryproveniens kun som `manual_edit`. Dermed kan ingen skjulte kommune-, kategori- eller personsignaler påvirke rangeringen av et manuelt redigert søk.

#### Offisiell Brave API-kontrakt og vilkårsgrense

Provideradapteren bruker `GET https://api.search.brave.com/res/v1/images/search` og autentiserer server-side med `X-Subscription-Token`. Følgende parametre er faste i 3D.2:

- `country=NO`
- `search_lang=nb`
- `safesearch=strict`
- `spellcheck=false`
- `count=30`

`search_lang=nb` er et bevisst og dokumentert avvik fra ønsket norskekode `no`: Braves offisielle [API-referanse](https://api-dashboard.search.brave.com/api-reference/images/image_search) og [Image Search-dokumentasjon](https://api-dashboard.search.brave.com/documentation/services/image-search) støtter `nb`, men ikke `no`, i enumen for `search_lang`. `spellcheck=false` hindrer at provider omskriver den synlige queryen. Timeout, HTTP-feil, `429`, ugyldig content type, for stor/malformed JSON og manglende servernøkkel feiler kontrollert uten å eksponere nøkkelen.

[Braves standard API-vilkår](https://api-dashboard.search.brave.com/documentation/resources/terms-of-service) begrenser lagring/caching av Search Results til transient bruk med mindre egne storage-rettigheter er avtalt. Derfor gjelder følgende:

- full providerrespons lagres aldri
- bare eksakt query, querykilder og det normaliserte nødvendige delsettet av bilde-URL, kildeside, domene, tittel, publisher, dimensjoner og thumbnail kan ligge i omtrent 30 minutter gamle signerte refs bundet til tenant, Organization og bruker
- det opprettes ingen persistent `ImageCandidate` eller søkehistorikk
- når et Brave-bilde velges og prosesseres, beholder eventet `source_type=brave_image_search` og provider, men `source_url` og `source_page_url` lagres tomme; query og providerresultatmetadata kopieres ikke til databasen
- selve valgte bildebytene behandles som redaktørgodkjent tredjepartsinnhold, ikke som en rettighet Brave har gitt; den versjonerte menneskelige bildegodkjenningen gjelder fortsatt

Denne app-retensjonen er ikke det samme som providerens logging. Braves [privacy policy](https://api-dashboard.search.brave.com/privacy-policy) opplyser at standard query-logger kan beholdes i opptil 90 dager. Zero Data Retention krever Enterprise/egen avtale og er ikke aktivert eller dokumentert for denne leveransen.

Live provideraktivering har i tillegg en manuell, operativ avtaleplikt. Braves gjeldende [Search API Terms of Use](https://api-dashboard.search.brave.com/documentation/resources/terms-of-service) punkt 4(c) krever at hver End User er bundet av en skriftlig avtale med Customer med forpliktelser vesentlig tilsvarende bruksbegrensningene i punkt 3(b). Customer har også ansvar for nødvendige privacy notices og samtykker; se dessuten Braves gjeldende [Privacy Policy](https://api-dashboard.search.brave.com/privacy-policy). Prosjekteier har godkjent providerparametrene og den synlige privacy-/rettighetscopyen, men sluttbrukeravtalegaten er ikke dokumentert oppfylt. Brave skal derfor være operativt deaktivert for ordinære Editor-sluttbrukere frem til avtaleeier har dokumentert oppfyllelse. Dette er ikke manglende kode i 3D.2, og ingen consent-, terms- eller brukeravtalemotor inngår i fase 3D.2. Om gaten senere dekkes av eksisterende arbeids-/oppdragsvilkår, egne Editor-vilkår eller eksplisitt digital aksept avgjøres separat.

Direkte URL går gjennom samme normalisering, sikre fetch, preview og processing som official/Brave. Upload går direkte gjennom samme begrensede ingest-/processingprofil. URL-er som kan lagres som tillatt proveniens renses slik at credentials, fragmenter eller kjente signatur-/tokenparametre ikke lagres utilsiktet.

Skjermbildeanalyse er ikke del av første implementering.

### 20. Import 2.0-kontrakt

Fase 3 etablerer kontrakten; full Import 2.0-UX hører fortsatt til roadmapens senere importfase.

Fremtidige typed bildeutfall er:

- `KEEP_LOCKED_IMAGE`
- `SET_APPROVED_IMAGE`
- `USE_APPROVED_FALLBACK`

Manglende bildebeslutning for en eksisterende aktør betyr `KEEP_LOCKED_IMAGE`.

For nye aktører kan et tenant-eid asset godkjennes og gjøres klart før `Organization` opprettes. `ImportRow` eller en typed bildedecision skal referere med referanseintegritet til asset, fit, fokus, processing-version og ferdig immutable rendition-sett. Den skal også ha et immutable proposed-actor-/ImportRow-snapshot som approvalen gjelder. En løs ID eller løs presentasjonsoppskrift i `decision_json` er ikke tilstrekkelig.

Importreview skal huske forventet eksisterende selection og revisjon. Dersom selection er endret etter review, skal commit stoppe med konflikt og kreve nytt review.

`SET_APPROVED_IMAGE` eller `USE_APPROVED_FALLBACK` mot en eksisterende låst selection er en eksplisitt replacement og skal presenteres og auditeres som dette. Manglende valg er fortsatt `KEEP_LOCKED_IMAGE`.

Ved import-commit skjer:

- ingen Brave-søk
- ingen Open Graph-henting
- ingen ekstern nedlasting
- ingen bildekoding
- ingen rendition-generering
- ingen automatisk bildeerstatning
- ingen publiseringsendring

Commit bruker bare et ferdig og godkjent asset eller fallbackvalg, er idempotent og bruker den samme atomiske selection-kommandoen som Editor.

Approvalhistorikken er append-only og ligger ikke bare i JSON eller en commitlogg som kan slettes eller regenereres. En mislykket aktør-commit sletter ikke det forhåndsgodkjente assetet.

### 21. Ingen sideeffekt på publisering

Ingen bildehandling skal endre:

- `Organization.is_published`
- organisasjonens øvrige publiseringsflagg
- personpublisering
- kontaktpublisering
- e-postpublisering
- telefonpublisering

Dette skal både håndheves i domenetjenesten og bevises med regresjonstester.

### 22. Kontrollert legacy-overgang

Legacyfeltene:

- `thumbnail_image_url`
- `auto_thumbnail_url`
- `og_image_url`
- `og_last_fetched_at`

beholdes midlertidig for additiv og reversibel overgang.

De kan:

- brukes som skrivebeskyttet inventar
- foreslås som kandidatkilder
- støtte shadow-sammenligning under cutover

De kan ikke:

- bli godkjent eller aktivt bilde automatisk
- erstatte en låst selection
- overstyre takedown, karantene eller eksplisitt fallback
- brukes som aktiv offentlig kilde etter fullført cutover

Automatisk nettverksrefresh ved vanlig aktørlagring og nettverk inne i import-commit skal fases ut.

Feltene droppes først i en separat leveranse etter stabiliseringsperiode, dokumentert integrasjonskontroll og egen rollbackbeslutning. Deprecated public aliaser kan bestå lenger enn de interne URL-feltene.

Rollback kan aldri gjeneksponere et tatt ned, avvist, karantenelagt eller eksplisitt erstattet legacybilde. Takedown- og deny-status har prioritet over enhver midlertidig legacyresolver.

### 23. Fase 3B.1: godkjent processingkontrakt v1

Den isolerte [fase 3B.1-spiken](../status/PHASE_3B1_IMAGE_RENDITION_SPIKE.md) målte Pillow og pyvips/libvips på syntetiske fixtures. Prosjekteier har godkjent følgende tekniske retning for første produksjonsrettede MVP. Godkjenningen gjør valgene til arkitekturgrunnlag; den aktiverer ingen runtimekode eller produksjonsavhengighet.

#### Bibliotek og adaptergrense

- Pillow er primært bildebehandlingsbibliotek for første MVP og skal ligge bak en liten intern adapter.
- Domene, storagekontrakt og API skal ikke avhenge av Pillow-spesifikke typer.
- pyvips/libvips beholdes som dokumentert ytelsesalternativ og vurderes på nytt hvis representative batchmålinger viser at Pillow ikke møter senere godkjente ressursgrenser.
- ADR-et låser ikke en bestemt Pillow-versjon. Produksjonsversjonen pin-nes og verifiseres når avhengigheten faktisk innføres.
- Produksjonskode skal ikke mutere globale `Image.MAX_IMAGE_PIXELS` per request eller parallell behandlingsoperasjon. Pixelbeskyttelsen må håndteres trådsikkert og prosessfast eller gjennom en isolert worker-/valideringsstrategi.

#### Inputformater

Første MVP støtter bare statiske JPEG-, PNG- og WebP-filer. Følgende avvises forklarlig:

- SVG
- AVIF som påkrevd inputformat
- GIF
- HEIC/HEIF
- TIFF
- ukjente formater
- animerte WebP-filer

Ingen animert fil skal stilltiende behandles som første frame. Rå SVG skal ikke serveres offentlig. SVG kan vurderes senere gjennom en separat, sikker rasterizerspike og skal vurderes på nytt før storstilt logoimport eller legacyovergang hvis kartleggingen viser at mange offisielle logoer bare finnes som SVG.

#### Output, renditions og immutable keys

Processing profile v1 er:

| Variant og innhold | Størrelse | Output |
| --- | --- | --- |
| Foto `square` | 512 × 512 | WebP, quality 82 |
| Foto `landscape` | 800 × 450 | WebP, quality 82 |
| Foto `share` | 1200 × 630 | JPEG, quality 85, ikke-progressiv |
| Logo med alpha | relevant variantstørrelse | PNG |
| Dynamisk fallback `square`/`landscape` | relevant variantstørrelse | WebP |
| Fallback `share` | 1200 × 630 | JPEG |

Format, encoderinnstillinger, source checksum, fit, normalisert fokus, normalisert Foto-zoom, renditionvariant og processing-version inngår i immutable key. Endring av en av disse verdiene gir ny key og overskriver aldri historisk output. AVIF er utsatt og er ikke et MVP-krav.

Offentlige renditions følger denne godkjente MVP-kontrakten:

```text
gyldig kilde
    → eksplisitt normalisering eller konvertering til sRGB
    → crop og resize
    → offentlig rendition uten innebygd ICC-profil
```

- Embedded sRGB behandles gjennom den samme normaliseringskontrakten.
- Gyldig embedded non-sRGB konverteres eksplisitt til sRGB før crop og resize.
- Untagged input behandles som antatt sRGB og registreres eksplisitt som `untagged`/`assumed-sRGB`; dette er ikke automatisk hard fail.
- Korrupt eller uleselig ICC-profil skal ikke ignoreres. Den gir en kontrollert teknisk feil og krever en annen eller reparert kilde.
- Sensitive kildeprofiler kopieres ikke til offentlige renditions.

Profilfri sRGB-normalisert output er valgt for MVP fordi den representative kjøringen ga byte-deterministisk output. En fast innebygd standardprofil er ikke valgt. Dersom den senere vurderes, kreves en separat deterministisk test av en kanonisk profil uten variabel metadata.

#### Fit, fokus, oppskalering og metadata

- Logo bruker `contain` og skal ikke kuttes eller strekkes.
- Foto bruker `cover`, lagret normalisert fokuspunkt og zoom; sentrum og `1.0000` er standard.
- EXIF-orientering skjer før crop.
- Sensitive metadata fjernes fra offentlige renditions.
- Ingen kildepiksler skaleres opp automatisk. For lavt reelt cropområde håndteres med bedre kilde, annet bilde eller kontrollert komposisjon/fallback, ikke et uskarpt offentlig bilde.
- Privat original følger den separate storage- og retensjonskontrakten.

#### Tekniske grenser og kvalitetsklassifisering

- Maksimal kildefilstørrelse på 15 MiB beholdes som konfigurerbar standardverdi.
- Maksimal decoded pixelmengde er 36 megapiksler som konfigurerbar MVP-standard. Dette er den laveste representative kandidatgrensen som beholdt alle 24 fixtures, ikke en universelt optimal grense. Den kan revurderes ved ny evidens.
- Det finnes ingen universell minimumsbredde eller minimumshøyde.
- Ingen kildepiksler skaleres opp automatisk.
- Logo bruker `contain` og skal aldri crop-es. Foto bruker `cover` og vurderes separat for `square`, `landscape` og `share` ut fra faktisk cropområde og scaling margin.
- Alle obligatoriske renditions må kunne produseres uten oppskalering før et asset er klart for godkjenning. En manglende obligatorisk rendition gjør assetet `NOT READY FOR APPROVAL`, men sletter eller avviser ikke nødvendigvis kildekandidaten; flyten skal be om bedre kilde, annet bilde eller fallback.

Edge variance og blockiness er informational/advisory. Tydelige outliers kan gi warning, og en outlier kombinert med liten kilde, synlig komprimering, mye tekst, vannmerkerisiko eller et annet visuelt problem kan trigge manual review. Ingen numerisk edge-variance-, blur- eller blockinessgrense er automatisk hard fail, og prototypeintervallene fra fase 3B.1 er ikke produksjonsgrenser.

Mye internt logowhitespace kan gi warning og manual review, men whitespace alene er ikke hard fail. Numerisk whitespaceprosent er ikke alene en godkjenningsregel; faktisk lesbarhet og presentasjon ved relevante UI-størrelser er avgjørende.

Tekniske readiness-feil holdes adskilt fra subjektiv bildekvalitet. Decodefeil, unsupported eller ugyldig input, en korrupt/uleselig ICC-profil som ikke kan behandles etter kontrakten, og en manglende obligatorisk rendition under no-upscale-kontrakten kan blokkere teknisk readiness. Dette er ikke en vurdering av om bildet er pent eller stygt.

#### Fase 3B.1R: representativ kvalitetsvalidering gjennomført

[Fase 3B.1R](../status/PHASE_3B1R_REPRESENTATIVE_QUALITY_HARNESS.md) kjørte 24 lokalt lagrede, rettighetsavklarte fixtures gjennom den isolerte harnesskontrakten og manuell visuell review. Private kilder, privat manifest og visuell/full evidens forblir Git-ignorert; bare anonymiserte aggregater dokumenteres.

Den representative evidensen viste at 20 MP avviste to nyttige kilder, mens 36, 50, 64 og 100 MP beholdt alle 24. Ingen edge-variance-, blockiness- eller whitespaceverdi korrelerte stabilt nok med visuell kvalitet til automatisk hard fail. Profilfri output etter verifisert sRGB-konvertering var byte-deterministisk; kandidaten med generert standardprofil hadde identiske dekodede piksler, men var ikke byte-deterministisk.

Prosjekteier godkjente 2026-08-07 grensene og klassifiseringene i dette punktet. Fase 3B.1R er dermed **GJENNOMFØRT / GODKJENT**, uten at hele fase 3B eller CRM-runtime er ferdig.

#### Fase 3B.2: teknisk gjennomført storage-, takedown- og restoreprototype

Den isolerte [fase 3B.2-spiken](../status/PHASE_3B2_STORAGE_RESTORE_SPIKE.md) har testet:

- separate private/public `STORAGES`-aliaser uten å endre default storage for eksisterende import-/eksportfiler
- lokal filesystemreferanse og én disponibel S3-kompatibel testbackend
- immutable renditionkeys fra processing profile v1
- private originaler og offentlige renditions
- allowlistede og absolutte media-origins
- origin-sletting, purge/takedown og ny offentlig key ved restore
- en append-only-orientert deny-journalprototype som vinner over eldre database-/object-backup
- direkte renditionbackup mot deterministisk regenerering
- statisk nød-fallback ved storage- eller rendererfeil

Spiken er prototypeevidens, ikke runtimeimplementering. Den har ikke opprettet CRM-bildemodeller, migrasjoner, aktive API-ruter, OpenAPI-schema, Editor, PUBLIC, selection-concurrency, Import 2.0-integrasjon, bakgrunnskø eller stagingdeploy. De godkjente beslutningene som følger av evidensen står i punkt 24.

### 24. Fase 3B.2: godkjent storage-, delivery-, takedown- og restorekontrakt

Følgende prinsipper ble godkjent av prosjekteier 2026-08-01. De er arkitekturgrunnlag for senere leveranser, men er ikke implementert i CRM-runtime.

#### To-key-kontrakt

Det skal være et uttrykkelig skille mellom:

1. **Processing artifact identity:** deterministisk identitet for prosesserte bildebytes basert på source checksum, processing-version, format, encoderinnstillinger, variant, fit, normalisert fokus og canonical render config.
2. **Public release identity:** en separat immutable release identity for én konkret offentlig publiseringsrevisjon av artifactet.

En ny offentlig release får alltid ny identity og public key. En gammel public key overskrives eller gjenbrukes aldri. Restore etter takedown bruker ny public release identity, også når den gjenbruker nøyaktig samme artifact-bytes uten ny encoding.

Fase 3B.3 fastsetter den eksakte public release identity- og key-kontrakten i punkt 25. Produksjonen bruker ikke prototypens `public/<tenant>/<actor>/r<n>/...` eller selection-revisjon som release identity.

#### Aktiv public rendition-storage

Første MVP skal bruke et dedikert host-persistent public rendition-område eller et likeverdig lokalt namespace med immutable release keys og uten offentlig tilgjengelig filhistorikk. Samme public key kan ikke overskrives med andre bytes, gamle public release keys gjenbrukes aldri, takedown fjerner eller blokkerer den konkrete releasen, og autorisert restore oppretter en ny release key.

Historiske public bytes skal ikke være tilgjengelige gjennom den lokale media-originen. Dersom et S3-kompatibelt namespace senere innføres, skal historiske bytes heller ikke være tilgjengelige gjennom `versionId` eller en tilsvarende offentlig mekanisme. En bucket med suspended versioning skal da ikke automatisk behandles som aldri-versioned; prosjektet må bruke et nytt dedikert delivery-namespace, permanent fjerne historiske versjoner og bevise at de ikke kan nås, eller dokumentere en leverandørmekanisme med tilsvarende sikker takedownadferd.

#### Public delivery er ikke det samme som public bucket

«Public storage» beskriver offentlige rendition-bytes, ikke et krav om anonym object-storage-bucket. Godkjent første MVP er host-persistent lokal storage bak kontrollert same-origin- eller lokal media-origin-serving uten eksponert intern filesystempath.

Klienter bruker en kontrollert `PUBLIC_MEDIA_ORIGIN` eller same-origin-kontrakt. Dersom objektlagring/CDN senere innføres, skal intern provider-endpoint fortsatt ikke eksponeres, offentlige URL-er skal ikke inneholde credentials eller signerte queryparametere, og valgt provider/CDN må støtte origin-delete og kontrollert purge. Fase 3B.2-labens anonyme Moto-GET er bare protokollevidens og er ikke valgt produksjonsmodell.

#### Private originaler

I første MVP ligger private originaler i et separat host-persistent område med egne Django-storagealiaser, filesystempermissions og rollebeskyttet administrativ tilgang. Ingen offentlig mediaresolver kan returnere private originaler. Backup-/restore-gaten gir katastrofegjenoppretting; eksakt lokal historikk-/immutabilitymekanisme fastsettes sammen med media-runtime og retensjonsreglene.

Dersom ekstern objektlagring senere innføres, må faktisk provider bevise IAM og public-access-block også for eksplisitt `versionId`. Moto er ikke tilstrekkelig sikkerhetsbevis. Provider, region, ekstern IAM, bucket-policy/public-access-block, signerte URL-er, KMS, Object Lock og provider-spesifikk versioning blir først porter når en slik migrering er godkjent på grunn av dokumentert behov.

#### Hybridbackup

Godkjent backupretning omfatter:

- private originaler, source checksum og canonical metadata
- eksakt processing-version og processing profile
- nødvendige selection-/release-referanser
- aktive public rendition-bytes
- nødvendig audit- og approvalhistorikk
- deny-journal i separat backup- og failure-domain

Deterministisk regenerering beholdes som sekundær reparasjonsvei og er ikke eneste katastrofeplan. Byte-identisk regenerering kan avhenge av at gammel Pillow-, encoder-, wheel- og processingprofil fortsatt er tilgjengelig; aktive public bytes beholdes derfor for rask og eksakt restore. ADR-008 har valgt stabil lokal Borg `>=1.2.8` og `<1.3.0` med remote path `borg-1.2` til separat Hetzner Storage Box, 14 daglige, 8 ukentlige og 12 månedlige arkiver og obligatorisk restore-gate. Faktiske RPO-/RTO-målinger gjenstår; ekstra regionredundans er bare en senere behovsdrevet hardening.

#### Restore-gate

Restore skal ikke automatisk republisere eldre public objekter. Godkjent konseptuell rekkefølge er:

1. restore private originaler og canonical metadata
2. restore rendition-bytes til et ikke-offentlig restore-/karanteneområde
3. last inn nyeste autoritative deny-journal
4. replay og materialiser deny-state
5. reconcile restaurert state, keys og checksums mot deny-state
6. slett eller blokker denied releases
7. verifiser referanseintegritet og checksums
8. åpne public serving
9. bruk nye release keys ved ny autorisert publisering

Når journal eller reconciliation mangler, er korrupt, er uferdig eller har ukjent cursor/integritet, skal public image projection returnere statisk Kreative Norge-fallback. Et eldre app- eller databasesnapshot kan aldri vinne over en nyere deny-hendelse.

#### Varig deny-journal

Takedown-/deny-sporet er append-only eller WORM-orientert, har eget backup- og failure-domain og rulles ikke automatisk tilbake med app-state eller databasebackup. Event-ID-er er idempotente, gamle hendelser redigeres ikke, og restore/gjenoppretting registreres som ny kompenserende hendelse.

Manglende eller korrupt autoritativ journal feiler lukket til fallback. Journalen skal replikeres, overvåkes og ha schema-version. Normal takedown bruker deny-first: varig deny-registrering før origin-delete og purge.

Fase 3B.2 lot permanent journalteknologi stå åpen. ADR-009 har senere valgt en lokal append-only SQLite-ledger med et restore-sikkert WORM-orientert off-server anker. JSONL-filen i fase 3B.2 er fortsatt bare domene- og replaybevis og beviser ikke WORM, tamper evidence, tilgangskontroll eller katastrofegjenoppretting.

#### Journal og runtime read-model

Den append-only journalen er autoritativ. Produksjonsruntime kan bruke en materialisert deny-indeks/read-model med kjent journalcursor eller tilsvarende. Etter restore replayes journalen og read-modelen avstemmes før public serving åpnes. Ukjent eller stale sikkerhetstilstand gir fallback.

Eksakt read-model-, cache- og cursorimplementasjon avgjøres senere.

#### Deny-scopes

Produksjonsmodellen skal senere støtte minst:

- public release deny for én konkret release key
- tenant-scopet checksum deny som hindrer stille reupload/godkjenning av samme forbudte bytes i samme tenant
- global checksum deny som separat plattform-superadminhandling med eget scope og audit uten informasjonslekkasje mellom tenants

Fase 3B.2 beviste bare public release deny. At journalhendelsen inneholder artifact- og source-checksum betyr ikke at checksum-deny er implementert eller bevist. Checksum-deny implementeres først i en senere backendfase med egne tenant-, rolle- og personverntester.

#### Purge

Origin-delete alene er ikke nok. Relevant lokal response-/media-cache skal purges; purge er idempotent; retrybare og permanente feil skilles; request-/hendelses-ID registreres; og takedown er ikke komplett før nødvendig purge og verifikasjon er registrert. Fallback brukes mens public levering har ukjent sikkerhetstilstand. Dersom CDN senere innføres, gjelder den samme kontrakten også providerens purge-API og propagation.

`RecordingPurgeProvider` og cache-simulatoren er domeneprototyper. De beviser ikke faktisk provider-API, propagation, rate limits, partial failure eller autentisering.

#### Moto

Moto Server 5.2.2 beholdes bare som dokumentert emulator for fase 3B.2-evidensen. Moto er ikke produksjonsleverandør, IAM-sikkerhetsbevis, bevis for bucket-policy conditions eller bevis for privat historisk versjonstilgang, og skal ikke innføres i CRM-runtime eller staging.

Det observerte gapet der unsigned GET med eksplisitt `versionId` nådde en eldre privat versjon, beholdes som evidens for en betinget fremtidig provider-gate dersom objektlagring tas opp igjen; det blokkerer ikke den lokale MVP-en.

#### Godkjent MVP-drift og fortsatt åpne valg

ADR-008 velger Hetzner one-server storage, stabil lokal Borg `>=1.2.8` og `<1.3.0` med remote path `borg-1.2` mot separat Storage Box, retention 14/8/12 og en obligatorisk restore-gate. Repo-grunnmuren er forberedt, men den eksterne kjeden må være ACTIVE før fase 3C kan skrive nye varige bildefiler.

Fase 3B.3-A har implementert release-aggregate- og canonical key-domenegrunnmuren uten storage- eller public runtime. ADR-009 har senere besluttet lokal append-only SQLite-ledger, restore-sikkert off-server anker, separat public delivery-root, create-only/no-clobber materialisering, kontrollert serving, origins, projection/API-kontrakt og fasegater frem til takedown. 3E.1A-ledgeren/off-serverankeret er `ACTIVE` i staging og 3E.1B-kontrakten er godkjent, mens materialisering, serving, projection/API og takedown fortsatt er uimplementert. Backupkjeden er aktivert og restore-smoke er målt, men full katastrofe-RTO er fortsatt åpen. S3-/CDN-provider, region, ekstern IAM, bucket-policy, KMS, Object Lock og provider-spesifikk purge/`versionId`-verifikasjon er utsatt og blir bare en betinget senere gate ved dokumentert behov.

### 25. Fase 3B.3: godkjent public release identity og key-kontrakt

Prosjekteier godkjente 2026-08-07 følgende produksjonsrettede identitets- og nøkkelkontrakt. Beslutningen presiserer to-key-kontrakten i punkt 24, men aktiverer ingen public image runtime.

#### Separat public release identity

Public release identity er forskjellig fra både intern processing artifact identity og `OrganizationImageSelection.revision`.

- Hver nye offentlige bilde-release får en tilfeldig UUIDv4 som immutable `release_id`.
- UUID-en er en offentlig identifikator, ikke et autentiserings- eller bearer-token.
- Selection-revisjon, database-PK, tenant-ID og Organization-ID er ikke release identity og inngår ikke i public key.
- Replacement, restore og senere autorisert republisering får alltid ny release-ID, også når de bruker samme `ImageRenditionSet` og eksakt samme artifact-bytes.
- En tidligere release-ID eller public key reassosieres, frigjøres eller tas aldri i bruk igjen.
- Idempotent gjenoppretting av samme fortsatt autoriserte release kan skrive tilbake samme forventede bytes under samme key etter full restore-/deny-reconciliation. Dette er ikke en ny release eller reaktivering av en gammel denied key.

`OrganizationImageSelection.revision` er fortsatt selectionens concurrency- og historikkidentitet i den aktive databasen. Den kan ikke være public release identity fordi en eldre databasebackup kan miste nyere revisjoner og senere beregne samme `MAX(revision) + 1` på nytt.

#### Canonical relative public release key

Public rendition-storage bruker denne relative key-kontrakten:

```text
releases/<release_uuid>/<variant>.<ext>
```

Eksempel for R1:

```text
releases/5db81680-4557-4376-b213-51d90939c425/square.webp
releases/5db81680-4557-4376-b213-51d90939c425/landscape.webp
releases/5db81680-4557-4376-b213-51d90939c425/share.jpg
```

Hvis R2 senere gjenbruker de eksakt samme tre `ImageRendition`-radene og artifact-bytes, får den likevel en ny release-ID og nye keys uten ny encoding:

```text
releases/a01d813f-9e9b-4f73-97a1-3ac8f4cb103a/square.webp
releases/a01d813f-9e9b-4f73-97a1-3ac8f4cb103a/landscape.webp
releases/a01d813f-9e9b-4f73-97a1-3ac8f4cb103a/share.jpg
```

`release_uuid` er canonical lowercase RFC 4122 UUIDv4. `variant` er nøyaktig `square`, `landscape` eller `share`. Canonical extensionmapping er `jpeg` → `jpg`, `png` → `png` og `webp` → `webp`.

Den lagrede keyen skal være eksakt resultat fra den interne canonical builderen, semantisk:

```text
public_storage_key == build_public_release_key(
    release.release_id,
    variant,
    output_format,
)
```

Caller leverer aldri en fri `public_storage_key`. Pattern- eller regexmatch alene er ikke tilstrekkelig: feil release-UUID, variant eller extension skal avvises selv om teksten ellers ligner en canonical key. Dersom denne cross-row-likheten ikke kan uttrykkes forsvarlig som databaseconstraint, er den en obligatorisk domenetjenesteinvariant.

Keyen inneholder bare release-ID, variant og canonical extension. Den inneholder ikke tenant-ID/-slug, Organization-ID/-navn/-slug/-nummer, selection-revisjon, rendition-sett-ID, artifact storage key, artifact-checksum/-hash, processing-version, request host, filesystempath, credentials, tokens, queryparametere eller andre mutable displayverdier. Disse verdiene kan finnes som interne relasjoner og metadata i databasen.

Public URL bygges senere ved å kombinere den relative keyen med en allowlistet, miljøkonfigurert public media-origin. Request-host, intern filesystempath og signerte eller sensitive queryparametere kan aldri påvirke keyen.

Prototypens `public/<tenant>/<actor>/<release>/<variant>-<artifact-hash>.<ext>` videreføres derfor bare konseptuelt med separat release-segment og variant. Tenant-, actor- og artifact-hashsegmentene fjernes, og sekvensiell `r<n>` erstattes av UUIDv4. Artifact-checksum forblir intern fordi den ikke er nødvendig for public key-unikhet og kan synliggjøre identiske bytes på tvers av tenants.

#### Organization-typed public release aggregate

Første implementering skal være additiv, organization-typed og uten `GenericForeignKey`. Modellnavnene og feltene nedenfor er anbefalt retning for fase 3B.3-A, ikke en beslutning om eksakt schema:

- `OrganizationImageRelease`, med intern vanlig PK, globalt unik immutable UUIDv4 `release_id`, beskyttet `ForeignKey` til den konkrete `OrganizationImageSelection`, eksplisitt key-schema-version og opprettelsestidspunkt
- `OrganizationImageReleaseRendition`, med beskyttet kobling til releasen og én konkret `ImageRendition`, samt immutable snapshots av variant, outputformat, artifact-checksum og eksakt public storage key

Relasjonen er:

```text
Organization
    → OrganizationImageSelection
    → ImageRenditionSet
    → ImageRendition / intern artifact identity

OrganizationImageSelection
    → OrganizationImageRelease med UUIDv4
    → én OrganizationImageReleaseRendition og public key per nødvendig variant
```

Den normative mappingen er:

- tenant og `Organization` fastsettes fra den konkrete `OrganizationImageSelection` når releasen opprettes og inngår deretter i den frosne historiske mappingen; de eksponeres ikke i keyen
- `OrganizationImageRelease` peker til selectionen og bærer release-ID-en, men endrer ikke selectionens revisjon eller livssyklus
- selectionen peker som i dag til nøyaktig ett `ImageRenditionSet` for en asset-selection
- hver `OrganizationImageReleaseRendition` peker til én `ImageRendition` fra akkurat dette settet og lagrer variant-/format-/checksum-snapshot og den canonical public keyen
- artifact identity og bytes forblir eid av `ImageRendition`; releasekoblingen er en immutable public delivery-mapping, ikke en ny encoding eller kopi-identitet

Når releasen opprettes, fryses dens historiske mapping til tenant, `Organization`, `OrganizationImageSelection`, `ImageRenditionSet` og de konkrete `ImageRendition`-/artifact-identitetene. En senere endring av en referert selection eller annen levende domenerad kan aldri endre hva en eksisterende release representerer. Denne no-reassociation-invarianten er besluttet, mens fase 3B.3-A velger om den bevises med immutable identitetsfelt/snapshots på release aggregate, beskyttede immutable relasjoner eller en annen dokumentert mekanisme. Valget innfører ingen ny selection-livssykluskommando.

Release aggregate kan dermed peke mot eksisterende immutable rendition-bytes uten ny encoding. Fallback-selection får ikke en asset-release i denne kontrakten; systemfallbackens endelige public key-struktur er en separat senere gate.

Nødvendige databaseconstraints er minst:

- global unikhet for `release_id`
- global unikhet for hver `public_storage_key`
- unik `(release, variant)` og `(release, rendition)`
- gyldig key-schema-version, variant, outputformat og ikke-tomme canonical keys/checksums
- `PROTECT` fra release til selection og fra release-rendition til den konkrete renditionen for å blokkere sletting av referert historikk

`PROTECT` blokkerer sletting, men hindrer ikke alene ForeignKey-reassosiering eller endring av andre felt. En kort, atomisk domenetjeneste skal i tillegg kontrollere at selection er en asset-selection, at selection og rendition-sett tilhører samme organization-/tenant-scope, at alle tre renditions kommer fra selectionens eksakte sett, at snapshotfeltene matcher renditionen, og at hver key er eksakt builder-resultat for release-ID, variant og outputformat. Tjenesten skal opprette et komplett, konsistent release aggregate eller ingenting; en delvis release avvises. Vanlige ForeignKeys og check constraints kan ikke alene bevise disse cross-table-invariantene.

[ADR-009s senere 3E.1B-presisering](ADR-009-PUBLIC_IMAGE_RUNTIME_RELEASE_DELIVERY_AND_RESTORE_SAFE_DENY_STATE.md#5-materialisering-og-release-livssyklus) tillater maksimalt én public release per selection-revisjon. Retry skal gjenbruke samme permanent reserverte UUID og keys; senere autorisert republisering går via en ny selection-revisjon og får ny UUID/key uten å omskrive tidligere selections eller releases. Fase 3B.3-A-modellen beholdt en vanlig ForeignKey og håndhever ennå ikke denne idempotency-grensen entydig; eksakt ledger-/databasehåndheving er et 3E.1B-implementeringsspørsmål. Hvilken release som er `reserved`, `active`, `retired` eller `denied` avgjøres av safety-ledgeren, ikke av en ny selection-status eller en parallell PostgreSQL lifecycle-status.

Release aggregate og release-renditions er immutable gjennom støttede skriveruter. Ordinær cleanup kan ikke slette eller frigjøre en release-ID. Retention, eventuell kontrollert anonymisering og sterkere database-WORM/trigger er separate senere gater.

#### Varig reservasjon, no-clobber og idempotens

UUIDv4 gir svært sterk praktisk unikhet, men no-reuse-kontrakten bygger ikke bare på kollisjonssannsynlighet.

- En release-ID og dens keys reserveres varig før de kan brukes offentlig.
- Reservasjonen slettes ikke ved feil, replacement, restore, takedown eller ordinær cleanup; en avbrutt reservasjon er permanent brukt.
- Den senere autoritative release-/deny-journalen eller et likeverdig separat failure-domain skal kjenne alle reserverte release-ID-er og keys, ikke bare denied keys.
- Manglende, korrupt eller stale reservation-/deny-state feiler lukket og kan ikke produsere eller aktivere public release.
- Samme release key med samme forventede bytes kan behandles som idempotent retry.
- Samme selection-revisjon gjenbruker samme reservation, release-ID og keys ved retry og kan ikke opprette en ny release med ny UUID.
- Samme release key med andre bytes er en hard konflikt.
- Public bytes skrives create-only/no-clobber og overskrives aldri stilltiende.
- En UUID-/key-kollisjon mot varig reservasjon, database, storage eller deny-state avvises fail-closed; en ny UUID må reserveres.
- En release/key som deny-journalen kjenner som denied kan aldri aktiveres igjen.

Ved restore av en eldre database skal nyeste reservation-/deny-state lastes og reconciles før public serving. En restaurert selection-revisjon, PK eller annen databaseidentitet kan aldri brukes til å beregne eller reaktivere en tidligere release key. Takedown/deny vinner alltid over restore.

Disse detaljene var ikke besluttet i fase 3B.3. ADR-009 har senere fastsatt journaltype, restore-safe anker, materialiseringsrekkefølge og faseinndeling. 3E.1A-ledgeren og off-serverankeret er `ACTIVE` i staging, og 3E.1B-presiseringen fastsetter lokal Unix-socket/systemd-bro, selection-revisjonsidempotens og cleanupgrensen. Eksakt socket-/databasehåndheving, delivery-runtime, cacheverdier og senere operatørprosedyrer skal fortsatt bevises i riktige 3E-leveranser.

#### Livssyklusvirkning uten ny selection-kommando

- Replacement oppretter ny selection-revisjon og senere en ny release-ID; gammel release forblir permanent reservert.
- Removal-to-fallback oppretter som i dag en fallback-selection og ingen ny asset-release; gammel release forblir permanent reservert.
- Restore oppretter som i dag en ny asset-selection-revisjon og senere en ny release-ID, også med samme rendition-sett og bytes.
- Senere formell takedown lar deny-state og public projection gå til fallback; gammel release-key forblir permanent denied.
- Senere autorisert republisering bruker ny release-ID og nye keys. Den gjenbruker artifacts uten re-encoding når bytesene fortsatt er gyldige og autoriserte.

Fase 3B.3 legger ikke til en selection-status eller selection-livssykluskommando. Dagens locking-, replacement-, removal-to-fallback- og restorekommandoer forblir uendret.

#### Avviste alternativer

- **Selection-revisjon eller database-PK i key:** avvist fordi eldre database-restore kan gjenta verdien.
- **Tenant-/Organization-segmenter:** avvist fordi de ikke trengs for global unikhet og kan være mutable, gjenbrukbare eller unødig eksponerende.
- **Artifact-hash i public key:** avvist fordi release-ID gir cacheidentitet og hashen kan synliggjøre like bytes på tvers av tenants.
- **Public release-ID som felt direkte på selection:** avvist fordi public release er en separat delivery-/reservasjonsidentitet og selection-livssyklusen er komplett.
- **UUIDv4 uten varig reservasjon og no-clobber:** avvist fordi streng no-reuse etter database-restore også krever autoritativ kunnskap om tidligere brukte keys.
- **Generisk release med `GenericForeignKey`:** avvist i første implementering av samme tenant- og referanseintegritetsgrunner som den typed selection-modellen.

#### Trinnvis implementeringsplan

**Leveranse 3B.3-A – additiv release-domenegrunnmur:**

- legg til de organization-typed release-modellene, constraints og en reverserbar schema-migrasjon
- legg til en ren canonical key-builder og en kort release-aggregate-tjeneste uten storage-, journal-, API- eller selection-runtimekobling
- behold `IMAGE_ASSET_FEATURE_ENABLED=False`

Akseptansekriterier og tester:

- migrasjon frem og tilbake bevarer alle eksisterende modeller og data
- UUID-, key-, release-/variant- og release-/rendition-unikhet håndheves i PostgreSQL
- nøyaktig square/landscape/share, canonical extension og cross-tenant/-set-avvisning testes
- lagret public key er alltid internt generert og eksakt builder-resultat; fri caller-key, feil release-UUID, variant eller extension og delvis/inkonsistent aggregate avvises
- historisk release-mapping kan ikke omskrives gjennom vanlig update, ForeignKey-reassosiering, bulk update, upsert/update-conflict eller relevant delete
- revision, database-ID-er, host, hash, credentials og mutable verdier kan ikke inngå i keyen
- samme artifacts kan mappes til to forskjellige release-ID-er uten encoder-, renderer-, storage- eller nettverkskall
- modell-/settings-load oppretter ingen mapper eller filer og endrer ingen publiseringsflagg

Rollback: feature forblir av; additive tabeller kan migreres tilbake så lenge ingen release-reservasjoner er opprettet. Når reelle reservasjoner finnes, brukes fremoverrettet migrasjon og data slettes ikke.

**Erstattet av fase 3E.1A–3E.1B – varig reservation-/deny-integrasjon og materialisering:**

- følger ADR-009s godkjente SQLite-ledger, restore-sikre off-server anker, cursor/failure-domain og separate public delivery-root
- reserverer release-ID og keys varig før DB-/filmaterialisering og støtter idempotent replay/reconciliation
- simulerer gammel database + nyere reservation-/deny-state og beviser at gammel key aldri regenereres eller aktiveres

Rollback: public projection forblir eller går fail-closed til fallback; reservations- og deny-historikk slettes aldri.

**Senere materialisering, serving og projection:**

Public filskriving, lokal serving, nginx/Caddy, cache/purge-runtime, takedown-/publish-saga, unpublish-semantikk, systemfallback-key, API-schema, public projection, sync/async-grense, observability og full disaster-RTO forblir egne beslutnings- og implementeringsgater.

## Begrunnelse

Denne ansvarsdelingen skiller:

- oppdagelse fra varig lagring
- teknisk validering fra redaksjonell godkjenning
- tenant-eid asset fra aktørspesifikk selection
- privat original fra offentlig rendition
- bildevalg fra aktør- og kontaktpublisering
- operasjonell importlogg fra varig approvalhistorikk
- intern proveniens fra offentlig presentasjon

Typed selection gjør én aktiv aktørkobling eksplisitt uten å gjøre assetet avhengig av at aktøren allerede finnes. En felles projection gir samme bildevalg til Editor, PUBLIC, API og deling. Private originaler og immutable renditions gir kontroll over kvalitet, cache og senere bearbeiding, mens append-only events gjør approval, replacement og takedown etterprøvbart.

## Avviste alternativer

### Fortsette med eksterne URL-er som aktiv bildekilde

Avvist fordi hotlinking, ekstern endring, faviconfallback og manglende teknisk kontroll ikke kan gi en stabil eller etterprøvbar offentlig kontrakt.

### Eie `ImageAsset` direkte fra `Organization`

Avvist fordi et asset må kunne godkjennes før en ny importaktør finnes, og fordi storage-/assetlivssyklus ikke skal blandes med aktørraden.

### Legge fil, URL og godkjenningsfelt direkte på `Organization`

Avvist fordi dette blander bytes, presentasjon, approval, historikk og fallback i én modell og gjør replacement/takedown vanskelig å spore.

### Bruke `GenericForeignKey` eller én generell selection for alle objekttyper

Avvist i første implementering fordi det svekker referanseintegritet, permissions og klare tenantinvarianter. Personer og prosjekter kan få egne typed modeller senere.

### Innføre `ImagePlacement` i første MVP

Avvist inntil prototypen viser et konkret behov. Fit og ett fokuspunkt på selection er tilstrekkelig start.

### Gjøre kreditering og juridiske felter obligatoriske

Avvist fordi standardflyten skal være rask og fordi manglende kreditering ikke er det samme som et kjent krediteringskrav.

### La AI, Open Graph eller import godkjenne og erstatte automatisk

Avvist fordi relevans, rettigheter og replacement krever eksplisitt menneskelig beslutning. Automatisering kan finne og rangere kandidater, ikke låse eller publisere dem.

### Bruke uidentifisert containerlag som varig staging-/produksjonslager

Avvist fordi container-recreate kan fjerne filer. ADR-008 godkjenner lokal filesystemstorage når den har eksplisitte Django-aliaser, host-persistente paths, tilgangsgrenser og verifisert off-server backup.

### Lagre bildefiler som databaseblob

Avvist fordi det binder databasebackup, levering og bildebehandling sammen og gjør objektlagring/CDN vanskeligere.

### Bruke pyvips/libvips som primær backend i første MVP

Utsatt, ikke permanent avvist. Fase 3B.1 målte omtrent dobbelt så lav veggtid for de syntetiske arbeidslastene, men Pillow bestod den samme avgrensede kontrakten med en mindre operasjonell dependencyflate. Adaptergrensen og benchmarkkontrakten beholdes slik at pyvips kan overta uten å endre domene, storage eller API hvis representative batchmålinger senere tilsier det.

## Konsekvenser

### Positive konsekvenser

- samme aktive bildevalg i Editor, PUBLIC, API og deling
- tenant-eierskap og tydelig referanseintegritet
- privat original og kontrollerte offentlige renditions
- rask, versjonert og etterprøvbar godkjenning
- eksplisitt låsing, replacement, restore og takedown
- forutsigbar fallback uten ekstern avhengighet
- additiv API- og legacyovergang
- klart skille mellom bilder og publiseringsflagg
- grunnlag for senere person-, prosjekt- og Import 2.0-integrasjon

### Kostnader og ulemper

- flere modeller, statuser og permissions
- ny storage-, backup-, restore- og cleanupkontrakt
- en pin-net og verifisert Pillow-avhengighet bak intern adapter når produksjonsimplementeringen starter
- bildebehandling, sRGB-normalisering og teknisk kvalitetskontroll
- større testmatrise for sikker fetch, tenant-isolasjon, kort og responsive varianter
- lokal media-/cachehåndtering ved takedown; eventuell CDN-håndtering bare dersom CDN senere innføres
- midlertidig dual-read/compatibility under legacyovergangen
- ekstra operasjonell kompleksitet rundt retensjon og karantene

### Risiko som skal reduseres i fase 3B

- for høy prosesseringskostnad eller minnebruk på representative batcher
- manglende eller inkonsistent sRGB-normalisering
- lokal storage/serving uten tilstrekkelige permissions, purge eller restore; eventuell senere provider må bevise samme kontrakt
- dårlig kvalitetsterskel som avviser gode logoer eller godkjenner svake bilder
- uklare regler for samme-tenant assetgjenbruk og orphan cleanup
- dynamisk fallback som ikke er stabil eller tilgjengelig
- alias- eller cacheadferd som gjør public API eller takedown inkonsistent

## Implementeringsleveranser og akseptansekriterier

Ingen leveranse under skal starte før gate og stoppunkt for leveransen er godkjent. Leveransene skal være additive og reversible frem til en eksplisitt dokumentert datakontrakt gjør en migrasjon forward-only eller separat legacyopprydding starter. Før en slik grense aktiveres, må pre-deploy-backup tas og verifiseres; feature-off og fremoverrettet retting er deretter operativ rollback.

### Fase 3B: teknisk prototype og kontrakt

**Status:** Fase 3B.1 og fase 3B.2 er teknisk gjennomført som isolerte prototyper, fase 3B.1R er gjennomført og godkjent med representativ kvalitets- og sRGB-evidens, og fase 3B.3 har godkjent eksakt UUIDv4-basert public release identity, canonical key-format og varig reservasjonsinvariant. Fase 3B.3-A har implementert den additive release-domenegrunnmuren uten public runtime. ADR-008s lokale Hetzner storage-/backup-MVP er **ACTIVE**. ADR-009 har flyttet runtimegatene til fase 3E.1A–3E.4; 3E.1A-ledgeren/off-serverankeret er `ACTIVE` i staging og 3E.1B-kontrakten er godkjent, mens materialisering, serving, projection, API/PUBLIC og takedown ikke er implementert.

**Omfang:**

- syntetisk fixture-sett for logo, foto, transparens, EXIF, SVG, små/store, korrupte og uønskede plattformbilder i fase 3B.1
- rettighetsavklart, representativt bildesett og fargeprofiler i fase 3B.1R
- spike av bildebehandlingsbibliotek, format, kvalitet, ressursbruk og deterministic renditions i fase 3B.1
- prototype av contain, cover, ett fokuspunkt og fallback i godkjente kortmål
- spike av separate `STORAGES`-aliaser for private originaler og offentlige renditions uten å endre default storage for eksisterende import-/eksportfiler
- spike av absolutte URL-er, purge, response-cacheinvalidering, restore og varig deny-journal
- API-schema, aliasmapping, autoritative public/media-origins, selection-concurrency, processing-version og cache-key
- anbefaling om sync/async-grense, cleanupmekanisme, assetgjenbruk og orphan retention

**Akseptansekriterier:**

- tekniske alternativer og målinger er dokumentert uten å omtale prototypen som produksjonsklar
- logo kuttes ikke, foto respekterer fokuspunkt og ingen variant strekkes
- sharevariant er 1200 × 630
- fallback finnes i alle tre varianter og har en statisk nødvariant
- private originaler kan ikke nås offentlig
- storageprototypen beviser domenekontrakten for origin-fjerning, recording-purge og gjenoppretting med ny nøkkel; lokal implementasjon må bevise kontrakten før fase 3C, mens faktisk provider-/CDN-adferd bare blir en gate dersom ekstern storage senere innføres
- canonical, `og:url` og public rendition-URL er stabile ved endret request-host og følger konfigurert HTTPS-origin
- backup/restore-kontrakten er prøvd i isolert miljø og reaktiverer ikke en takedown som skjedde etter backup-punktet
- pre-Organization review kan forberede asset, fit, fokus og immutable renditions, og senere commit gjør null renderer-/storagekall
- bildealiasene påvirker ikke eksisterende default-storagefiler for import og eksport
- eksakte åpne valg nedenfor er anbefalt og eksplisitt godkjent før fase 3C

**Testkrav:**

- deterministic filhash eller dokumentert deterministisk variantkontrakt
- ressursgrenser, corrupt input, MIME/bytes-mismatch og decompression-bomb-fixtures
- desktop-/mobilprototyper med lange navn, kommuner, tags og knapper
- minst representative bredder rundt 320, 390, 768 og 1280 px eller en dokumentert likeverdig matrise
- host-header-/proxytest som beviser riktig schema og at vilkårlig host ikke endrer canonical eller public media-URL
- restoretest med eldre database-/object-snapshot og nyere deny-journal
- prepare → create Organization/selection-test med eksplisitt assert på null fil-I/O i commit

**Rollback:**

- isolerte prototyper og prototypeobjekter kan fjernes
- ingen produksjonsdata, aktiv API eller PUBLIC påvirkes

### Fase 3C: additiv backend- og storagegrunnmur

**Omfang:**

- additive modeller, constraints og migrasjoner
- private originaler, renditionstorage og kontrollerte ingesttjenester
- append-only events, versjonert approvaltekst og capability-permissions
- kandidat-, asset-, selection-, rendition-, retention- og takedownkommandoer
- kompatibel deny-guard i dagens legacygetter, aktivt public API og Editor-preview
- feature av; ingen offentlig cutover

**Akseptansekriterier:**

- maksimalt én aktiv selection per aktør håndheves ved concurrency
- asset/fallback-XOR og alle tenantinvarianter håndheves
- private originaler og sensitiv metadata er rollebeskyttet
- redigerer, gruppeadmin, tenant-superadmin, plattform-superadmin og leser følger matrisen
- godkjenning, replacement og restore beholder immutable historikk
- ingen bildekommando endrer publiseringsflagg
- kandidater og filer følger vedtatt retensjon og referansebevisst cleanup
- formell takedown kan ikke omgås med reupload av samme checksum
- tenant A sin checksum-deny påvirker eller avslører ikke identiske bytes i tenant B
- ingen takedownrute er aktiv før legacy og ny projection returnerer fallback for samme deny-status

**Testkrav:**

- migrasjon frem og tilbake på tom testdatabase
- tenant-/rolle-/redaksjonstester, inkludert negative cross-tenant-tester
- SSRF, redirect, timeout, bytes, MIME, decode, format og checksum
- transaksjon, idempotens og concurrent replacement
- retention, actor deletion, archive, tenant-/global checksum-deny, takedown, response-cachepurge og restore

**Rollback:**

- feature og nye skriveruter deaktiveres
- additive tabeller beholdes når reelle events eller filer finnes
- rollback bruker kompenserende events; audit og filer slettes ikke
- PUBLIC fortsetter legacy eller systemfallback uten å eksponere blokkerte bilder

### Fase 3D: Editor-flyt for aktørbilde

**Implementeringsstatus 2026-08-13:** Fase 3D.1 er implementert bak miljøstyrt featuregate med official website/Open Graph-discovery, transient signert kandidat, ephemeral kandidat-preview, valgt 3C.7-processing, intern rendition-preview og eksplisitt first lock/replacement. Den interne host-persistente storage-runtimeen er teknisk aktivert, backup-/restore-verifisert og visuelt godkjent for 3D.1 i staging. Kode-default er fortsatt avslått og public serving er uendret. Fase 3D.2 er gjennomført og merget til `main` med PR #33 og omfatter Brave, limt URL, upload, fokusforvalg, presis X/Y, Foto-zoom, live crop, norske feil og valgfri asset-alttekst. Precision/zoom-oppfølgingen er fullverifisert lokalt, CI-grønn på mergecommiten, live Brave-verifisert og visuelt eiergodkjent i staging. Brave-credentialen ble deretter deaktivert; ordinær Editor-bruk er operativt blokkert frem til sluttbrukeravtalegaten er dokumentert oppfylt. Systemfallback-/historikk-/takedown-UI og den kontrollerte overgangen til public projection er fortsatt ikke implementert og prioriteres etter konkret brukerreise eller nødvendig sikkerhets-/driftsgaranti.

**Omfang:**

- prioritert kandidatfunn fra official/Open Graph via Brave og limt URL til upload; systemfallback forblir et separat selectionvalg
- teknisk status, varsler, kildegrunnlag og previews
- synlig/redigerbar deterministisk Brave-query uten AI og med eksplisitte refinementvalg
- Foto-fokusforvalg, presis X/Y og 100–300 % zoom med felles klient-/servergeometri og autoritative serverrenditions
- «Godkjenn og lås bilde»
- «Godkjenn og erstatt bilde»
- ordinær arkivering, fjerning til fallback, restore og historikk
- forberedt, men deaktivert takedown- og karantenegrensesnitt frem til deny-gaten i fase 3E er grønn

**Akseptansekriterier:**

- standardgodkjenning krever ett tydelig klikk etter ferdig teknisk behandling
- asset-alttekst kan være tom uten skjult fallback; whitespace-only avvises, og systemfallback-selection beholder tekstkravet
- godkjenningstekst versjon og snapshot lagres
- kjent krediteringskrav blokkerer til kravet er løst eller særskilt vurdert
- låst bilde erstattes aldri av bakgrunnsjobb, refresh eller import
- leser kan ikke utføre handlinger eller se sensitiv metadata
- redigerer kan ikke utføre formell takedown
- gruppeadmin, tenant-superadmin og plattform-superadmin følger riktig scope
- Editor-preview bruker den nye projection i shadow/feature-flag-modus
- search/providerdata er transient og oppretter ingen persistent kandidatrad
- takedownhandling er ikke tilgjengelig før legacy HTML, aktivt public API, Editor-preview og ny projection følger samme deny-status

**Testkrav:**

- komponent-, API- og E2E-tester for hele rollematrisen
- concurrent/stale selection ved replacement
- load error til CRM-fallback
- uendrede publiseringsflagg før og etter hver bildehandling

**Rollback:**

- UI og skriveruter kan deaktiveres
- lagrede assets, selections og events beholdes
- aktiv lesing kan gå til systemfallback uten å gjenaktivere blokkert legacybilde
- migrasjon `0027` kan reverseres bare før blank asset-/event-alt finnes; etter første blanke rad er schemaet forward-only
- operativ rollback etter denne grensen er feature-off og fremoverrettet retting; pre-deploy-backup må tas og verifiseres før aktivering, og data omskrives aldri til en skjult aktørnavn-fallback

### Fase 3E: public projection, API, delingsmetadata og kort

**Omfang:**

- én read-only public image projection
- strukturert bildeobjekt og deprecated aliaser
- PUBLIC HTML, canonical, Open Graph og Twitter Card
- square-, landscape- og shareleveranse
- godkjente kortstørrelser, grønne PUBLIC-tags og overflowregler
- aktivering av rolleavgrenset takedown først etter verifisert deny-, origin- og response-cacheguard
- kontrollert cutover per tenant eller feature flag

**Akseptansekriterier:**

- aktivt bilde er alltid CRM-rendition eller systemfallback
- samme selection brukes i Editor, PUBLIC, API og head
- nye og gamle API-felter kommer fra samme resolver
- alle eksterne URL-er er absolutte HTTPS-URL-er
- `og:image` bruker 1200 × 630-sharevariant eller fallback
- intern kilde, approval og privat original eksponeres ikke
- PUBLIC desktopdetalj bruker 160 × 160
- oversiktsmålene 84 × 84 og 90 × 90 beholdes
- logo bruker contain; foto bruker cover og fokuspunkt
- alle åtte kort-/bildevisninger tåler lange navn, kommuner, tags og knapper
- PUBLIC-tags er grønne
- ødelagt rendition gir CRM-fallback
- upublisert aktør lekker ikke bilde eller metadata
- ID-rute og entydig legacyredirect beholder eksisterende regresjonsadferd
- det loves ikke previewstøtte i alle tredjepartsklienter
- én formell takedown gir fallback og ingen gammel mediareferanse i legacy HTML, aktivt public API, Editor-preview, ny projection eller delingsmetadata

**Testkrav:**

- serializer-/OpenAPI-kontrakt for strukturert objekt, aliaser og deprecation
- list/detail-kontrakttest mot den faktisk aktive `/api/public/actors/`-ruten, ikke bare en alternativ eller shadowed serializer
- PUBLIC HTML- og head-tester for canonical, OG og Twitter
- host-header-invarians og identiske absolutte URL-er mellom API og head
- E2E på desktop og mobil for alle åtte visninger
- computed-style/overflow og målrettet visuell kontroll
- bevis for at projection aldri gjør ekstern fetch
- shadow-diff av legacy og ny projection før cutover

**Rollback:**

- cutoverflagget kan slås av per tenant
- tatt ned, avvist eller karantenelagt bilde kan ikke gjenkomme via legacy
- systemfallback brukes når sikker legacyrollback ikke er mulig
- ingen nye modeller eller auditdata slettes

### Fase 3F: legacyovergang, Import-kontrakt og driftsverifisering

**Omfang:**

- skrivebeskyttet legacyinventar og kandidater uten automatisk godkjenning
- stoppe automatisk bilde-refresh ved aktørlagring og nettverk i import-commit
- typed kontrakt for `KEEP_LOCKED_IMAGE`, `SET_APPROVED_IMAGE` og `USE_APPROVED_FALLBACK`
- backup-/restoreøvelse og kontrollert stagingverifisering
- stabiliseringsperiode før senere feltdropp

Full Import 2.0-review-UX implementeres fortsatt i roadmapens senere importfase.

**Akseptansekriterier:**

- legacy URL blir aldri aktivt bilde uten eksplisitt approval
- eksisterende låst selection beholdes uten eksplisitt beslutning
- import-commit gjør null søk, fetch, nedlasting, dekoding eller rendition-generering
- wrong-tenant, stale eller ikke-klart asset avvises
- bildecommit er idempotent og endrer ingen publiseringsflagg
- database og assets kan gjenopprettes sammen
- staging bekrefter public projection, API-aliaser, kort, metadata, takedown og fallback
- legacyfelt droppes ikke i samme leveranse

**Testkrav:**

- dry-run og idempotent legacyinventar
- importkontrakt med eksplisitt assert på null nettverks-/prosesskall i commit
- offentlig diff og tenantavgrenset staging-smoke
- restoreøvelse og kontrollert orphan-/retentionjobb

**Rollback:**

- legacyfelt beholdes read-only gjennom stabiliseringsperioden
- importbildedecisions kan deaktiveres uten å slette godkjente assets eller events
- public projection kan gå til systemfallback
- fysisk feltdropp, objektcleanup og aliasfjerning krever egne senere gater

## Tverrgående akseptansekriterier

ADR-007 regnes som implementert først når:

- aktivt bilde er CRM-kontrollert
- privat original bevares
- offentlig bruk skjer gjennom renditions
- samme selection brukes av Editor, PUBLIC, public API og Open Graph
- ett-klikk-godkjenning er versjonert og sporbar
- kreditering ikke er obligatorisk uten konkret krav
- låst bilde ikke kan erstattes automatisk
- ingen bildehandling endrer publiseringsflagg
- plattformlogoer ikke kan godkjennes
- logo ikke kuttes
- foto kan bruke fokuspunkt
- fallback fungerer uten ekstern kilde
- public API er bakoverkompatibelt i overgangsfasen
- Open Graph bruker CRM-rendition
- Import 2.0 beholder låst bilde uten eksplisitt beslutning
- takedown fjerner offentlig bruk uten å slette historikk
- backup og restore dekker database og assets
- legacy URL-er fases ut kontrollert og aldri godkjennes automatisk

## Rollbackprinsipper

- Modeller og API utvides additivt frem til separat opprydding.
- Legacyfelt beholdes gjennom cutover og stabiliseringsperiode.
- Feature flag eller tilsvarende kontroll brukes for ny skriverute og public projection.
- Ekstern I/O og filbehandling avsluttes før korte selection-/importtransaksjoner.
- Rollback sletter ikke immutable events, private originaler eller godkjenningssnapshots.
- Selection endres med ny revisjon og kompenserende event.
- Orphan cleanup er forsinket, idempotent og referansebevisst.
- Takedown-/deny-status overlever alle feature-flag- og legacyrollbacks.
- Database- og mediarestore testes som én konsistent operasjon; eventuell senere object-storage-restore skal bevise samme invariant.
- Fysisk feltdropp, aliasfjerning og irreversibel cleanup skjer i egne leveranser.

## Tekniske valg som fortsatt er åpne

Følgende gjenstår etter de godkjente fase 3B.1-, 3B.1R-, 3B.2- og 3B.3-valgene:

- konkret trigger og migreringsplan dersom objektlagring/CDN senere blir nødvendig
- eksakte socket-permissions, peer-autorisasjon og timeout-/healthkontrakt for Djangos lokale 3E.1B-bro til den host-eide safety-runtimeen
- konkret `public-delivery`-path/mount, API-rettighet og eksplisitt backup-/restore-allowlist før stagingaktivering
- full katastrofe-RTO og senere eventuell ekstra regionredundans; ADR-008-backupen er aktivert og restore-smoke er målt
- SVG-rasteriseringsverktøy
- eventuell bakgrunnskø
- eventuell skadevarekontroll
- om mer enn ett fokuspunkt eller en placementmodell senere trengs
- endelig fallbackgrafikk og fallback-alttekst; ADR-009 har fastsatt `image`, enum og aliasmapping
- konkret lokal cache-TTL, headers, purge- og verifikasjonskontrakt; provider/CDN bare ved senere dokumentert behov
- om første MVP tillater logisk same-tenant assetgjenbruk
- retensjonsfrist for godkjente, aldri tilknyttede assets
- om fallback-selection låser innholdssnapshot eller rendereroppskrift
- teknisk leveringsmekanisme, TTL og audit for administrativ tilgang til privat original
- auditretensjon og eventuell kontrollert anonymisering
- scheduler-/workergrense for retensjon

Disse valgene endrer ikke hovedarkitekturen. Fase 3B.1R, fase 3B.3, fase 3B.3-A-domenegrunnmuren, operativ aktivering av ADR-008-backupen og ADR-009s fase 3E.1A er gjennomført som beslutnings-, implementerings- og evidensgater. ADR-009s fase 3E.1B–3E.4 skal implementeres og bevises før offentlig serving eller formell takedown aktiveres.

## Beslutninger som fortsatt krever eksplisitt godkjenning

Gjenstående fase 3B-resultater må godkjennes før de respektive produksjonsrettede runtimeleveransene aktiveres. Godkjenningen skal minst omfatte:

- konkret implementasjonsevidens for ADR-009s delivery-root, controlled serving, origins, purge og restoreadferd; lokal ledger, off-server anker, read-model/cursor og host/systemd-placement er bevist i 3E.1A
- lokal socketprotokoll, peer-autorisasjon og minst-privilegert runtimekobling mellom Django og den host-eide safety-runtimeen
- fallbackgrafikk/-alttekst og cache-TTL/headerverdier som ADR-009 bevisst lar åpne
- sync/async-grense og cleanupmekanisme
- same-tenant reuse- og orphan-retensjonsregel

Den overordnede arkitekturen, rollene, approvalteksten, fallbacken, den additive API-overgangen, retensjonsprinsippene, Import 2.0-kontrakten, fase 3B.1 processing profile v1, fase 3B.2 storage-/delivery-/takedown-/restoreprinsippene og fase 3B.3 release identity-/key-/reservasjonskontrakten er godkjent gjennom dette ADR-et og skal ikke åpnes på nytt uten ny evidens eller en eksplisitt endringsbeslutning.

## Ferdigkriterium

ADR-007 kan omtales som implementert først når fase 3B–3F er levert og verifisert, legacy URL ikke lenger er aktiv offentlig bildekilde, relevante tester er grønne, database og assets kan gjenopprettes sammen, staging er kontrollert og autoritativ dokumentasjon beskriver faktisk adferd.
