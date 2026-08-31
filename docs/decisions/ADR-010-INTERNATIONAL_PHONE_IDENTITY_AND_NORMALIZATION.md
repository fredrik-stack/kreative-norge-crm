# ADR-010: Internasjonal telefonidentitet og normalisering

## Status

Godkjent av prosjekteier 2026-08-25 etter uavhengig frozen-head-review uten funn og merget til `main` med PR #56 som `e0c38162a7e0b0c8b90daf7387a1682e44370f33`.

Beslutningen er implementert gjennom fase 4A–4H innen avtalt fase-4-scope og
teknisk stagingverifisert 2026-08-26. Etter to remediation-/polishrunder
gjennomførte prosjekteier siste manuelle smoke og [godkjente resultatet
2026-08-29](../status/PHASE_4_OWNER_APPROVAL_2026-08-29.md). Nåstatus er
`PHASE 4 = CLOSED / VERIFIED`. ADR-010 presiserer fortsatt bare telefonsporet i
ADR-005; full relasjonsspesifikk kontaktpublisering er ikke implementert.

**Beslutningsdato:** 2026-08-25

## Forhold til tidligere ADR-er

Denne beslutningen presiserer og viderefører:

- [ADR-002](ADR-002-PERSON_CONTACT_MODEL.md): `PersonContact` er målmodellen for flere kontaktkanaler per person.
- [ADR-004](ADR-004-IMPORT_ARCHITECTURE.md): import skal gå gjennom normalisering, validering, matching, review og eksplisitt commit.
- [ADR-005](ADR-005-CONTACT_ARCHITECTURE.md): `PersonContact.value` skal bevares som presentert verdi, mens en additiv normalisert sammenligningsverdi inngår i målmodellen.

ADR-010 presiserer ADR-005 for telefonnummer. Det erstatter ikke ADR-005 og endrer ikke skillet mellom intern kontakt, primærkontakt og offentlig publisering.

Dagens implementerte tenantisolasjon fra ADR-001 gjelder til ADR-011s separate
gater eventuelt aktiveres. Publiseringsskillet fra ADR-003 gjelder uendret.

**Målarkitekturpresisering 2026-08-31:**
[ADR-011](ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md)
er godkjent, men ikke implementert. Dagens telefonlagring og matching forblir
tenant-scopet. I målarkitekturen betyr ADR-010s cross-tenant-forbud at lesing,
matching og skriving utenfor eksakt SharingDomain, eller uten gyldig agreement,
membership og capability, skal avvises. Privacy-minimert matching mellom
tenants i samme eksakte SharingDomain er tillatt etter ADR-011s porter. E.164 er
fortsatt bare et sterkt signal, aldri personidentitet eller automatisk merge.

## Bakgrunn og mellomtilstand ved beslutningsdatoen

Fase 3 og fase 3F er `CLOSED / VERIFIED`. Bildearkitekturen er ikke del av denne beslutningen.

Ved beslutningsdatoen hadde aktiv kode følgende overgangsmodell for telefon:

- `Person.phone` og `Organization.phone` er nullable tekstfelt uten egen kanonisk sammenligningsverdi.
- `PersonContact` lagrer `type`, fri `value`, `is_primary` og global `is_public`, men ingen telefonspesifikk normalisert verdi.
- `Tenant` har ingen eksplisitt standardregion for telefon.
- `crm.services.person_contacts` trimmer bare ytre whitespace når direkte personfelt synkroniseres til primær kontakt.
- importens `normalize_phone()` komprimerer whitespace, men parser eller validerer ikke telefonnummer og produserer ikke E.164.
- dagens personmatching sammenligner navn sammen med eksakt rå telefontekst i `Person.phone` eller `PersonContact.value`.
- dagens serializers eksponerer og godtar de eksisterende tekstfeltene uten en felles internasjonal telefonkontrakt.
- PUBLIC viser fortsatt den lagrede presentasjonsverdien når gjeldende publiseringsregler tillater det; direkte `Person.phone` brukes ikke som PUBLIC-fallback.

Dette betyr at formater som `+47 900 12 345`, `0047 90012345` og `900 12 345` ikke har en stabil felles identitet. Nasjonale numre kan heller ikke tolkes sikkert uten eksplisitt regionkontekst.

## Problem

Editor, API, import, matching, reparasjonsverktøy og organisasjonstelefon kan ellers utvikle ulike regler for samme nummer. Rå strengsammenligning gir falske forskjeller, mens skjult antakelse om Norge kan gi feil land, feil matching og utrygg datamigrering.

