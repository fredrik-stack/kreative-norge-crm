# ADR-012: Place identity, geografisk klassifikasjon og actor-only kart

## 1. Status

Godkjent målarkitektur – ikke implementert

**Beslutningsdato:** 2026-08-31

**Dokumentasjonsbaseline:** `main` på
`98a20c5aa6e8e7743db8b4310d4093cb17b51d3a`

ADR-et formaliserer fase 5C. Leveransen oppretter ingen modeller, migrasjoner,
data, API-ruter, frontend, Google Cloud-prosjekt, nøkler, runtimefeatureflagg
eller stagingendringer.

Dagens implementerte stedskontrakt er fortsatt fritekstfeltene
`Organization.municipalities` og `Person.municipality`. Det finnes ingen
`Place`, `PlaceProviderReference`, `PlaceCoordinate`, `OrganizationPlace`,
`PersonPlace`, `GeographicTenantRuleSet`, Google Maps-integrasjon eller
kartprojeksjon i aktiv kode.

## 2. Relasjon til tidligere ADR-er

- [ADR-001](ADR-001-TENANT_ARCHITECTURE.md): dagens Organization og Person er
  direkte tenant-eid. Etter ADR-011 blir tenant assignment- og arbeidsscope,
  mens Place er felles geografisk referansedata. Stedsrelasjoner arver fortsatt
  objektets autoriserte SharingDomain-/tenant-scope.
- [ADR-003](ADR-003-PUBLICATION_MODEL.md): et strukturert sted blir ikke
  offentlig bare fordi Organization eller Person publiseres. Offentlig
  OrganizationPlace krever et eksplisitt valg på relasjonen.
- [ADR-004](ADR-004-IMPORT_ARCHITECTURE.md): sted går gjennom preview,
  normalisering, matching, tvetydighetsreview og eksplisitt commit.
- [ADR-005](ADR-005-CONTACT_ARCHITECTURE.md): PersonPlace får ingen
  kartfunksjon. Eventuell tekstlig publisering av et godkjent personsted følger
  den separate person-/relasjons- og publicationkontrakten.
- [ADR-007](ADR-007-IMAGE_ASSET_ARCHITECTURE.md) og
  [ADR-009](ADR-009-PUBLIC_IMAGE_RUNTIME_RELEASE_DELIVERY_AND_RESTORE_SAFE_DENY_STATE.md):
  kart kan lese den godkjente Organization-bildeprojeksjonen eller
  systemfallback, men oppretter, flytter eller endrer ingen image state.
- [ADR-008](ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md): varige
  Place-/relasjonsdata, regler, proveniens, audit og koordinater som lovlig kan
  følge ordinær retensjon, inngår i databasebackup og restore. Tidsbegrensede
  rå providerkoordinater får ikke automatisk følge PostgreSQL-/Borg-/Storage
  Box-/Cloud Backup-kjeden; de krever den separate restore-sikre kontrakten i
  dette ADR-et. ADR-012 oppretter ingen ny filstorage.
- [ADR-010](ADR-010-INTERNATIONAL_PHONE_IDENTITY_AND_NORMALIZATION.md): telefon
  og sted er separate matchsignaler. Ingen av dem er alene personidentitet eller
  automatisk mergegrunnlag.
- [ADR-011](ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md):
  canonical Organization/Person, eksakt SharingDomain, assignments, overlays,
  agreement/capabilities og én PUBLIC-identitet er forutsetninger. Geografi kan
  foreslå assignment, men aldri opprette assignment eller gi autorisasjon.

## 3. Bakgrunn

Fase 5A kartla dagens tenant-, import-, PUBLIC-, bilde- og lagringsgrunnlag uten
writes. Den PII-frie evidensen fant 125 Organizations med ikke-tom
`municipalities`, hvorav 32 hadde flere skilletegnsdelte steder, og 141 Persons
med ikke-tom `municipality`. Tallene er et datert migreringsgrunnlag, ikke en
løpende produksjonsmåling.

Aktiv kode bruker de to fritekstfeltene i Editor, API, importmatching og PUBLIC.
Navn kan være tvetydige, administrative grenser endres, og ett tekstfelt kan
inneholde flere steder. Samtidig trenger framtidig Import 2.0 konsistent
stedsreview og redaksjonelle tenantforslag, mens Editor og PUBLIC trenger et
kart som aldri trekker personer eller private CRM-data inn i provider-scope.

ADR-011 har allerede besluttet canonical Organization/Person og
SharingDomain-grensen. ADR-012 legger stedskontrakten oppå denne målmodellen
uten å åpne identity- eller assignmentbeslutningen på nytt.

## 4. Problem

Systemet trenger å kunne:

- identifisere norske og utenlandske steder uten å bruke navn som unik nøkkel
- skille varig stedssannhet fra kortlivet eller vilkårsbundet providerdata
- knytte flere steder til en aktør og en person med tydelig proveniens
- gi forklarbare, versjonerte tenantforslag uten å gjøre dem til tilgang
- migrere fritekst additivt uten tap eller skjult publisering
- vise Organizations på kart uten personmarkører eller private data
- fortsette med lister, søk, importreview og steder når Google er av eller nede

En direkte Google-modell ville blande intern identitet med en ekstern database,
gjøre sentrale funksjoner provideravhengige og bryte gjeldende EØS-begrensninger
for lagring og videre bruk av Places-innhold.

## 5. Scope

ADR-012 eier målkontrakten for:

- global provider-nøytral Place
- norske offentlige navn, administrative koder og kildeversjoner
- providerreferanser og separat koordinatlivssyklus
- OrganizationPlace og PersonPlace
- versjonerte geografiske tenantregler og rådgivende forslag
- additiv legacyovergang og framtidig `STEDER`-importkontrakt
- actor-only kart i Editor og PUBLIC
- dataminimerte kartprojeksjoner, fallback, featuregater og rollback
- provider-, nøkkel-, personvern-, attribusjons- og produksjonsporter

## 6. Ikke-mål

Følgende avvises eller utsettes i MVP:

- personkart, personmarkører og marker clustering for personer
- Google-søk eller geokoding av personer og offentlige personkartpunkter
- gateadresse som generelt krav eller registrering av private hjemmeadresser
- ruteplanlegging, avstandsmatriser, Street View, heatmaps og live-posisjon
- brukersporing
- PostGIS, polygonlag, tenantfylkespolygoner og egen punkt-i-polygon-analyse
  basert på Google-koordinater
- masseimport eller kopiering av virksomheter fra Google Places
- skjult geografisk AI-avgjørelse eller automatisk tenantassignment
- kart-, provider- eller geokodingskall under import-commit
- generisk multi-provider-orkestrering
- låsing til én bestemt frontendpakke eller Google Maps-versjon
- fysisk fjerning av legacy-stedsfeltene
- detaljdesign av kartlayout, wireframes, markører, farger, filtre, sidepanel,
  eksakte API-ruter, npm-versjoner eller Google Cloud-oppsett

Disse grensene hindrer ikke framtidig tekstlig publisering av et eksplisitt
godkjent personsted etter ADR-003/ADR-005.

## 7. Begreper

**Place** er offentlig geografisk referansedata med stabil intern identitet.

**PlaceProviderReference** kobler et Place til en ekstern kilde- eller
provideridentitet uten å gjøre provideren canonical.

**PlaceCoordinate** er én kildebelagt kartposisjon med presisjon, status og egen
livssyklus.

**OrganizationPlace** og **PersonPlace** er typed relasjoner mellom canonical
CRM-objekt og Place. Scope, publication og privat proveniens ligger på objektet
og relasjonen, ikke på Place.

**GeographicTenantRuleSet** er et versjonert regelsett i ett SharingDomain som
produserer rådgivende tenantforslag fra kontrollerte geografiske koder.

**Actor-only map** betyr at bare canonical Organizations kan inngå i
kartprojeksjon. PersonPlace er strukturert data, men har aldri kartscope.

**Providerdata** er data hvis bruk, lagring, attribusjon eller levetid styres av
en ekstern avtale. Providerdata er ikke automatisk plattformens stedssannhet.

**Varig koordinat** er kildebelagt koordinatdata som etter kontroll av kilde,
lisens, bruk, policy og attribusjon kan følge ordinær databasebackup og restore.

**Tidsbegrenset rå providerkoordinat** er latitude/longitude eller en avledet
representasjon som kan rekonstruere dem, og som etter providerpolicy må slettes
eller ikke kan følge ordinær langtidsretensjon.

## 8. Global provider-nøytral Place

Place er felles geografisk referansedata på plattformnivå og skal kunne
gjenbrukes av flere SharingDomains. Den har en stabil intern ID og kan minst
representere:

- land, region/fylke, kommune, by, tettsted og annet relevant sted
- menneskevennlig visningsnavn og landkode
- valgfritt administrativt hierarki
- valgfri offentlig kode med eksplisitt namespace, kilde og gyldighet
- valgfri offentlig kilde-ID og kildeversjon
- opprettelses-, kontroll- og verifiseringsstatus

