# ADR-007: Tenant-eid bildeassetarkitektur

## Status

Godkjent som arkitekturgrunnlag. Fase 3A og den isolerte fase 3B.1-prototypen er gjennomført. Prosjekteier har godkjent processing profile v1 og faseinndelingen nedenfor, men bildearkitekturen er ikke implementert i CRM-runtime.

**Beslutningsdato:** 2026-07-30

**Fase 3B.1-valg godkjent:** 2026-07-31

**Dokumentert i repo:** 2026-07-31

Denne beslutningen innebærer ingen applikasjonskode, datamodell, migrasjon, storage-konfigurasjon, API-endring, frontendendring, dataendring eller deploy. Dagens legacyflyt med eksterne bilde-URL-er gjelder fortsatt frem til en kontrollert overgang er implementert og verifisert.

## Forhold til tidligere ADR-er

ADR-007 viderefører:

- [ADR-001](ADR-001-TENANT_ARCHITECTURE.md): kandidater, assets, selections, renditions, events og alle bildekommandoer skal være tenant-isolerte
- [ADR-003](ADR-003-PUBLICATION_MODEL.md): private originaler, intern proveniens og audit skal være adskilt fra offentlig bildeleveranse
- [ADR-004](ADR-004-IMPORT_ARCHITECTURE.md): import skal bruke preview, review og eksplisitt commit, også når et bilde inngår
- [ADR-005](ADR-005-CONTACT_ARCHITECTURE.md): én felles offentlig projeksjon skal hindre at Editor-preview, HTML og API får egne regler
- [ADR-006](ADR-006-SESSION_WORKFLOW.md): godkjent retning skal lagres varig før større implementering starter

ADR-007 endrer ikke kontaktmodellen eller publiseringsreglene i ADR-003 og ADR-005. Et bilde kan være godkjent og låst uten at aktøren er publisert. En bildehandling skal aldri aktivere eller endre aktør-, person- eller kontaktpublisering.

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
- alt-tekst
- offentlig kreditering når den er relevant eller påkrevd
- status, revisjon og tidspunkt
- hvem som godkjente og låste valget

Det skal bare finnes ett aktivt bildevalg per aktør. Dette håndheves i domenekommando og databaseconstraint.

En selection er et eksklusivt valg:

- asset-selection skal peke på nøyaktig ett asset i samme tenant
- fallback-selection skal ikke peke på et tenantasset

Et godkjent og låst valg overskrives aldri automatisk. «Godkjenn og erstatt bilde» oppretter en ny aktiv revisjon, arkiverer forrige selection og registrerer hendelsen. Gjenoppretting av et ordinært arkivert bilde oppretter også en ny revisjon, slik at historikken ikke omskrives.

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

Processingbibliotek, første formatsett og maksimal kildefilstørrelse er godkjent i punkt 23. Endelig pixelgrense, dimensjonsregler, kvalitetsgrenser og eventuell skadevarekontroll avgjøres fortsatt gjennom senere fase 3B-evidens.

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
4. utløse og verifisere nødvendig CDN-invalidering
5. flytte eller merke originalen som begrenset privat karantene
6. registrere årsak, bruker, tidspunkt og berørte referanser
7. hindre at samme checksum stille lastes opp og godkjennes på nytt av en redigerer

Checksum-deny er tenant-avgrenset som standard. En gruppeadmin i tenant A kan ikke påvirke eller få vite om identiske bytes i tenant B. En global checksum-blokkering er en separat plattform-superadminhandling med eget scope og audit.

Offentlige rendition-nøkler er immutable og cachevennlige, men skal ikke være uoppsigelige. Valgt storage-/CDN-løsning må støtte kontrollert origin-fjerning og purge. Gjenoppretting etter takedown skal bruke ny offentlig rendition-nøkkel.

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
- Bilder skal ikke strekkes eller skaleres opp automatisk for å skjule for lav kildeoppløsning.
- Når nødvendig rendition ikke kan produseres uten oppskalering, skal flyten be om en bedre kilde, velge et annet bilde eller bruke en kontrollert Kreative Norge-komposisjon eller fallback.
- Square, landscape og share bruker samme godkjente original, fit og fokusintensjon.
- Ulike aspect ratios kan ikke ha identisk pikselutsnitt; tilsvarende visninger med samme ratio skal bruke samme cropkontrakt.
- Aktørnavn er trygg standard for alt-tekst når ingen bedre redaksjonell tekst finnes.

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
- eksakt alias-til-variant-mapping fastsettes og dokumenteres før API-implementeringen
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