Full Import 2.0 trenger derfor en stabil telefonkontrakt før telefon kan brukes til trygg matching og review.

## Beslutning

### 1. E.164 er kanonisk telefonidentitet

Et gyldig telefonnummer skal ha en maskinell kanonisk sammenligningsverdi i E.164-format. Eksempel:

```text
+47 900 12 345 -> +4790012345
```

Den kanoniske verdien brukes til:

- sammenligning
- deduplisering innen avtalte scopes
- importmatching
- idempotens
- validering

Den menneskevennlige eller importerte presentasjonsverdien bevares separat. ADR-et beslutter ikke at eksisterende `value`- eller `phone`-felt skal overskrives med E.164.

En extension er ikke del av E.164-identiteten. Extensions er utenfor MVP og hele fase 4.

### 2. Etablert telefonbibliotek bak én domenegrense

Målarkitekturen bruker Google libphonenumber-modellen gjennom en egnet Python-implementasjon, normalt `phonenumbers`. Det skal ikke utvikles en egen internasjonal telefonparser.

Eksakt dependency-versjon velges og pinnes først i fase 4C. Biblioteket skal kapsles bak én intern telefonadapter/domenegrense slik at Editor, API, import, matching, eksport og reparasjonsverktøy bruker samme kontrakt.

### 3. Eksplisitt regionkontekst

Nasjonalt skrevne numre krever eksplisitt regionkontekst. En norsk tenant eller en konkret importjobb kan for eksempel ha `NO` som standardregion, men regionen er tolkningskontekst og ikke del av telefonnummerets identitet.

Et nummer som starter med internasjonalt `+` skal tolkes etter sin egen landkode og skal ikke være avhengig av standardregionen.

Norge skal ikke brukes som skjult universell gjetning. Hvis en nasjonal verdi mangler tilstrekkelig kontekst, skal utfallet kreve review i stedet for automatisk kanonisering.

Den eksakte additive utformingen av tenant- og importregion, inkludert felt- og typenavn, avgjøres ved implementasjon så lenge konteksten er eksplisitt, tenant-isolert og sporbar.

### 4. Typed normaliseringsutfall

Domenegrensen skal skille konseptuelt mellom minst følgende utfall:

| Utfall | Betydning | Tillatt automatikk |
| --- | --- | --- |
| `VALID` | Verdien kan parses og valideres deterministisk i relevant kontekst. | Kan få kanonisk E.164-verdi og inngå i sammenligning. |
| `INVALID` | Verdien kan med tilstrekkelig sikkerhet fastslås som ugyldig. | Skal normalt ikke opprette en ny godkjent kontakt automatisk. |
| `AMBIGUOUS` / `NEEDS_REGION` | Verdien kan være legitim, men mangler region eller annen nødvendig kontekst. | Skal til review; systemet skal ikke gjette. |

Eksakte enum- og typenavn avgjøres i fase 4C. Et utfall skal kunne bære nødvendig, ikke-sensitiv årsakskode for UI, importreview, tester og operativ feilsøking.

Normalisering endrer aldri publiseringsstatus.

### 5. Én kontrakt for personer og organisasjoner

Samme domenegrense og regler skal brukes for:

- `PersonContact` med `type=PHONE`
- `Organization.phone`

For personkontakt er målretningen `PersonContact.value` med en additiv normalisert sammenligningsverdi i tråd med ADR-005. For organisasjon er målretningen `Organization.phone` med en additiv normalisert sammenligningsverdi.

Fase 4 oppretter ikke `OrganizationContact` og fjerner ikke `Person.phone`.

### 6. Editor-konsekvenser

Editor skal sende telefoninput gjennom samme domenegrense som øvrig domenelogikk. Den skal:

- støtte internasjonale numre med `+`
- støtte nasjonale numre når eksplisitt regionkontekst finnes
- vise et forståelig skille mellom ugyldig verdi og manglende kontekst
- bevare presentasjonsverdien separat fra maskinidentiteten
- ikke publisere, avpublisere eller endre primærstatus som bivirkning av normalisering

Eksakt UI og feltnavn avgjøres i fase 4E. Generell redesign av Editor er ikke del av fase 4.

### 7. Import-konsekvenser

Import 2.0 og dagens importgrunnlag skal kobles til samme telefondomene som Editor. En importjobb skal kunne ha eksplisitt standardregion, for eksempel «Standardland for telefonnumre: Norge».