Place kan eksistere uten koordinat, providerreferanse eller Google-data. Et
source-backed/systembekreftet eller kontrollert brukerbekreftet Place er
canonical når servervalideringen er fullført; det er ikke et tenantprivat utkast
som venter på plattformgodkjenning. Senere kildeverifisering endrer ikke den
interne identiteten.

Place skal ikke:

- eies av én tenant eller ett SharingDomain
- inneholde aktør-/personnotater, private tags eller andre CRM-overlays
- gi tilgang til Organizations eller Persons i andre SharingDomains
- bruke visningsnavn alene som global unik identitet
- være en polymorf CRM-relasjon
- være en kopi av Google Places eller et annet providerregister

Providerens ID-semantikk inngår i identiteten. For eksempel må Kartverkets
stednummer, stedsnavnnummer og skrivemåte-ID ikke behandles som samme ID-type.
Offentlige administrative koder lagres som tekst slik at ledende null bevares.

En autorisert tenantbruker eller importreviewer med relevant create-/edit-
capability kan gjennom én kontrollert server-side tjeneste:

- søke etter og velge et eksisterende Place
- bekrefte en entydig source-backed kandidat, slik at tjenesten oppretter eller
  gjenbruker canonical Place umiddelbart etter duplicate-/similarity-kontroll
- velge `Opprett nytt sted manuelt` når ingen klar kilde finnes; navn, land,
  region/fylke, kommune, type, original råtekst og kilde/begrunnelse kreves i den
  utstrekning de er relevante og kjente
- knytte resultatet til canonical Organization eller Person og lagre den typed
  relasjonen i samme arbeidsflyt
- eksplisitt gjøre OrganizationPlace offentlig i samme arbeidsflyt når separat
  publication-capability og alle øvrige porter er oppfylt

Dette gjelder Editor, senere Import 2.0, Organization create/update og
PersonPlace. Et offentlig OrganizationPlace blir map-eligible først når et
lovlig, gyldig kartpunkt og alle kart-/providerporter også er grønne.

Duplicate-/similarity-kontrollen sammenligner minst normalisert navn, land,
region/fylke, kommune, stedstype, offentlige kilde-ID-er, alternative
skrivemåter og redirect-/tombstonehistorikk. Eksakt score og terskler avgjøres i
implementeringen.

Normal Place-opprettelse krever ikke plattform-superadmin, obligatorisk ekstra
menneskelig godkjenning eller et eget workflow-subsystem. Den kontrollerte
tjenesten kjører duplicate-/similarity-, autorisasjons-, revision-/stale- og
servervalidering før write og registrerer proveniens og audit. Et manuelt sted
som passerer denne valideringen blir et gjenbrukbart, canonical,
brukerbekreftet Place og kan brukes tekstlig og i offentlig typed relasjon;
koordinat-, kart- og tenantregelkrav vurderes separat. Tjenesten gjør aldri en
automatisk merge av to eksisterende Places.

Verifisering er datakvalitetsstatus, ikke en plattformrolle. Konseptuelle
utfall er source-backed/systembekreftet, brukerbekreftet,
tvetydig/review-required, avvist, deaktivert og redirected/merged; eksakte enum-
navn avgjøres i implementeringen. Bare reell tvetydighet eller konflikt går til
review. Uavklarte/tvetydige kandidater kan bevare råtekst og proveniens, men kan
ikke publiseres, få kartmarkør, drive GeographicTenantRuleSet, brukes som
verifisert match eller skjult mutere global Place.

En tvetydig kandidat kan forbli eksplisitt knyttet til sin ImportJob-/
reviewkandidat. Importrevieweren løser den ved å velge et eksisterende Place
eller oppgi tilstrekkelig geografisk kontekst; ingen canonical Place- eller
relasjonswrite skjer før utfallet er entydig.

En vanlig tenantbruker kan ikke vilkårlig endre en eksisterende global Place,
providerreferanse, administrativ sannhet eller aktivt kartpunkt. Brukeren kan
legge til, fjerne eller endre eget autoriserte objekts
OrganizationPlace/PersonPlace, velge eller opprette Place gjennom tjenesten,
publisere OrganizationPlace med separat publication-capability og sende inn en
global rettelse. Plattformcapability er forbeholdt merge, redirect/tombstone,
deaktivering av referert Place, endring av kilde-ID, administrativt hierarki
eller global koordinat som påvirker eksisterende referanser, multi-domain-/
massekonflikter og provideropprydding.
Slike globale handlinger krever revision-/stale-kontroll og audit. Et referert
Place slettes ikke destruktivt; merge eller deaktivering bevarer relasjoner,
proveniens og historikk. Eksakte rolle- og tjenestenavn avgjøres i
implementeringen.

## 9. Norsk stedssannhet og offentlige koder

For norske steder er målretningen:

- Kartverkets Sentrale stedsnavnregister (SSR) er primær offentlig navne- og
  stedskilde når registerets stedstype og ID passer behovet.
- SSB Klass sine versjonerte kommune- og fylkesklassifikasjoner er autoritet
  for administrative områder og geografiske tenantregler.
- kilde, ID-type, ekstern ID, klassifikasjon, kode, gyldighetsperiode og
  kontrollert kildeversjon lagres når de finnes
- endringer og korrespondanser mellom historiske og nye koder skal kunne spores
- Kartverkets representasjonspunkt kan brukes som PlaceCoordinate når
  gjeldende lisens og den konkrete bruken tillater det

Et entydig treff i en kontrollert Kartverket-/SSB-kilde kan bekreftes i
normalflyten og opprettes eller gjenbrukes uten separat plattformreview. Kilde,
ID-namespace, ekstern ID, kildeversjon, gyldighet og tilgjengelig administrativ
kontekst bevares.

Ikke alle norske Places trenger både Kartverket- og SSB-identitet. Et tettsted
kan ha SSR-identitet uten egen kommunekode, mens et administrativt område kan
ha SSB-kode uten behov for samme type SSR-referanse.

Svalbard skal behandles som eksplisitt territorium med eget kildenamespace og
versjonert kodegrunnlag. Det skal ikke feilaktig modelleres som et gjeldende
ordinært fylke i SSB Klass 104.

Kartverkets åpne data er ved kontroll 2026-08-31 lisensiert under CC BY 4.0.
Relevant bruk skal kreditere `© Kartverket`, og systematiske eller vesentlige
SSR-uttrekk krever konkret lisens-/attribusjonskontroll. Dette er et gjeldende
vilkår, ikke en evig arkitekturkonstant.

## 10. Providerreferanser

Et Place kan ha null, én eller flere PlaceProviderReference-rader. Relasjonen
skal minst kunne bære:

- provider og ID-namespace
- ekstern ID og providerens type/kategori
- kontrolltidspunkt og status
- nødvendig, lovlig attribusjonsreferanse
- eventuell `expires_at` eller reverifiseringsregel
- siste kontrollerte vilkårs-/adapterversjon der det er nødvendig

Samme eksterne referanse kan ikke være aktivt knyttet til flere interne Places
når providerens ID-kontrakt sier at den identifiserer ett sted. Ett Place kan
likevel ha flere referanser, og en provider kan endre eller avvikle en ID uten
at Place forsvinner.

Google Place ID kan lagres etter de offisielle reglene som gjaldt på
kontrolldatoen. Google opplyser samtidig at ID-er kan endres eller bli
foreldet, og anbefaler ved kontroll 2026-08-31 oppfriskning når de er eldre enn
tolv måneder. Intervallet skal derfor være providerpolicy, ikke hardkodet
domeneinvariant, og må reverifiseres før implementering.

## 11. Koordinater, presisjon og providerlivssyklus

PlaceCoordinate er separat kildebelagt data og skal minst støtte:

- Place
- latitude og longitude
- kilde/provider og eventuell providerreferanse
- presisjon, for eksempel region, kommune, by, tettsted eller annet
  representasjonspunkt
- `verified_at`, eventuell `expires_at`, status og aktivt godkjent kartpunkt

Latitude valideres i intervallet -90 til 90 og longitude i -180 til 180.
Koordinater kan erstattes, utløpe eller deaktiveres uten at Place slettes.
Ingen koordinat er påkrevd for Place, OrganizationPlace eller PersonPlace.
Et Place kan ha flere historiske, foreslåtte eller avviste koordinatrader når
kildens lisens, providerpolicy og retensjon tillater at råverdiene bevares. Det
kan til enhver tid ha maksimalt én aktivt godkjent kartkoordinat. Bytte av aktivt
kartpunkt skal deaktivere gammel og aktivere ny rad atomisk med revision-/stale-
kontroll og audit. Uten en slik entydig aktiv rad får Place ingen markør.

Offisielle/open-data-koordinater foretrekkes for norske steder når kilden
dekker behovet og tillater lagring. Et representasjonspunkt er ikke en påstand
om besøksadresse eller inngang; presisjonen skal være synlig i produktet.