- `FileSystemStorage` eller tilsvarende i lokal utvikling
- S3-kompatibel objektlagring i staging og produksjon
- Djangos `STORAGES`-grensesnitt mellom applikasjon og leverandør

Endelig leverandør besluttes etter en teknisk spike.

Storage-kontrakten er:

- originaler er private
- offentlige renditions har immutable, cachevennlige og versjonerte nøkler
- offentlige renditions kan leveres gjennom objektlager og CDN
- originaler krever autentisert og rollebeskyttet administrativ tilgang
- database og bildefiler inngår begge i backup og restore
- restore skal kontrollere konsistens mellom database, originaler og aktive renditionreferanser
- filer lagres ikke som databaseblob
- named Docker-volume kan brukes i isolert prototype, men er ikke endelig staging-/produksjonsmål
- eventuell fysisk deduplisering er usynlig og kan aldri bryte tenant-isolasjonen
- storage-/CDN-løsningen må støtte takedown, origin-fjerning og cache-invalidering

Private originaler og offentlige renditions skal bruke egne navngitte `STORAGES`-aliaser og tilgangspolicyer. Eksisterende import- og eksportfiler bruker allerede Djangos default storage; bildearbeidet skal ikke endre deres backend eller filplassering uten en separat kompatibilitets- og migreringsplan.

Fase 3B avgjør om renditions inngår direkte i backup eller kan regenereres deterministisk fra original, selection og prosesseringsversjon. Privat original og nødvendig audit/proveniens skal alltid kunne gjenopprettes etter den vedtatte retensjonen.

Restore kan ikke publisere media før en separat, varig takedown-/deny-journal er avstemt mot den restaurerte databasen og objektlageret. Takedown som skjedde etter et eldre backup-punkt skal fortsatt vinne. Inntil avstemmingen er verifisert, leverer public image projection systemfallback. Gamle objektnøkler eller S3-versjoner kan aldri reaktiveres automatisk av restore.

### 19. Bildekilder og providergrense

Godkjente kandidatkilder er:

- offisiell nettside
- Open Graph
- vanlige bilder på offisiell nettside
- Brave Image Search
- opplasting
- manuelt limt kilde-URL
- systemfallback

Brave skal ligge bak en egen provider-adapter og implementeres ikke før følgende er kontrollert:

- API-vilkår
- caching
- retention
- attribusjon
- SafeSearch
- kostnad
- rate limits

Full providerrespons lagres ikke. Bare nødvendig proveniens for valgt kandidat beholdes permanent. URL-er og metadata skal renses slik at credentials eller tokens ikke lagres utilsiktet.

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

Format, encoderinnstillinger, source checksum, fit, normalisert fokus, renditionvariant og processing-version inngår i immutable key. Endring av en av disse verdiene gir ny key og overskriver aldri historisk output. AVIF er utsatt og er ikke et MVP-krav.

Offentlige renditions skal ha en eksplisitt testet sRGB-normaliseringskontrakt før fase 3C. Fase 3B.1 beviste metadatafjerning, men fastsatte ikke fargeprofilnormalisering.

#### Fit, fokus, oppskalering og metadata

- Logo bruker `contain` og skal ikke kuttes eller strekkes.
- Foto bruker `cover` og lagret normalisert fokuspunkt; sentrum er standard.
- EXIF-orientering skjer før crop.
- Sensitive metadata fjernes fra offentlige renditions.
- Ingen kildepiksler skaleres opp automatisk. For lavt reelt cropområde håndteres med bedre kilde, annet bilde eller kontrollert komposisjon/fallback, ikke et uskarpt offentlig bilde.
- Privat original følger den separate storage- og retensjonskontrakten.

#### Tekniske grenser og fortsatt åpne kvalitetsvalg