Konseptuell flyt:

```text
raw phone value
    -> explicit region context
    -> phone normalization
    -> VALID / INVALID / AMBIGUOUS
    -> matching or review
    -> explicit commit
```

Numre med eksplisitt internasjonal landkode tolkes uavhengig av jobbens standardregion. Manglende kontekst eller ugyldig input skal ikke skjules av AI eller heuristisk landgjetning.

Tom eller manglende importverdi beholder eksisterende data. Importcommit skal fortsatt følge ADR-004 og ADR-005 med preview, review, eksplisitt beslutning og sporbar commit.

Fase 4F etablerer telefonkontrakten i import. Full Import 2.0-UX og hele brukerreisen kommer senere.

### 8. Matching og deduplisering

Eksakt lik kanonisk E.164-verdi er et sterkt matchsignal. Det er ikke alene personidentitet og skal ikke utløse automatisk person-merge.

Samme telefon kan legitimt brukes av flere personer, blant annet som sentralbord, arbeidsplass, bookingnummer eller delt jobbtelefon. Telefon kan også være historisk eller gjenbrukt.

Det skal derfor ikke innføres en global unik constraint på telefonnummer mellom personer. ADR-005s målkrav om unik normalisert verdi gjelder innen samme person og kontakttype, ikke globalt på tvers av personer.

Importmatching skal vise signalet og øvrig kontekst i review når automatisk handling ikke er sikker.

### 9. Konservativ legacy- og migreringsstrategi

Eksisterende telefondata skal ikke massekonverteres ved å anta Norge. Overgangen følger:

```text
read-only inventory
    -> deterministisk klassifisering
    -> safe additive backfill
    -> review av rester
```

Bare verdier som kan normaliseres deterministisk under godkjent, sporbar kontekst kan backfilles automatisk. Uklare og ugyldige verdier bevares uendret for review.

Ingen eksisterende telefonverdi skal mistes som følge av teknisk migrering. Additive felt, batchsporbarhet, idempotens, backup og kontrollert rollback skal være på plass før backfill.

Den konservative `repair_person_contacts --contact-type PHONE`-kommandoen fra fase 2 beholdes som historisk avgrenset legacyreparasjon. Den er ikke den nye normaliseringstjenesten og skal ikke utvides til blind internasjonal backfill.

### 10. Personvern og dataintegritet

Telefonnumre er personopplysninger når de kan knyttes til personer. Inventory, migreringsrapporter, logger og review skal derfor være tenant-isolerte, rollebeskyttede og minimere gjengivelse av rå verdier.

Kanonisk E.164 gjør kobling og matching enklere og øker samtidig risikoen for utilsiktet sammenkobling. Systemet skal derfor:

- ikke bruke telefon alene til automatisk person-merge
- ikke logge rå eller kanoniske telefonverdier unødvendig
- bevare originalverdi og migreringsspor
- skille normalisering fra publisering
- avvise lesing, matching og skriving utenfor autorisert scope; dagens scope er
  tenant, mens et senere aktivert ADR-011-scope kan være eksakt SharingDomain
- stoppe eller sende til review ved utilstrekkelig kontekst

Behandlingsgrunnlag, tilgangsroller og retensjon fra ADR-005 må avklares før de leveransene som faktisk lagrer nye migrerings- eller reviewartefakter.

## Fase 4: International phone identity foundation

Målet er å etablere en stabil og internasjonalt skalerbar telefonidentitet før full Import 2.0-implementering.

### 4A – ADR-010

**Omfang:** Arkitekturbeslutning og fasescope. Ingen runtime- eller dataendring.

**Akseptanse og test:** ADR, beslutningsindeks, roadmap, prosjektstatus og changelog er konsistente; dokumentlenker og diff er kontrollert; fase 3 forblir `CLOSED / VERIFIED`.

**Rollback:** Dokumentasjonscommiten kan reverseres uten data- eller runtimekonsekvens.

### 4B – Databaseline

**Omfang:** Skrivebeskyttet inventory av faktisk person- og organisasjonstelefon i staging. Rapporten skal klassifisere formater og kontekstbehov uten å endre data og uten unødvendig eksponering av verdier.

**Akseptanse og test:** Repeterbare aggregerte tellinger, dokumentert scope, no-write-bevis og identifiserte konflikt-/reviewgrupper.