Etter Google Maps Platforms gjeldende EØS-tjenestevilkår kontrollert
2026-08-31 kan latitude/longitude fra Places API bare caches i inntil 30
sammenhengende kalenderdager, og Places-koordinater kan ikke brukes som input
til punkt-i-polygon-analyse. En eventuell Google-koordinat må derfor ha
providerstyrt utløp, aldri være varig stedssannhet og aldri drive
tenantforslag. Perioden og tillatt bruk skal kontrolleres på nytt før
implementering og produksjonsaktivering.

Når providerens vilkår krever sletting ved utløp, skal rå latitude/longitude
fysisk fjernes innen fristen og ikke beholdes som «inaktiv historikk». Bare
lovlig, ikke-rekonstruerbar tombstone-/auditmetadata som provider, status,
slettetidspunkt, årsak og kontrollert policyversjon kan bestå. En utløpt
Google-koordinat blir umiddelbart ubrukelig som kartpunkt mens kontrollert purge
fullføres.

Varige open-data-koordinater kan følge ADR-008s ordinære PostgreSQL-, Borg-,
Storage Box-, Cloud Backup- og restorekjede når kilde, lisens, konkret bruk,
policy og attribusjon tillater samme retensjon. Dette gjelder ikke automatisk
Google-derived latitude/longitude eller annen tidsbegrenset rå providerdata.

Følgende er en bindende restore-sikker invariant: tidsbegrenset rå providerdata
kan ikke overleve tillatt levetid gjennom live database/cache, replika, kø,
eksport, logg, `pg_dump`, Borg-arkiv, Storage Box-snapshot, Cloud Backup eller
annen kopi, og kan aldri bli lesbar eller aktiv igjen etter restore. En
rekonstruerbar avrunding, geohash eller encoding behandles som rå koordinat.

Senere implementering skal velge og bevise én providerkompatibel strategi før
slike writes aktiveres, for eksempel:

- separat kortlivet storage som er bevist ekskludert fra alle langsiktige
  backup-, snapshot-, replika-, eksport- og logglag
- en særskilt backup-/purgekjede som håndhever hvert datapunkts samme
  providerfrist i alle kopier
- en juridisk og teknisk dokumentert ekvivalent løsning

At slettefristen må gjelde backup og restore er en konservativ arkitektur-/
compliance-slutning for å gjøre Googles uttrykkelige slettekrav reelt. De
kontrollerte Google-vilkårene omtaler ikke katastrofebackup, Borg, Storage Box,
Cloud Backup eller restore eksplisitt. Endelig løsning krever derfor juridisk og
kontraktsmessig kontroll; vanlig PostgreSQL-lagring med ADR-008s
langtidsretensjon er ikke godkjent som standard for disse rådataene.

Etter enhver restore skal en provider-policy-reconciliation være grønn før
provider-, koordinat- eller kartlesing/-skriving kan aktiveres. Reconciliation
skal minst:

1. identifisere provider, kilde, kontrollert policyversjon, `verified_at`,
   `expires_at` og eventuelle providerreferanser
2. deaktivere rådata før de kan leses eller projiseres
3. purge data som er utløpt, skulle vært slettet, mangler kilde, har ukjent
   policy, har utløpt referanse eller ikke lenger er lovlig
4. bare bevare lovlig, ikke-rekonstruerbar tombstone-/auditmetadata uten rå
   koordinater
5. logge resultat, policy og frist uten latitude/longitude

Google-koordinatlesing og -skriving feiler lukket når juridisk/providerbruk ikke
er godkjent, vilkårene ikke er ferskt kontrollert, policy eller kilde er ukjent,
sletting ikke kan håndheves, purge ikke er operativ, backup-/retensjonskontrakten
ikke er godkjent eller restore-reconciliation ikke er grønn. Providerpålagt
disable/purge kjører uavhengig av map-, provider- og øvrige featuregater,
rollback og om kartet er aktivt.

Utløp eller purge av en Google-koordinat sletter ikke Place,
PlaceProviderReference som fortsatt er lovlig, OrganizationPlace, PersonPlace,
GeographicTenantRuleSet, publication, proveniens eller ikke-rekonstruerbar
tombstone/audit. En lovlig Google Place ID følger sin separate
reverifiseringspolicy og slettes ikke bare fordi en koordinat utløper.

Utløpt eller utilgjengelig koordinat fjerner bare markøren. Aktøren forblir i
liste, søk og tekstlig stedspresentasjon. Vanlig sidevisning og import-commit
skal ikke skjult hente eller fornye koordinater. PostGIS innføres ikke i MVP.

## 12. OrganizationPlace

OrganizationPlace knytter canonical Organization til Place og skal minst
støtte:

- stedstype/rolle, med et lite første sett som `BASE`,
  `ACTIVITY_LOCATION` og `OTHER`
- primær/sekundær
- intern/offentlig
- verifiserings- og reviewstatus
- original importert eller legacy tekst
- kilde/proveniens, revisjon/stale-kontroll og audit
- aktiv/inaktiv historikk uten destruktiv overskriving

Eksakte felt- og enumnavn avgjøres i implementeringen. Følgende invarianter er
bindende:

- maksimalt ett aktivt primærsted per Organization
- samme aktive Organization/Place/type-kobling dupliseres ikke
- offentlig sted er et eksplisitt relasjonsvalg
- privat sted blir aldri offentlig fordi Organization publiseres
- migrering, geokoding eller publication gir ingen skjult sideeffekt
- relasjonen leses og skrives bare gjennom Organizationens autoriserte
  SharingDomain-/assignmentkontekst; Place i seg selv gir aldri cross-domain
  innsyn
- tenantassignment og OrganizationPlace er separate relasjoner
- geografi kan foreslå tenant, men kan aldri tildele tenant eller autorisere

OrganizationPlace tilhører canonical Organization og gjelder på tvers av alle
dens tenantassignments; det opprettes ingen relasjons- eller markørkopi per
tenant. Publication ligger på OrganizationPlace, aldri på Place. En autorisert
tenantbruker kan gjøre relasjonen offentlig uten plattformgodkjenning når
brukeren er aktiv, agreement, membership og assignment er gyldige, edit- og
publication-capability er oppfylt, og servervalidering samt revision-/stale-
kontroll er grønn. Publisering er alltid eksplisitt og auditert.

MVP-kartpunktet er normalt kommune, by, tettsted eller annet godkjent
representasjonspunkt. Eksakt gateadresse er ikke et generelt krav, og privat
hjemmeadresse skal ikke registreres.

## 13. PersonPlace uten kart

PersonPlace knytter canonical Person til provider-nøytral Place. Den skal kunne
støtte flere norske og utenlandske steder, primær/sekundær status,
legacy-/importert tekst, proveniens, verifisering, revision/stale-kontroll og
additiv migrering fra `Person.municipality`.

PersonPlace kan brukes til profil, matching, filtrering og rådgivende
tenantforslag. Den skal ikke:

- kreve eller hente koordinater
- utløse Google-søk, Google-geokoding eller andre skjulte providerkall
- inngå i EditorActorMapProjection eller PublicActorMapProjection
- gi personmarkør, clustering eller eget kartendepunkt
- sende personnavn, e-post, telefon, aktørrelasjon, notater eller private tags
  til Google

En autorisert bruker kan velge eksisterende eller opprette source-backed eller
brukerbekreftet Place gjennom samme kontrollerte normalflyt før PersonPlace
lagres. Et eksplisitt Place-oppslag kan bare bruke den oppgitte stedsverdien og
nødvendig geografisk kontekst; personidentitet eller annen CRM-kontekst sendes
aldri til en sted-/kartprovider. Opprettelsen gir fortsatt ingen personkartrett.

Hvis samme Place også brukes av en Organization og har koordinat, gir det ingen
kartrettighet for personen. Shared Place-coordinate skal aldri projiseres via
PersonPlace.

Tekstlig visning av et eksplisitt offentlig godkjent personsted er fortsatt
mulig etter ADR-003/ADR-005. ADR-012 forbyr personkart, ikke all tekstlig
personstedspublisering.

## 14. Geografiske tenantregler

GeographicTenantRuleSet tilhører nøyaktig ett SharingDomain og skal ha versjon,
status, gyldighetsperiode og auditerbar endringshistorikk. Reglene bruker egne
land-, klassifikasjons-, region-, kommune- eller territoriekoder og produserer
ett eller flere forklarte tenantforslag.

Bare systemvaliderte administrative koder kan drive automatisk
GeographicTenantRuleSet. Et manuelt brukerbekreftet Place uten slike koder kan
lagres, gjenbrukes, knyttes, vises tekstlig og publiseres gjennom en typed
relasjon, men gir ikke automatisk geografisk tenantforslag.

Første Musikkontoret-regelsett er:

| Geografi | Rådgivende tenantforslag |
| --- | --- |
| Nordland | Musikkontoret Nord |
| Troms | Musikkontoret Nord |
| Finnmark | Musikkontoret Nord |
| Svalbard | Musikkontoret Nord |
| Trøndelag | Musikkontoret Tempo |
| Møre og Romsdal | Musikkontoret Tempo |
| Vestland | Musikkontoret Brak |
| Rogaland | Musikkontoret STAR |
| Agder | Musikkontoret SØRF |
| Telemark | Musikkontoret ØKS |
| Buskerud | Musikkontoret ØKS |
| Vestfold | Musikkontoret ØKS |
| Oslo | Musikkontoret MØST |
| Akershus | Musikkontoret MØST |
| Innlandet | Musikkontoret MØST |
| Østfold | Musikkontoret MØST |