Maksimal kildefilstørrelse på 15 MiB er godkjent som konfigurerbar standardverdi.

Følgende er fortsatt prototypeverdier og ikke godkjente endelige produktgrenser:

- 20 megapiksler som maksimal pixelgrense
- korteste side under 160 som universell hard fail
- 160–511 som universelt reviewområde
- minst 512 som universell pass
- edge variance under 5 som automatisk hard fail
- de øvrige edge-variance-/blurintervallene

En pixelgrense skal finnes av sikkerhetshensyn, men endelig tall krever representative høyoppløselige fixtures og ressursmålinger. Dimensjonsregler skal vurderes per bildetype, fit, variant, reelt cropområde og behov for oppskalering. Én universell regel basert bare på korteste side skal ikke avvise alle logoer og foto. Blur-/edge-variance brukes foreløpig bare som varsel, reviewprioritering og diagnostisk informasjon, ikke automatisk endelig hard fail.

#### Fase 3B.1R: representativ kvalitetsvalidering

Før fase 3C skal et lite, rettighetsavklart datasett med ekte brede/høye logoer, logoer med liten tekst og whitespace, portretter, gruppebilder, mørke scene-/konsertbilder, komprimerte nettsidebilder, plakater/årstall, vannmerker, høyoppløselige mobilbilder og reelle ICC-/fargeprofiler testes.

Fase 3B.1R skal brukes til å fastsette pixelgrense, variant- og cropbaserte dimensjonsregler, blur-/komprimeringsvarsler, lesbarhetsvarsler for logo og eventuell begrenset kvalitetsregel. Delsteget blokkerer ikke fase 3B.2, men må være gjennomført og godkjent før fase 3C.

#### Fase 3B.2: neste godkjente spike

Neste leveranse er en isolert storage-, immutable-key-, purge-, deny- og restorelab. Den skal teste:

- separate private/public `STORAGES`-aliaser uten å endre default storage for eksisterende import-/eksportfiler
- lokal filesystemreferanse og én disponibel S3-kompatibel testbackend
- immutable renditionkeys fra processing profile v1
- private originaler og offentlige renditions
- allowlistede og absolutte media-origins
- origin-sletting, purge/takedown og ny offentlig key ved restore
- en varig deny-journal som vinner over eldre database-/object-backup
- direkte renditionbackup mot deterministisk regenerering
- statisk nød-fallback ved storage- eller rendererfeil

Fase 3B.2 er ikke implementert og skal ikke opprette CRM-bildemodeller, migrasjoner, aktive API-ruter, OpenAPI-schema, Editor, PUBLIC, selection-concurrency, Import 2.0-integrasjon, bakgrunnskø eller stagingdeploy.

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

### Bruke named Docker-volume som endelig staging-/produksjonslager

Avvist som målarkitektur fordi private originaler, offentlig leveranse, cache, backup/restore og fremtidig drift krever en eksplisitt storagekontrakt. Et volume kan brukes i en avgrenset prototype.

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
- CDN-/cachehåndtering ved takedown
- midlertidig dual-read/compatibility under legacyovergangen
- ekstra operasjonell kompleksitet rundt retensjon og karantene

### Risiko som skal reduseres i fase 3B

- for høy prosesseringskostnad eller minnebruk på representative batcher
- manglende eller inkonsistent sRGB-normalisering
- storageleverandør uten tilstrekkelig privat tilgang, purge eller restore
- dårlig kvalitetsterskel som avviser gode logoer eller godkjenner svake bilder
- uklare regler for samme-tenant assetgjenbruk og orphan cleanup
- dynamisk fallback som ikke er stabil eller tilgjengelig
- alias- eller cacheadferd som gjør public API eller takedown inkonsistent

## Implementeringsleveranser og akseptansekriterier

Ingen leveranse under skal starte før gate og stoppunkt for leveransen er godkjent. Leveransene skal være additive og reversible frem til separat legacyopprydding.

### Fase 3B: teknisk prototype og kontrakt

**Status:** Fase 3B.1 er teknisk gjennomført og processing profile v1 er godkjent. Fase 3B.1R er en påkrevd kvalitetsgate før fase 3C. Fase 3B.2 er neste godkjente isolerte spike og er ikke implementert.

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
- providerprototypen beviser origin-fjerning, CDN-purge og gjenoppretting med ny nøkkel
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