**Rollback:** Ikke relevant for data; eventuelle lokale rapportartefakter håndteres etter avtalt personvern og retensjon.

### 4C – Normalization domain

**Omfang:** Én intern telefonadapter for parsing, regionkontekst, validering, typed resultat og E.164. Dependency-versjon velges her.

**Akseptanse og test:** Representative norske og internasjonale gyldige, ugyldige og kontekstløse verdier; eksplisitt `+`-uavhengighet; ingen skjult Norge-default; ingen domene-write i ren normalisering.

**Rollback:** Adapteren kan fjernes eller deaktiveres før modell- og dataavhengigheter aktiveres.

### 4D – Additiv datamodell

**Omfang:** Additive normaliserte sammenligningsfelt for person- og organisasjonstelefon og, dersom nødvendig, eksplisitt tenant-regiongrunnlag. Ingen destruktiv legacyfjerning.

**Akseptanse og test:** Tenant-konsistens, nullable overgang, constraints for gyldig kanonisk verdi, migrasjon fra realistisk kopi, reverse/rollback og uendrede legacyverdier.

**Rollback:** Ny lesing og skriving kan stoppes mens additive felt og råverdier bevares; fysisk feltdropp inngår ikke.

### 4E – Editor

**Omfang:** Internasjonal telefoninput og validering med eksplisitt regionkontekst og forståelige typed feil-/reviewutfall.

**Akseptanse og test:** Person- og organisasjonstelefon bruker samme kontrakt; `+`-numre, nasjonale numre, ugyldige numre og manglende region er dekket; publisering og primærstatus endres ikke implisitt.

**Rollback:** Gå tilbake til forrige Editor-lesing/-skriving uten å fjerne råverdier eller additive data.

### 4F – Import contract

**Omfang:** Dagens importgrunnlag kobles til samme telefonnormalisering, med eksplisitt standardregion per jobb/importkontekst og review av usikre verdier.

**Akseptanse og test:** Typed preview, matching og commit; blank betyr `KEEP`; internasjonal landkode overstyrer ikke identitet via jobbregion; `INVALID` og `AMBIGUOUS` kan ikke gjette seg til automatisk godkjent kontakt; retry er idempotent.

**Rollback:** Slå av ny importlesing/-skriving og behold eksisterende importkontrakt og rådata til avvik er gjennomgått.

### 4G – Controlled backfill

**Omfang:** Backfill bare deterministisk normaliserbare legacyverdier. Resten bevares for review.

**Akseptanse og test:** Dry-run, batchsporbarhet, idempotens, før-/ettertellinger, ingen tapte råverdier, ingen publiseringsendring og prøvd rollback på datakopi.

**Rollback:** Reverser kun batchens additive kanoniske verdier; aldri slett eller overskriv originaldata.

### 4H – Staging verification

**Omfang:** Samlet kontroll av Editor, import, API/PUBLIC-regresjoner, data, backup/restore og relevante invariants.

**Akseptanse og test:** Representative person- og organisasjonsreiser, cross-tenant negative tester, deterministisk inventorydiff, restore, rollback og dokumentert stagingevidens.

**Rollback:** Gå tilbake til siste verifiserte lese-/skrivevei, behold råverdier og additive data, og merk fase 4 som ikke lukket.

Fase 4 kunne først markeres `CLOSED / VERIFIED` etter separat implementasjon og stagingverifikasjon i 4B–4H. De tekniske kriteriene ble verifisert 2026-08-26. Etter første owner-smoke-remediation og andre owner-smoke UI-polish gjennomførte prosjekteier siste manuelle kontroll og godkjente leveransen 2026-08-29. ADR-010 er dermed gjennomført innen avtalt fase-4-scope.

## Akseptansekriterier fra 4A til 4B

Fase 4B kan først starte når:

- ADR-010 er reviewet, eksplisitt prosjekteiergodkjent og merget
- den faktiske mellomtilstanden er dokumentert uten å omtales som måltilstand
- E.164, bibliotekretning, regionkontekst, typed utfall, matchsignal og konservativ migrering er låst
- person- og organisasjonstelefon omfattes av samme prinsipper
- non-goals og grensen mot full Import 2.0 er tydelige
- roadmap og prosjektstatus peker på samme fase 4A–4H
- fase 4B har et separat, skrivebeskyttet og personvernbevisst oppdrag

## Beslutninger som fortsatt krever eksplisitt godkjenning