Tabellen har 16 eksplisitte navngitte region-/territoriemappings: de 15
gjeldende ordinære fylkene samt Svalbard som separat territorium. Den framtidige
testmatrisen skal dekke disse 16 og den separate utenlandsk/uavklart-fallbacken,
altså 17 regelutfall totalt. Det skal ikke oppfinnes en syttende fylkeskode for
å oppfylle et tallkrav.

Alle tenants kan overlappe med alle andre. Flere steder kan gi flere forslag;
samme tenant dedupliseres, mens forklaringen bevarer hvilke regler som traff.
Brukeren kan avvike fra forslaget innen ADR-011s capabilities. Eksisterende
canonical objekt kan legges til brukerens egen aktive tenant etter ADR-011;
bare plattform-superadmin kan opprette et nytt objekt direkte med flere
assignments.

Utenlandsk eller uavklart sted kan gi aktiv tenant/importjobbtenant som et
operativt forslag. Det merkes eksplisitt som ikke-geografisk og skal ikke late
som en norsk regel traff.

Et forslag:

- oppretter aldri assignment
- endrer aldri membership, capability eller autorisasjon
- krysser aldri SharingDomain
- bruker aldri Google som eneste beslutningsgrunnlag

## 15. Legacyovergang

`Organization.municipalities` og `Person.municipality` beholdes gjennom
overgangen. Migreringen følger disse prinsippene:

1. Nytt schema legges til additivt i senere leveranser.
2. Legacytekst bevares ordrett; første migrering overskriver ingen tekstfelt.
3. Schema- og datamigrasjoner utfører ingen eksterne API-kall.
4. Deterministisk splitting produserer kandidater, ikke sannhet.
5. Entydige treff mot kontrollerte offentlige koder kan få egen kontrollert
   backfill; bare reelt uavklarte eller tvetydige treff får reviewstatus.
6. Ingen OrganizationPlace blir offentlig som migreringsbivirkning.
7. Ingen PersonPlace får koordinat-, Google-persondata- eller kartscope.
8. Legacy og strukturert projection sammenlignes i shadow mode.
9. PUBLIC fortsetter på legacyfelt til additive API-felt, consumer og staging
   er verifisert.
10. Fysisk fjerning av legacyfeltene krever en separat senere gate.

Tvetydighetsreview skal minst dekke like stedsnavn i flere områder, flere steder
i én streng, historiske kommune-/fylkesnavn, utenlandsk sted uten landkode og
tekst som beskriver et område fremfor ett sted.

En uavklart/tvetydig kandidat kan aldri bli public- eller map-eligible, drive en
tenantregel eller brukes som verifisert match. Den kan heller ikke utløse skjult
providerbruk eller global Place-mutasjon.

## 16. Import 2.0-grense

ADR-012 implementerer ikke Import 2.0, men fastsetter stedskontrakten for det
framtidige arket `STEDER`. Kontrakten skal kunne bevare:

- kildeark og source place assignment ID
- entity type og entity source ID
- original stedsverdi
- land, region/fylke, kommune og locality/by/tettsted
- stedstype, primærstatus og eksplisitt offentlig status
- proveniens og reviewstatus

Planlagt pre-commit-flyt er:

```text
rå tekst
→ normalisert kandidat
→ kontrollert offentlig kode-/provideroppslag ved behov
→ duplicate-/similarity-kontroll
→ tvetydighetsreview bare ved reell konflikt/uavklart kandidat
→ eksisterende, source-backed eller brukerbekreftet Place
→ OrganizationPlace eller PersonPlace
→ eventuelt rådgivende tenantforslag
→ eksplisitt commit
```

Like stedsverdier i samme jobb skal senere kunne løses samlet. Importrevieweren
kan i normalflyten velge eksisterende Place, bekrefte en entydig offentlig
kildekandidat eller opprette et manuelt brukerbekreftet Place uten
plattform-superadmin. Place-opprettelse er en eksplisitt pre-commit-beslutning;
bare globale registerkonflikter, multi-domain-konflikter og forvaltningshandlinger
eskaleres til plattformcapability. Dette er fase 5D/7-UX og ikke implementert
runtime her.

Stedsdelen av import-commit skal aldri kjøre Google-søk, geokoding, kartlasting
eller providerhenting. Den skal aldri gjøre et sted offentlig eller opprette
tenantassignment automatisk. Dagens generelle import kan skrive publication når
input og review eksplisitt ber om det; ADR-012 forbyr den skjulte
stedsbivirkningen, ikke en separat eksplisitt publicationbeslutning etter
ADR-004/ADR-011.

## 17. Editor actor-only map

Editor får senere en Organization-only kartarbeidsflate. Vanlig tenantbruker
kan bare se canonical Organizations med aktiv assignment til brukerens aktive
tenant og øvrige gyldige capabilities. Plattform-superadmin kan filtrere flere
tenants innen samme eksakte SharingDomain.

Den vanlige stedflyten er søk → velg eller opprett Place gjennom den
kontrollerte server-side tjenesten → knytt til canonical aktør/person → lagre
typed relasjon → eventuelt publiser OrganizationPlace med separat capability.
`Opprett nytt sted manuelt` er tilgjengelig når ingen klar kildekandidat finnes.
En bruker som mener eksisterende global Place er feil, sender inn en rettelse;
brukeren får ikke vilkårlig global edit-rett.

Kart og resultatliste skal være synkronisert og kunne filtrere på:

- tenant innen autorisert scope
- kategori, underkategori og shared editorial tags
- private internal tags bare for aktiv tenant
- PUBLIC-status
- med/uten bilde
- med/uten strukturert sted
- med/uten gyldig kartposisjon
- Organizations med flere assignments

Kartpayloaden skal ikke inneholde personer, e-post, telefon, private notater,
andre tenanters internal tags, private bildeoriginaler, image credentials eller
agreement-/auditdetaljer.

Kartet kan bruke eksisterende godkjent PUBLIC-image projection eller
systemfallback. Det skal aldri opprette image assets, selections, releases eller
andre writes. Browser-aktiv Codex er hard gate før kart-UI implementeres.

## 18. PUBLIC actor-only map

PUBLIC får senere en Organization-only kartvisning. En markør krever samtidig:

- publisert canonical Organization med entydig PUBLIC-identitet etter ADR-011
- eksplisitt offentlig OrganizationPlace
- tilstrekkelig source-backed/system- eller brukerbekreftet Place etter
  datakvalitetsstatus; aldri tvetydig/review-required
- gyldig, godkjent og ikke utløpt PlaceCoordinate
- aktiv PUBLIC-kartfeature og oppfylt juridisk/providergate

Én canonical Organization med tre assignments og ett OrganizationPlace gir én
markør. Tre reelle offentlige OrganizationPlaces kan gi tre markører.
Markøren representerer Organization–Place, aldri tenantassignment.
Map eligibility følger data-, publication-, provider- og featuregatene og krever
ikke plattform-superadmin.

Assignments, private overlays og internal tags eksponeres ikke. Personer får
aldri kartpunkt. Organizations uten gyldig koordinat forblir i den offentlige
resultatlisten. Kartet er et supplement til en fullverdig, keyboardtilgjengelig
liste og bruker samme canonical Organization-ID og godkjente image projection
som øvrig PUBLIC.

PUBLIC kan senere filtrere på kategori, underkategori, shared editorial tags,
land, region/fylke, kommune og sted. Interne assignments er ikke PUBLIC-filter
eller PUBLIC-data uten en separat produktbeslutning.

## 19. Dataminimerte kartprojeksjoner

Målarkitekturen bruker separate read-only projections, konseptuelt:

- `EditorActorMapProjection`
- `PublicActorMapProjection`

Eksakte serializer-, service- og URL-navn avgjøres senere. En markørpayload skal
bare inneholde det nødvendige, eksempelvis canonical Organization-ID,
OrganizationPlace-ID, aktørnavn, stedsnavn, latitude/longitude,
koordinatpresisjon, thumbnail/fallback, nødvendige filter-ID-er og offentlig
aktørlenke i PUBLIC.

Editor-projeksjonen kan ha scoped status- og filterverdier, men ingen kontakter
eller andre private data kartet ikke trenger. Public-projeksjonen inneholder
aldri assignments, overlays eller internal tags. Begge projections er
read-only, gjør ingen provideroppslag og utfører ingen state-write.

## 20. Google Maps’ avgrensede rolle

Google Maps er en valgfri kart- og mulig søkeadapter, ikke canonical
stedssannhet. Maps JavaScript API kan senere vise egne, godkjente aktørmarkører,
clustering og kartnavigasjon.