**Omfang:**

- kandidatfunn, upload, limt URL og systemfallback
- teknisk status, varsler, kildegrunnlag og previews
- «Godkjenn og lås bilde»
- «Godkjenn og erstatt bilde»
- ordinær arkivering, fjerning til fallback, restore og historikk
- forberedt, men deaktivert takedown- og karantenegrensesnitt frem til deny-gaten i fase 3E er grønn

**Akseptansekriterier:**

- standardgodkjenning krever ett tydelig klikk etter ferdig teknisk behandling
- godkjenningstekst versjon og snapshot lagres
- kjent krediteringskrav blokkerer til kravet er løst eller særskilt vurdert
- låst bilde erstattes aldri av bakgrunnsjobb, refresh eller import
- leser kan ikke utføre handlinger eller se sensitiv metadata
- redigerer kan ikke utføre formell takedown
- gruppeadmin, tenant-superadmin og plattform-superadmin følger riktig scope
- Editor-preview bruker den nye projection i shadow/feature-flag-modus
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
- Database- og object-storage-restore testes som én konsistent operasjon.
- Fysisk feltdropp, aliasfjerning og irreversibel cleanup skjer i egne leveranser.

## Tekniske valg som fortsatt er åpne

Følgende gjenstår etter de godkjente fase 3B.1-valgene:

- endelig pixelgrense basert på representative høyoppløselige fixtures og ressursmålinger
- dimensjonsregler per bildetype, fit, variant, reelt cropområde og oppskaleringsbehov
- blur-, komprimerings- og logolesbarhetsvarsler og eventuell begrenset kvalitetsregel
- eksplisitt sRGB-normaliseringskontrakt
- konkret S3-kompatibel objektlagringsleverandør
- SVG-rasteriseringsverktøy
- eventuell bakgrunnskø
- eventuell skadevarekontroll
- om mer enn ett fokuspunkt eller en placementmodell senere trengs
- eksakt public API-feltnavn, enum og alias-til-variant-mapping
- konkret storage-key-, cache- og purgekontrakt innenfor den godkjente immutable key-invarianten
- om første MVP tillater logisk same-tenant assetgjenbruk
- retensjonsfrist for godkjente, aldri tilknyttede assets
- om fallback-selection låser innholdssnapshot eller rendereroppskrift
- teknisk leveringsmekanisme, TTL og audit for administrativ tilgang til privat original
- auditretensjon og eventuell kontrollert anonymisering
- scheduler-/workergrense for retensjon
- om renditions sikkerhetskopieres eller regenereres ved restore

Disse valgene endrer ikke hovedarkitekturen. Fase 3B.1R-, 3B.2- og øvrig fase 3B-evidens skal dokumenteres og relevante beslutninger godkjennes før fase 3C starter.

## Beslutninger som fortsatt krever eksplisitt godkjenning

Fase 3B-resultatet må godkjennes før produksjonsrettet implementering av fase 3C. Godkjenningen skal minst omfatte:

- konkret storageleverandør og backup-/restorekontrakt
- representative pixel-, dimensjons- og kvalitetsgrenser fra fase 3B.1R
- eksplisitt sRGB-normaliseringskontrakt
- purge-/takedownadferd
- endelig API-schema og aliasmapping
- sync/async-grense og cleanupmekanisme
- same-tenant reuse- og orphan-retensjonsregel

Den overordnede arkitekturen, rollene, approvalteksten, fallbacken, den additive API-overgangen, retensjonsprinsippene, Import 2.0-kontrakten og fase 3B.1 processing profile v1 er godkjent gjennom dette ADR-et og skal ikke åpnes på nytt uten ny evidens eller en eksplisitt endringsbeslutning.

## Ferdigkriterium

ADR-007 kan omtales som implementert først når fase 3B–3F er levert og verifisert, legacy URL ikke lenger er aktiv offentlig bildekilde, relevante tester er grønne, database og assets kan gjenopprettes sammen, staging er kontrollert og autoritativ dokumentasjon beskriver faktisk adferd.