De låste arkitekturvalgene ovenfor skal ikke åpnes på nytt i implementasjonen. Følgende leveransegater krever likevel separat godkjenning:

1. ADR-010-dokumentet er reviewet, prosjekteiergodkjent og merget med PR #56; denne gaten er oppfylt.
2. Fase 4B skal ha godkjent staging-scope, no-write-bevis, redaksjonsnivå og håndtering/retensjon for eventuelle rapportartefakter.
3. Hver av 4C–4H skal bestilles og godkjennes som en separat leveranse med konkret implementeringsplan, tester og rollback.
4. ADR-005s åpne valg om kontaktroller, behandlingsgrunnlag og retensjon må være avklart før den aktuelle telefonleveransen er avhengig av dem.

Eksakte dependency-, klasse-, enum-, felt-, indeks- og API-navn krever ikke en ny arkitekturbeslutning dersom de oppfyller dette ADR-ets invariants additivt og reverserbart.

## Eksplisitte non-goals

Følgende inngår ikke i fase 4:

- full Import 2.0-UX eller full Import 2.0-implementering utover telefonkontrakten
- generell persondeduplisering eller automatisk person-merge
- full implementering av ADR-005s relasjonsspesifikke kontaktpublisering
- fysisk fjerning av `Person.phone` eller annen generell legacyopprydding
- `OrganizationContact`
- telefonextensions, extensionfelt, extensionparsing, extensionimport eller extension-UX
- SMS- eller WhatsApp-integrasjon
- eksternt telefonnummeroppslag, carrier lookup eller telefonbasert geolokasjon
- AI-basert telefonnummer- eller landgjetning
- generell internasjonalisering av kommune- eller adressearkitekturen
- generell redesign av Editor
- endringer i fase 3-bildearkitekturen

## Avviste alternativer

### Rå streng som identitet

Avvist fordi presentasjonsvarianter av samme nummer ikke blir sammenlignbare eller idempotente.

### Overskrive alle eksisterende verdier med E.164

Avvist fordi presentasjonsverdi og kanonisk maskinidentitet har ulike formål, og fordi uklar legacykontekst kan gi datatap eller feil land.

### Egen norsk eller internasjonal parser

Avvist fordi nummerplaner endres og er mer komplekse enn en lokal regex-/prefiksløsning kan forvalte sikkert.

### Skjult Norge-default for alle nasjonale numre

Avvist fordi det gir feil identitet utenfor eksplisitt norsk tenant- eller importkontekst.

### Global unik telefon på tvers av personer

Avvist fordi delte, organisatoriske, historiske og gjenbrukte numre er legitime.

### Automatisk person-merge ved lik E.164

Avvist fordi telefon er et sterkt signal, ikke tilstrekkelig bevis på personidentitet.

### Egen telefonmodell for organisasjoner i fase 4

Avvist som unødvendig scopeutvidelse. `Organization.phone` får samme normaliseringsprinsipp additivt uten `OrganizationContact`.

### Extensions i MVP

Avvist fra fase 4-scope. En eventuell senere extension må lagres og behandles separat fra E.164-identiteten.

## Konsekvenser og tradeoffs

### Positive konsekvenser

- stabil identitet for internasjonale telefonnummer
- samme regler i Editor, import, API og domenelogikk
- tryggere matching, deduplisering og idempotens
- eksplisitt håndtering av usikker region
- reverserbar overgang uten tap av presentasjonsverdi
- felles prinsipp for person- og organisasjonstelefon

### Kostnader og ulemper

- ny dependency og intern adapter må forvaltes
- additive felt og migrering øker overgangskompleksiteten
- inventory og review av legacydata krever tid og personvernkontroll
- noen verdier kan ikke automatiseres og må behandles manuelt
- E.164 gjør sammenkobling enklere og krever streng tenant-, tilgangs- og loggdisiplin

### Uavklarte implementeringsdetaljer

Følgende avgjøres i riktig fase uten å åpne arkitekturretningen på nytt:

- eksakt `phonenumbers`-versjon
- konkrete klasse-, enum- og feltnavn
- eksakt additiv lagring av tenant-/importregion
- databaseconstraint- og indeksutforming
- API-schema og feil-/årsakskoder
- batchformat for inventory, backfill og review
- kontrollert aktiverings- og rollbackmekanisme

Hvis en implementeringsdetalj ikke kan oppfylle invariantene i dette ADR-et additivt og reverserbart, må avviket tilbake til eksplisitt arkitekturreview.