En konkret Google Places-integrasjon er ikke ubetinget godkjent. Gjeldende EØS-
vilkår begrenser Places-innhold til opplistede brukstyper; Kreative Norge CRM
kan ikke uten juridisk kontroll anta at generisk kulturaktørsøk er omfattet.
Videre kan bare latitude, longitude og Place ID fra Places API brukes visuelt
med et kart etter vilkårene som ble kontrollert 2026-08-31. Markørnavn og annen
tekst skal derfor komme fra CRM-ets provider-nøytrale, lovlig etablerte Place-
data, ikke fra en kopiert Google-respons.

Google kan etter en egen godkjent gate brukes til autocomplete/stedssøk,
særlig for utenlandske steder, en providerreferanse eller et tidsbegrenset
koordinatoppslag. Et slikt Place-oppslag mottar bare eksplisitt stedsverdi og
nødvendig geografisk kontekst, aldri personidentitet eller øvrige private
CRM-data. Google skal ikke:

- eie Place eller fylle en varig kopi av Google Places
- bestemme tenant eller være nødvendig for vanlig stedredigering
- være nødvendig for lister, søk, matching, importreview eller tenantforslag
- brukes til personkart eller motta persondata/private CRM-data
- kjøre under import-commit eller som skjult aktørberikelse
- være eneste koordinatkilde
- brukes til ruter, Street View, heatmaps, live-posisjon eller egen forbudt
  polygonanalyse i MVP

All Google-funksjonalitet kan deaktiveres uten at Place, OrganizationPlace,
PersonPlace, tenantforslag, importreview eller lister slutter å fungere.
Google-coordinate persistence er en separat default-off gate og kan ikke
aktiveres før juridisk/providerbruk, lagringsplassering, backup/retensjon,
featuregate-uavhengig purge, restore-reconciliation, audit og stagingevidens er
godkjent. En kart- eller lookup-gate gir aldri i seg selv rett til å lagre rå
Google-koordinater.

Editor, PUBLIC og enhver framtidig Google-consumer omfattes dessuten av den
separate Customer Application-vilkårsgaten i punkt 22 før aktivering.

## 21. Nøkler, sikkerhet, kostnad og observability

En senere Google-aktivering skal bruke minst privilegium:

- separat Editor browser key
- separat PUBLIC browser key
- separat servercredential bare dersom et godkjent serverbasert API faktisk
  tas i bruk
- separat lokal utviklingsnøkkel ved behov
- eksakte website-origin/referrer-restriksjoner for browsernøkler
- IP- eller annen støttet restriksjon for serverkall
- API-allowlist per nøkkel og deaktivering av ubrukte tjenester
- miljøisolasjon mellom staging og produksjon
- separate kvoter, overvåking og budsjettvarsler

Browsernøkkelen behandles som en eksponert klientcredential som beskyttes med
restriksjoner. Servercredentials ligger aldri i frontendbuild, API-respons eller
Git. Logger sanitiseres, providerquery inneholder ingen PII, featuregater er
fail-closed, og bruk/kostnad observeres aggregert. Budsjettvarsler alene
stopper ikke forbruk; kvoter og kontrollert avslag må testes.

Place-select/create, typed relasjon, publication, koordinatvalg og globale
forvaltningshandlinger autoriseres server-side, auditeres og bruker revision-/
stale-kontroll etter handlingens capability. Observability for tidsbegrenset
providerdata skal vise policyversjon, kommende frister, purge-lag/-feil og
restore-reconciliation-status uten rå koordinater. Ukjent policy, overskredet
frist, mislykket purge eller ikke-grønn reconciliation blokkerer relevante
providerdata read/write og kartprojection. Purgejobben er uavhengig av
featuregater og må fortsette når lookup eller kart er slått av.

Denne leveransen oppretter ikke prosjekt, API-er eller nøkler.

## 22. Personvern og attribusjon

MUSIKKONTORET AS er juridisk behandlingsansvarlig for CRM-behandlingen og det
felles SharingDomainet. Fredrik Forssman er produkteier, faglig ansvarlig og
operativ kontaktperson, ikke juridisk behandlingsansvarlig. ADR-012 åpner ikke
den beslutningen på nytt.

Google Maps Platforms gjeldende EØS-vilkår sier at kunden ikke skal sende
sluttbrukerens personidentifiserende opplysninger eller persondata til Google,
og at Google-tjenestene ved normal bruk selv samler blant annet IP-adresse,
søketermer og koordinater. Google og kunden er omfattet av de inkorporerte
controller-controller-vilkårene. Den konkrete rolle-, behandlingsgrunnlags- og
informasjonsvurderingen er en ekstern juridisk gate.

Ingen personnavn, e-post, telefon, personsted, aktørrelasjon, notat, private tag
eller annen privat CRM-kontekst sendes til Google for kartformål.

PUBLIC-utgangspunktet er at Google-komponenten først lastes etter uttrykkelig
brukerhandling, for eksempel `Vis interaktivt kart`, eller gjennom en senere
juridisk godkjent consent-management-løsning. Dette er en dataminimerende
arkitekturbeslutning, ikke en påstand om at ett klikk alene oppfyller alle
rettslige krav. Liste, søk og aktørsider fungerer før lasting.

Google Maps Platforms gjeldende EØS-vilkår krever i tillegg at brukervilkårene
til hver relevant Customer Application:

- opplyser om at applikasjonen inneholder Google Maps-funksjoner og -innhold
- sier at bruken er underlagt den til enhver tid gjeldende
  [Google Maps End User Additional Terms of Service](https://maps.google.com/help/terms_maps/)
  og [Google Privacy Policy](https://policies.google.com/privacy)
- støttes av egnet håndheving, inkludert suspensjon eller avslutning av tilgang
  til Google Maps-innhold/-funksjoner når sluttbrukeren ikke følger de relevante
  vilkårene

Dette er en selvstendig produksjonsgate, separat fra CRM-ets
personvernerklæring, cookie-/consentvurdering, `Vis interaktivt kart`, Google-
attribusjon, Kartverket-attribusjon, controller-controller-vilkårene og avtalen
for delte CRM-data. Juridisk kontroll skal fastsette endelig ordlyd,
versjonering, lenkeplassering, tilgang før eller ved bruk og eventuell
akseptmekanisme for Editor, PUBLIC og framtidige consumers. Gaten reverifiseres
ved implementeringsstart, stagingaktivering, produksjonsaktivering og vesentlig
providerendring. Uavklart eller foreldet vilkårsgate blokkerer Google-funksjonen;
endret URL eller navn påvirker aldri Place-identiteten.

Google Maps-attribusjon og eventuelle tredjepartsattributter skal forbli synlige
og uendrede. Nye integrasjoner skal følge den da gjeldende `Google Maps`-
attribusjonen. Kartverket krediteres etter gjeldende CC BY 4.0-vilkår. Dynamisk
providerattribusjon skal ikke blindt caches i PlaceProviderReference; adapteren
må kunne vise den til enhver tid påkrevde runtimeattribusjonen.

## 23. Provider outage og listefallback

Editor og PUBLIC fungerer uten Google. Ved manglende nøkkel, avslått gate,
providerfeil, timeout, kvote, blokkert JavaScript, manglende godkjent
brukerhandling/consent, uavklart Customer Application-vilkår, ikke-grønn
restore-reconciliation, ukjent providerpolicy, utløpt koordinat eller
utilgjengelig kartscript skal:

- listevisning bestå
- ikke-provideravhengig søk og filtre bestå
- Organizations ikke forsvinne
- ingen data endres
- ingen skjult retry-loop starte
- forståelig status vises
- kart kunne aktiveres senere uten datamigrering

Providerfeil er en visnings-/adapterfeil, ikke en feil ved Place-identiteten.

## 24. Featuregates og shadow

Senere implementering skal ha separate, default-off gater for minst:

- structured Place read
- structured Place write
- legacy/structured shadow projection
- geographic tenant suggestions
- provider lookup
- provider-coordinate persistence
- Editor actor map
- PUBLIC actor map

Eksakte settingsnavn avgjøres senere. En frontendkomponent aktiverer aldri
automatisk read/write eller providerbruk.

Structured Place write-gaten omfatter den kontrollerte create-/reuse-tjenesten,
men gir ingen frontend eller tenantrolle skjult rett til global mutasjon.
Provider-coordinate persistence forblir avslått inntil den separate backup-/
retensjons-/purge-/restorekontrakten er grønn. Providerpålagt disable, purge og
restore-reconciliation er sikkerhetskontroller, ikke av/på-funksjoner, og kan
aldri stoppes av featureflag, rollback eller deaktivert kart.

PUBLIC actor map kan ikke aktiveres før ADR-011s canonical PUBLIC-projection er
klar, offentlige OrganizationPlaces er kontrollert, provider-/personvernvilkår
og Customer Application-vilkår er reverifisert, restore-reconciliation er
grønn, listefallbacken er bevist og credentials/kvoter er sikkert konfigurert.
Tilsvarende vilkårsgate gjelder Editor eller enhver framtidig consumer som
eksponerer Google Maps-funksjoner eller -innhold.

Shadow skal være read-only, sammenligne legacy og strukturert projection med
forklarte avvik og aldri opprette Place, relasjon, publication, coordinate eller
assignment.

## 25. Alternativer vurdert

### Google Places som canonical stedstabell

Avvist fordi det gjør identitet og kjernefunksjoner provideravhengige, inviterer
til ulovlig eller ustabil kopiering og ikke gir offentlig norsk kodehistorikk.

### Bare fritekststeder

Avvist fordi tvetydighet, flere steder, historiske koder, tenantforslag og
kontrollert kartprojection ikke kan håndteres pålitelig.

### Tenant- eller SharingDomain-eid Place

Avvist fordi offentlig geografi kan gjenbrukes trygt. Privat scope ligger på
canonical CRM-objekt og typed relasjon; dupliserte Place-rader ville skape drift.

### Obligatorisk plattformreview for normal Place-opprettelse

Avvist fordi det gjør vanlig aktør-, person- og importarbeid avhengig av en
sentral flaskehals. Kontrollert servervalidering, duplicate-/similarity-kontroll,
proveniens og audit dekker normal source-backed og brukerbekreftet opprettelse;
plattformforvaltning reserveres for globale konflikter og registerendringer.

### Generisk polymorf stedskobling

Avvist fordi typed OrganizationPlace og PersonPlace gir klarere constraints,
publication og et eksplisitt forbud mot personkart.

### Utsette PersonPlace

Avvist av prosjekteiers godkjente retning. Strukturert personsted er nødvendig
for profil, matching, filtrering og forslag, men trenger ingen koordinat eller
kart.

### Kart for både Organizations og Persons

Avvist av personvern-, dataminimerings- og produktgrunner. Kartet løser
aktørreisen; PersonPlace skal ikke utvide provider- eller kartscope.

### Automatisk assignment fra geografi

Avvist fordi forslag ikke er identitet, medlemskap eller autorisasjon, og fordi
alle tenants kan overlappe.

### PostGIS og polygonregler i MVP

Avvist som unødvendig kompleksitet. Administrative koder gir deterministiske,
versjonerte regler, og gjeldende Google-vilkår forbyr dessuten Places-
koordinater som input til punkt-i-polygon-analyse.

## 26. Begrunnelse

En liten, global Place-modell skiller varig identitet fra providerlivssyklus og
lar norske offentlige kilder være autoritative uten å blokkere utenlandske
steder. Typed relasjoner holder privacy, publication og domain-scope tydelig.
Separate koordinater gjør kartet valgfritt og reverserbart. Versjonerte
kodebaserte regler er forklarbare og auditerbare, mens rådgivende forslag
bevarer menneskelig kontroll og ADR-011s autorisasjonsgrense.

Actor-only projections løser kartreisen med minst mulig data og gjenbruker
eksisterende canonical Organization- og imagekontrakter. Listefallback og
provider-nøytral kjerne gjør at Google kan slås av uten domenefeil eller
datamigrasjon.

## 27. Konsekvenser og tradeoffs

Positive konsekvenser:

- stabil intern stedssannhet uavhengig av Google
- selvbetjent, kontrollert Place-normalflyt uten plattform-superadmin som
  obligatorisk mellomledd
- norsk kode-/navnehistorikk kan spores og oppdateres kontrollert
- flere steder per Organization og Person uten å blande semantikk
- eksplisitt publication og klar PersonPlace-no-map-invariant
- forklarbare tenantforslag uten autorisasjonsbivirkning
- kart kan deaktiveres uten å miste aktører eller steder
- additiv, reviewbasert legacyovergang

Kostnader og ulemper:

- flere modeller, constraints, adapters og kildeversjoner må forvaltes
- duplicate-/similarity-kontroll og global konfliktforvaltning må hindre at
  selvbetjening fragmenterer canonical Place
- tvetydige legacyverdier krever redaksjonelt review
- offentlige kodeendringer og providerreferanser krever livssyklusarbeid
- Google Places kan være juridisk uegnet for deler av foreslått søk og kan ikke
  planlegges som obligatorisk funksjon
- kart krever egne privacy-, attribusjons-, sikkerhets-, kostnads- og
  tilgjengelighetsgater
- tidsbegrenset providerdata krever en separat backup-/purge-/restorekontrakt
  og kan ikke uten videre ligge i den aktive standardbackupen
- actor-only map må vente på ADR-011s canonical PUBLIC- og assignmentgrunnmur

## 28. Migreringsrekkefølge

Senere implementering skal være additiv og følge denne rekkefølgen:

1. Place og offisielle source/providerreferanser.
2. Kontrollert server-side search/select/create/reuse med duplicate-/similarity-
   kontroll, proveniens, audit og avgrenset global forvaltning.
3. OrganizationPlace og PersonPlace som nullable/additive relasjoner.
4. Legacy raw-text snapshot/proveniens.
5. Read-only legacy inventory og kandidatparser.
6. Kontrollert norsk code/source matching uten eksterne writes.
7. Shadow projection mellom legacytekst og structured places.
8. Review av bare tvetydige aktør- og personsteder.
9. GeographicTenantRuleSet og shadow suggestions.
10. Structured write path i Editor, inkludert eksplisitt publication.
11. Additive API-felt.
12. PUBLIC structured-place shadow.
13. Varig PlaceCoordinate-livssyklus for lovlig retinerbare kilder.
14. Separat default-off provider-coordinate persistence med bevist lagrings-,
    backup-, purge- og restore-reconciliation-kontrakt.
15. Editor actor-map projection.
16. Editor actor-only map etter relevante juridiske/provider-/vilkårsgater.
17. PUBLIC actor-map projection.
18. PUBLIC actor-only map etter juridiske/provider-/vilkårsgater.
19. Import 2.0 STEDER-kontrakt.
20. Legacy write deprecation.
21. Fysisk cleanup bare i separat senere gate.

Hver leveranse krever egen featuregate, akseptansekriterier, negative tester,
stagingbevis og rollback. Ingen leveranse kan ha skjulte public-, assignment-
eller providerwrites. Global merge/redirect/deaktivering og provideropprydding
forblir separate forvaltningshandlinger og er ikke del av normal Place-create.

## 29. Testkrav

### Place-normalflyt og global forvaltning

- autorisert tenantbruker kan velge eksisterende Place
- autorisert tenantbruker/importreviewer kan opprette source-backed canonical
  Place uten plattform-superadmin
- entydig offentlig kilde kan bekreftes og opprettes/gjenbrukes i normalflyten
- autorisert bruker kan opprette manuelt, brukerbekreftet canonical Place med
  påkrevd kontekst og uten ekstra plattformreview
- duplicate-/similarity-kontroll kjører før hver ny opprettelse og gjenbruker
  eksisterende Place når identiteten allerede finnes
- OrganizationPlace knytter canonical Organization og gjelder på tvers av alle
  assignments uten Place-, relasjons- eller markørkopi per tenant
- autorisert bruker kan eksplisitt gjøre OrganizationPlace offentlig når aktiv
  bruker, agreement, membership, assignment, edit-/publication-capability,
  servervalidering og stale-kontroll er grønne
- kart eligibility krever gyldig datakvalitetsstatus og koordinat, ikke
  plattform-superadmin
- tvetydig/review-required Place er aldri public-, map- eller
  tenant-rule-eligible og brukes ikke som verifisert match
- brukerbekreftet Place uten systemvaliderte administrative koder kan knyttes,
  vises og publiseres, men driver ikke GeographicTenantRuleSet
- vanlig bruker kan endre eget autoriserte objekts typed relasjon og sende inn
  rettelse, men ikke vilkårlig mutere eksisterende global Place
- plattformcapability kan merge, redirecte/tombstone og deaktivere referert Place
  samt håndtere globale kilde-, hierarki-, koordinat- og providerkonflikter med
  audit og revision-/stale-kontroll
- råtekst, kilde, basis, versjon, gyldighet og relevant administrativ kontekst
  bevares som proveniens
- alle writes er server-side autoriserte og auditert; frontend utløser ingen
  skjult global mutasjon eller automatisk merge

### Modell og migrering

- Place uten provider eller koordinat
- like labels i ulike land/regioner
- kilde-/ID-namespace, source-ID og providerreference-constraints
- OrganizationPlace- og PersonPlace-scope mot canonical objekt og eksakt
  SharingDomain-kontekst
- tenantbruker kan ikke mutere, merge eller deaktivere eksisterende global
  Place, providerreferanse eller aktivt kartpunkt på tvers av SharingDomains
- globale forvaltningsendringer har capability-, revision-/stale- og auditkrav,
  og referert Place kan ikke slettes destruktivt
- maksimalt ett aktivt primærsted per Organization og per Person dersom
  produktkontrakten bruker primær PersonPlace
- avvisning av duplisert aktiv Organization/Place/type
- latitude-/longitude-range, presisjon, aktiv koordinat og utløp
- maksimalt én aktivt godkjent kartkoordinat per Place; konkurrerende aktivering
  avvises og kontrollert bytte er atomisk og auditert
- byte-/tekstlig uendret legacyverdi
- reverse før writes og eksplisitt blokkering/forward-fix etter semantiske writes

### Tenantforslag

- alle 16 eksplisitte region-/territoriemappings i tabellen
- Svalbard som eksplisitt territorium til Musikkontoret Nord
- utenlandsk/uavklart som det syttende separate regelutfallet, tydelig
  ikke-geografisk
- flere steder gir flere dedupliserte forslag og overlap er tillatt
- forslag skaper aldri assignment eller autorisasjon
- bare systemvaliderte administrative koder kan utløse geografisk forslag
- feil SharingDomain avvises
- gammel og ny regelsettversjon spores og forklares

### Personer

- PersonPlace kan opprettes uten koordinat
- bruker kan velge eller kontrollert opprette canonical Place før PersonPlace
  lagres, uten plattform-superadmin
- PersonPlace-lagring utløser ingen skjulte Google-/providerkall; eksplisitt
  Place-oppslag bruker bare stedsverdi og geografisk kontekst
- Person finnes aldri i Editor- eller PUBLIC-kartprojection
- persondata sendes aldri til provider
- delt Place-coordinate projiseres ikke via PersonPlace
- tekstlig personsted kan fortsatt følge separat publicationkontrakt

### Editor actor map

- vanlig bruker ser bare Organizations assigned til aktiv tenant
- plattform-superadmin bruker bare tillatte tenantfiltre i samme SharingDomain
- private internal tags begrenses til aktiv tenant
- ingen kontaktdata eller private bildeoriginaler finnes i markørpayload
- aktør uten koordinat forblir i listen
- ett sted gir én markør uavhengig av assignments; tre steder gir tre markører
- eksisterende image projection/fallback brukes uten ny image state
- providerfeil gir listefallback uten write eller retry-loop

### PUBLIC actor map

- bare publisert canonical Organization, offentlig OrganizationPlace,
  tilstrekkelig source-backed/system- eller brukerbekreftet Place og gyldig
  koordinat; aldri tvetydig/review-required Place
- ingen personmarkører, assignments, overlays eller internal tags
- canonical aktør returneres én gang per OrganizationPlace
- aktør uten markør forblir i listen
- kart lastes ikke før godkjent brukerhandling/consentmekanisme
- kart av eller Google utilgjengelig bevarer liste og aktørsider uten write
- PUBLIC image-, canonical- og safety-invarianter er uendret

### Provider

- manglende nøkkel, feil origin, timeout, kvote og malformed respons
- utløpt/foreldet providerreference og koordinat
- providerpålagt purge fjerner rå Google-latitude/longitude ved utløp og
  beholder bare lovlig, ikke-rekonstruerbar tombstone-/auditmetadata
- tidsbegrenset rå providerdata finnes ikke etter sin frist i database/cache,
  replika, eksport, kø, logg, `pg_dump`, Borg, Storage Box-snapshot, Cloud Backup
  eller annen kontrollert kopi
- tidsbegrenset rå providerkoordinat er utenfor ordinær langtidsbackup med
  mindre en separat godkjent kjede håndhever samme utløp i hver kortlivet kopi
- backup-/purge-/restore-gaten er grønn før første Google-coordinate write
- restore av eldre backup deaktiverer rå providerdata før lesing og kan ikke
  reaktivere utløpt, skulle-ha-vært-slettet, manglende-kilde-, ukjent-policy-,
  utløpt-referanse- eller nylig ulovlig data
- restore-reconciliation er idempotent og race-sikker, identifiserer policy og
  frist, disable-er før purge og må være grønn før provider-/coordinate-/map-
  lesing eller skriving
- feature-off, rollback og deaktivert kart stopper aldri providerpålagt purge
- varig, lovlig Kartverket-koordinat overlever ordinær backup/restore, mens
  sletting av Google-koordinat bevarer Place, typed relasjoner, publication,
  regler, lovlig Place ID og ikke-rekonstruerbar audit
- aktiv Google-basert markør forsvinner ved utløp/purge, mens aktøren består i
  liste, søk og tekstlig stedspresentasjon
- tombstone, audit og logger kan ikke rekonstruere rå koordinat
- ukjent/foreldet providerpolicy, uløst backupkontrakt, mislykket purge eller
  ikke-grønn restore-reconciliation blokkerer Google-coordinate read/write
- Places-koordinat får providerstyrt utløp og brukes aldri til tenantregel eller
  punkt-i-polygon
- sanitert logging og ingen PII i query eller logg
- default-off gates og separate Editor/PUBLIC/servercredentials
- korrekt Google Maps-/tredjeparts- og Kartverket-attribusjon
- Editor, PUBLIC og framtidige Google-consumers har tilgjengelige, juridisk
  godkjente Customer Application-vilkår som opplyser om Google Maps og lenker til
  gjeldende End User Additional Terms og Google Privacy Policy
- Customer Application-vilkår, personvernerklæring, consent/brukerhandling og
  attribusjon testes som separate porter; uavklart vilkårsgate blokkerer
  aktivering
- nødvendig suspensjon/avslutning av tilgang til Google-funksjoner ved
  vilkårsbrudd kan håndheves etter juridisk godkjent kontrakt

### API og frontend

- additive structured-place-felt mens legacyfeltene består
- OpenAPI-kontrakt og dataminimerte map projections
- fullverdig keyboard-/listefallback
- Playwright-reiser for actor-only kart/listesynkronisering
- Editor-reise for søk, eksisterende valg, source-backed opprettelse, `Opprett
  nytt sted manuelt`, typed kobling og capabilitykontrollert publication
- Import-review løser normale unike stedsverdier uten plattform-superadmin,
  eskalerer bare globale konflikter og gjør ingen providerkall under commit
- eksplisitt test som beviser at personer aldri vises på kart
- browser-aktiv Codex ved senere UI-leveranse

## 30. Staginggater

Hver relevant senere leveranse skal dokumentere:

- eksakt commit og aktive featuregater
- schema-/backfilltellinger og legacyfingerprints
- shadow parity med forklarte avvik
- reviewresultat for tvetydige steder
- search/select, source-backed opprettelse og manuelt brukerbekreftet Place uten
  plattform-superadmin, inkludert duplicate-/similarity-kontroll
- canonical OrganizationPlace uten tenantkopier, capabilitykontrollert
  publication og tvetydige kandidater som feiler lukket for public/map/rules
- Import-review av normale unike stedsverdier uten plattform-superadmin og
  eskalering bare av globale registerkonflikter
- alle regelsettutfall og ingen assignmentwrite
- actor-only projections uten PII/private overlays
- provider outage, feil key/origin, kvote og listefallback
- PUBLIC-kartets brukerhandling/consentmekanisme
- separate, juridisk godkjente Customer Application-vilkår for alle aktive
  Google-consumers, med gjeldende End User Additional Terms- og Privacy-lenker
- default-off Google-coordinate persistence, operativ featuregate-uavhengig
  purge og grønn policy-reconciliation før provider-/coordinate-/map-read/write
- syntetisk bevis for at tidsbegrenset rå providerdata ikke overlever fristen i
  PostgreSQL/cache, Borg, Storage Box-snapshot, Cloud Backup, replika, eksport
  eller logg, og ikke reaktiveres ved full restore
- uendrede PUBLIC image-/safetyinvarianter
- sanitert provider-/applogg uten PII
- backup/restore og prøvd rollback

PUBLIC-kart krever i tillegg ferdig canonical PUBLIC-projection fra ADR-011 og
juridisk/provider-/Customer Application-vilkårsgodkjenning. Ingen staginggate
bestilles av dette ADR-et.

Produksjonsaktivering av enhver Google-flate er blokkert til de relevante
stagingbevisene er grønne, providerregler og Customer Application-vilkår er
ferskt reverifisert og juridisk godkjent, backup-/purge-/restorekontrakten er
operativ og restore-reconciliation er grønn.

## 31. Rollback

Før structured writes kan additivt schema normalt reverseres etter
migrasjonstest, og shadow/gater kan slås av.

Etter structured writes er normal rollback:

- feature-off
- read path tilbake til legacy
- structured writer-disable
- behold Place, relasjoner, proveniens og den koordinat-/providerhistorikken og
  auditen som providerregler fortsatt tillater

Bekreftede steder eller historikk slettes ikke for å simulere rollback. Etter
PUBLIC-kartaktivering kan kartgaten slås av mens liste og legacy/strukturert
tekstvisning består. Ingen canonical Organization eller OrganizationPlace
slettes. Providerfeil krever aldri datamigrasjon for å deaktivere kartet.

Rollback, feature-off eller restore kan aldri sette providerpålagt disable/purge
ut av drift. Et eldre snapshot behandles som ukjent/ikke-godkjent
providerdatatilstand til reconciliation har deaktivert før lesing, kontrollert
policy/frister og purget alt som ikke fortsatt er lovlig. Bare varig data og
lovlig ikke-rekonstruerbar tombstone/audit kan deretter åpnes for bruk.

Fysisk legacycleanup er en egen forward-only-beslutning med backup og separat
rollbackplan.

## 32. Åpne eksterne porter

Før berørte funksjoner kan implementeres eller aktiveres må følgende avklares:

- konkret Google Maps-/Places-bruk under da gjeldende EØS-vilkår og faktisk
  billing account/prosjekt
- hvilke EØS-/andre Maps-vilkår som gjelder for faktisk faktureringsadresse,
  prosjekt og integrasjonstilstand
- om foreslått Places-søk faller innen en tillatt bruk; inntil da er det
  blokkert, valgfritt og erstattbart
- gjeldende caching, retention, Place ID-reverifisering, koordinatbruk og
  attribusjon per aktiv Google-tjeneste
- godkjent lagrings-, backup-, purge- og restore-reconciliation-kontrakt som
  håndhever tidsbegrenset providerdata i alle kopier; katastrofebackupkonsekvensen
  er en konservativ slutning som krever juridisk/kontraktsmessig kontroll
- juridisk godkjent ordlyd, versjonering, plassering, tilgjengelighet og
  håndheving for Customer Application-vilkår i Editor, PUBLIC og framtidige
  Google-consumers, med gjeldende End User Additional Terms- og Privacy-lenker
- gjeldende SSR API-/ID-semantikk, Kartverket-lisens og attribusjon for planlagt
  uttrekksvolum
- gjeldende SSB Klass-versjoner, korrespondanser og valgt Svalbard-kildenamespace
- endelig personvern-/samtykke-/brukerhandlingsløsning for PUBLIC-kart
- oppdatert personvernerklæring og dokumentasjon av hva provider mottar
- juridisk kontroll før Google eller delte persondata aktiveres i produksjon
- endelig ordlyd og versjonering av avtalen for tilgang til delte CRM-data
- dokumentasjon av behandlingsgrunnlag, formål, rettigheter og interne
  ansvars-/arbeidsrutiner
- sikker key-/project-/quota-/budget-konfigurasjon

Providerregler og Customer Application-vilkår skal reverifiseres ved
implementeringsstart, stagingaktivering, produksjonsaktivering og vesentlig
providerendring.

Browser-aktiv Codex er i tillegg en hard produkt-/implementeringsgate før kart-
eller Import 2.0-UI bygges.

## 33. Ferdigdefinisjon

ADR-012 er varig besluttet når:

- dette dokumentet er merget med status
  `Godkjent målarkitektur – ikke implementert`
- ADR-indeks, roadmap, prosjektstatus og relevante arkitekturdokumenter peker til
  samme beslutning
- offisielle kilder og kontrolldato er registrert
- selvbetjent Place-normalflyt og avgrenset global plattformforvaltning er
  entydig beskrevet i ADR-et og nødvendige korte kryssreferanser
- restore-sikker providerdata- og Customer Application-vilkårsgate er entydig
  beskrevet uten å framstille backupslutningen som et uttrykkelig Google-krav
- ingen dokumentasjon omtaler Place, tenantregler eller kart som implementert

Målarkitekturen er først implementert når alle relevante trinn i den additive
migreringsrekkefølgen er gjennomført med egne godkjenninger, negative tester,
stagingbevis og rollback, autoriserte tenantbrukere/importreviewere kan bruke den
kontrollerte Place-normalflyten uten plattformflaskehals, providerdata kan ikke
reaktiveres gjennom restore, og relevante Customer Application-vilkår er
juridisk godkjent og tilgjengelige. Legacycleanup er separat. Godkjent ADR betyr
ikke runtimeaktivering.

## 34. Offisielle eksterne kilder med kontroll-/hentedato

Alle kilder nedenfor ble kontrollert 2026-08-31. De støtter dagens
vilkårsvurdering, men lenker, versjoner, API-er og juridiske krav skal
reverifiseres ved implementeringsstart og på nytt før produksjonsaktivering.

### Google Maps Platform og Google Cloud

- [Maps JavaScript API overview](https://developers.google.com/maps/documentation/javascript/overview)
  og [loading guidance](https://developers.google.com/maps/documentation/javascript/load-maps-js-api):
  interaktive kart, egne markører/datalag og kontrollert lasting.
- [Maps JavaScript API policies](https://developers.google.com/maps/documentation/javascript/policies):
  bruk, lagring og attribusjon for Maps JavaScript API.
- [Place IDs](https://developers.google.com/maps/documentation/places/web-service/place-id):
  Place ID kan lagres, kan endres/bli foreldet og har nå en anbefalt
  reverifiseringspraksis.
- [Places API policies and attribution](https://developers.google.com/maps/documentation/places/web-service/policies):
  caching-unntak, offentlig tilgjengelige bruker-/personvernvilkår, Google
  Maps-attribusjon og skille mellom Google- og eget innhold.
- [Google Maps Platform EEA Terms of Service](https://cloud.google.com/terms/maps-platform/eea):
  gjeldende EØS-regime, no-scraping/no-caching-unntak, personvern,
  controller-controller-vilkår, Customer Application-vilkår med End User
  Additional Terms-/Privacy-lenker, håndheving og forbud mot Places-koordinater
  i punkt-i-polygon. Siden viste siste endring 2026-08-26 ved kontrollen.
- [EEA Service Specific Terms](https://cloud.google.com/terms/maps-platform/eea/maps-service-terms):
  Places-bruk med kart og gjeldende midlertidig koordinatcache. Siden viste siste
  endring 2026-06-10 ved kontrollen.
- [Places API permitted uses for EEA customers](https://cloud.google.com/terms/maps-platform/eea-places-api-permitted-uses):
  uttømmende brukstyper som krever konkret juridisk vurdering for CRM-et.
- [Google Maps End User Additional Terms of Service](https://maps.google.com/help/terms_maps/):
  den gjeldende sluttbrukerlenken som Customer Application-vilkårene skal vise;
  siden viste siste endring 2026-01-27 ved kontrollen.
- [Google Privacy Policy](https://policies.google.com/privacy): gjeldende
  personvernlenke som Customer Application-vilkårene skal vise; siden var
  gjeldende fra 2026-05-26 ved kontrollen.
- [Google Maps Platform API security guidance](https://developers.google.com/maps/api-security-best-practices):
  separate og restriktede browser-/serverkeys, API-allowlist og sikker lagring.
- [Manage Google Maps Platform costs](https://developers.google.com/maps/billing-and-pricing/manage-costs):
  kvoter, overvåking og budsjettvarsler.
- [Google Controller-Controller Data Protection Terms](https://business.safety.google/controllerterms/):
  inkorporert behandlingsrollegrunnlag som må kontrolleres juridisk ved konkret
  aktivering.

Ingen av de kontrollerte Google-kildene beskriver katastrofebackup eller restore
som et særskilt unntak fra slettefristen. Restore-sikkerheten i dette ADR-et er
derfor en konservativ arkitektur-/compliance-slutning, ikke et sitat eller et
uttrykkelig Google-krav om Borg, Storage Box eller Cloud Backup.

### Kartverket og Geonorge

- [Kartverket: Stadnamndata](https://www.kartverket.no/api-og-data/stedsnavndata)
  og [brukerrettledning for stedsnavn-API](https://www.kartverket.no/api-og-data/stedsnavndata/brukarrettleiing-stadnamn-api):
  SSR, ID-typer, språk, navnetype, kommune og representasjonspunkt.
- [Kartverkets stedsnavn-API/OpenAPI](https://api.kartverket.no/stedsnavn/v1/):
  gjeldende maskinlesbar kontrakt; adapteren skal tåle endret endpoint/schema.
- [Kartverkets vilkår for åpne data](https://www.kartverket.no/api-og-data/vilkar-for-bruk):
  CC BY 4.0, `© Kartverket` og særskilt kildeangivelse ved systematisk eller
  vesentlig SSR-uttrekk. Siden var oppdatert 2026-07-21 ved kontrollen.
- [Geonorge produktspesifikasjon Stedsnavn](https://register.geonorge.no/register/versjoner/produktspesifikasjoner/kartverket/stedsnavn)
  og [Geonorge varsler](https://register.geonorge.no/varsler): skille mellom
  sted, stedsnavn og skrivemåte samt endringsvarsling.

### Statistisk sentralbyrå – Klass

- [Kommuneinndeling, klassifikasjon 131](https://www.ssb.no/klass/klassifikasjoner/131/versjoner):
  gjeldende og historiske kommuneversjoner; 2026-versjonen var gjeldende ved
  kontrollen.
- [Fylkesinndeling, klassifikasjon 104](https://www.ssb.no/klass/klassifikasjoner/104/versjoner):
  gjeldende og historiske fylkesversjoner; Svalbard er ikke et ordinært fylke i
  denne klassifikasjonen.
- [Klass API guide](https://data.ssb.no/api/klass/v1/api-guide.html): read-only
  kode-, tids-, endrings- og korrespondanseendepunkter samt CC BY 4.0.
- [SSB Notater 2025/7: Standarder for fylkes- og kommuneinndeling](https://www.ssb.no/befolkning/regioner/artikler/standarder-for-fylkes-og-kommuneinndeling/_/attachment/inline/23ab1eb4-8370-4e6c-b0a6-d8f6d3be6d9c%3A2be49847a056e45f5cd250bef99e07c4ce96306c/NOT2025-07.pdf):
  gyldighetsperioder, historikk, korrespondanser og risiko ved å bruke kode eller
  versjons-ID alene som varig identitet.
