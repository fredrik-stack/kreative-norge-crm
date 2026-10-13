# Fase 5E – godkjent implementerings- og testplan

**Status:** FULLFØRT / OWNER-APPROVED SOM PLAN

**Godkjenningsdato:** 2026-10-13

**Runtimeimplementering av de nye leveransene:** IKKE STARTET

**Dokumentasjonsleveranse:** planen og godkjenningen er lagret på `docs/phase5e-approved-plan` og leveres gjennom [PR #74](https://github.com/fredrik-stack/kreative-norge-crm/pull/74); skrivebeskyttet review av `a9691d5f1f2969514e24a266a9b4c9cd1add11c1` er gjennomført uten blokkerende funn, og kontrollert merge er bestilt 2026-10-13. Faktisk mergestatus følger GitHub. Eksakt PR-head, PR-lenke og CI følger GitHub og leveranserapporten. Lokal dokumentasjonsreview er gjennomført uten blokkerende funn.

**Godkjenningsgrunnlag:** Prosjekteier Fredrik Forssman godkjente hele den beslutningsklare 5E-rapporten og alle seks hovedvalg 2026-10-13. Rapportens ti fagområder er bevart nedenfor, med godkjente valg omskrevet til vedtatt målretning. Eksakte modellnavn, ruter og DDL er fortsatt implementeringsdetaljer der kilden ikke fastsetter dem.

**Normativ grense:** [ADR-013](../decisions/ADR-013-IMPORT_2_0_EXECUTION_AND_COMMIT_CONTRACT.md) fastsetter den nye importkontrakten; [ADR-012 §28](../decisions/ADR-012-PLACE_IDENTITY_GEOGRAPHIC_CLASSIFICATION_AND_ACTOR_ONLY_MAPS.md#28-migreringsrekkefølge) fastsetter den godkjente sted-/kartpresiseringen. Denne planen samler leveranserekkefølge, testspor og migrerings-/aktiveringsporter. §5–7 bevarer godkjent faggrunnlag og skal leses sammen med ADR-en, ikke som en konkurrerende definisjon.

**Kildespor:** inkludert godkjent planrapport i dokumentasjonsbestillingen 2026-10-13; 33687 byte før presentasjonsendringer, SHA-256 `4178af8fa464f581775ceea6cbfbe1034ede8b7a048f25fe3e17b19722309d8f`. Ingen råvedlegg eller privat dialog er lagt i repoet. Kontroller, databeslutninger og aktiveringskrav som ligger senere er planlagt, ikke gjennomført; nye tester er ikke registrert som bestått.

**Fase 5E er FULLFØRT / OWNER-APPROVED SOM PLAN. Den vedtatte grunnmursrekkefølgen er deling og tilgang → kontakter og relasjoner → steder → Import 2.0.** Lagring og backup kan forberedes parallelt. Kartarbeidet holdes utenfor importens kritiske sti.

Fase 5D står som avsluttet og godkjent. UX v6 revisjon 4, inkludert sluttkorrigeringen O-24, er styrende for brukerreisen. Planen nedenfor konkretiserer hvordan denne opplevelsen kan implementeres på dagens kodegrunnlag. Planen er eiergodkjent; runtimearbeid starter først gjennom senere avgrensede implementeringsbestillinger etter dokumentasjonsleveransen og de relevante inngangsportene.

## 1. Kontroll mot fersk main

Kildeplanens GitHub-baseline er kontrollert på nytt 2026-10-13; main er uendret:

| Kontroll | Verifisert resultat |
|---|---|
| Fersk `main` | [`18951b010d46eb7beea85e6c96b228e4472893af`][maincommit]. Kontrollen ble gjentatt under analysen; samme head. |
| Dokumentasjonsleveransen | [PR #73][pr73] er merget med denne mergecommiten. |
| Siste PR-head | `6a70c14b22e2d408e99b2b10f71995fa2a051830`. |
| PR-CI | [Kjøring 38306273325][prci]: 6 av 6 jobber bestått på PR-head. |
| Main-CI | [Kjøring 38306834660][mainci]: 6 av 6 jobber bestått på mergecommiten. |
| Endringsomfang | Åtte Markdown-dokumenter. Ingen endring i kode, migrasjoner eller ADR-er i dokumentasjonsleveransen. |

[Brukertestrapporten][report] og [UX-spesifikasjonen][ux] er lest som gjeldende dokumentasjon på denne commiten, sammen med relevante ADR-er, aktiv kode, migrasjoner og testdefinisjoner.

**Staging er ikke kontrollert på nytt i denne gjennomgangen.** Tidligere stagingevidens er brukt med dato og opprinnelig omfang. Det gjelder særlig [5A-kartleggingen fra 30. august][impact], som må oppdateres før datamigrering. Kildeplanens uavhengige kontroll gjaldt GitHub; lokal Git-status var den gang en opplysning fra Codex-handoff. Ved dokumentasjonsoppstart 2026-10-13 er lokal main selvstendig kontrollert som ren og 0/0 mot fersk origin/main. Ingen ny stagingkontroll er kjørt.

## 2. Hva aktiv kode betyr for implementeringen

Den viktigste konklusjonen er at telefon- og bildefundamentet gir betydelig gjenbruk, mens deling, kontaktpublisering og importens lagringsmodell trenger videre arbeid.

| Område | Faktisk løsning på main | Konsekvens |
|---|---|---|
| Deling og tilgang | Profiler, kontakter og relasjoner er direkte tenantbundet. Tilgangsfunksjonen har fortsatt global grupperolle som reserve. | SharingDomain, tilknytninger, private arbeidsdata, avtaleaksept og handlingsrettigheter må etableres før delt tilgang aktiveres. [Modeller][models] · [Permissions][permissions] |
| Kontakter og relasjoner | Flere kontakter finnes, men offentlig kontaktvalg ligger globalt på kontakten. Rolle/tittel mangler på aktør–person-koblingen. | Kontaktkanaler og rolle/tittel må kunne styres for den konkrete aktørkoblingen. [Modeller][models] · [ADR-005][adr5] |
| Steder | Aktør- og personsteder er fortsatt fritekst. | Place, aktørsteder, personsteder og geografiske forslag må implementeres. [Modeller][models] · [ADR-012][adr12] |
| Importformat | XLSX-parseren leser bare første ark. | Firearksformat, arkvalg og fri mapping er egne leveranser. Google Sheets er foreløpig en kildeverdi i modellen. [Parser][parser] · [Modeller][models] |
| Gjenåpning og review | Ny preview sletter eksisterende import­rader og commitlogger. Beslutninger mangler den nye revisjonskontrakten. | Kildegrunnlag, kandidater og vurderinger må få stabile identiteter og versjoner. [Preview][preview] |
| Analyse og UI | Nettleseren driver AI-batchene. Arbeidsflaten er en bred rådatatabell. | Analysen trenger selvstendig serverkjøring; Gjennomgang trenger kandidatbasert kø og detaljflate. [Import-hook][importhook] · [Import-UI][importui] |
| Lagringsbekreftelse | UI kan tolke et fanget API-avvik som vellykket lagring. | «Lagret» må kreve et uttrykkelig vellykket serversvar. Dette er et kodefunn, ikke en nettleserreprodusert feil. [Import-hook][importhook] · [Import-UI][importui] |
| Fullføring | Dagens `LINK_ONLY` kan fortsatt gå gjennom generell profiloppdatering. | Musikkontortilknytning må bli en egen handling som bevarer profil og bilde. [Commit][commitcode] |
| Bilder før ny profil | Bildebeslutningen støtter et foreslått aktørgrunnlag, men kandidatflyten krever en eksisterende Organization. | Det trengs en importtilpasset inngang som forbereder bilder uten å opprette profilen. [Bildekandidater][imagecandidates] · [Bildebeslutninger][imagedecisions] |

Dette gir en tydelig gjenbruksgrense: Vi viderefører telefonnormalisering, sikre bildefunksjoner, autentisering, taksonomi og eksisterende frontendplattform. Nye importvalg og fullføring bygges på tjenester som håndhever den godkjente domenemodellen.

## 3. Vedtatt fasesekvens

### Nødvendig presisering av ADR-012

[ADR-011s migreringsrekkefølge][adr11] legger kontakter og relasjoner før strukturerte steder, og deretter Import 2.0. Denne rekkefølgen beholdes.

[ADR-012 §28][adr12] legger derimot kartleveranser før `STEDER`-kontrakten. Samtidig krever ADR-et at steder og import skal fungere uten kartprovider. Nyere eierføring og [UX §15][ux] sier uttrykkelig at kart ikke skal forsinke kjerneimporten.

Prosjekteier har godkjent denne avgrensede presiseringen, formalisert i [ADR-012 §28](../decisions/ADR-012-PLACE_IDENTITY_GEOGRAPHIC_CLASSIFICATION_AND_ACTOR_ONLY_MAPS.md#28-migreringsrekkefølge):

> Når stedskjernen, geografiske forslag, nødvendig Editor-støtte, additive API-felt og tekstlig PUBLIC-visning er verifisert, kan STEDER og Import 2.0 leveres. Koordinat-, provider- og kartarbeid følger separat, med sine eksisterende aktiveringskrav.

Dette dokumenteres før runtimearbeidet. Kontaktgrunnlaget flyttes fortsatt ikke bak steder.

### Leveranseområder

Underfasene nedenfor er eiergodkjent konkretisering av roadmap; de er planlagt og ikke runtimeimplementert.

| Etappe | Leveranse | Ferdigkriterium |
|---|---|---|
| **6A – Deling og tilgang** | SharingDomain, tilknytninger, private arbeidsdata, avtale/handlingsrettigheter, revisjoner, sikre skrivetjenester, canonical PUBLIC og image-home. | Bevarte identiteter, kontrollert tilgang, sikre gamle innganger og verifisert offentlig visning/bildescope. |
| **6B – Kontakter og relasjoner** | Autoritative kontaktposter, primærkontaktregler, relasjonsspesifikk publisering, rolle/tittel og nødvendig Editor-/API-støtte. | Samme person kan ha forskjellige roller og offentlige kanaler hos forskjellige aktører. |
| **6C – Stedskjerne** | Place, OrganizationPlace, PersonPlace, kontrollert opprettelse/gjenbruk, geografiske forslag og tekstlig visning. | Import kan bruke og avklare steder uten kart eller Google. |
| **Parallelt: importlagring** | Privat filområde, filmanifest, rapporter, backup/restore og retensjonsmekanisme. | Verifisert før første reelle Import 2.0-opplasting. |
| **7A – Kilde, mapping og jobbregler** | Versjonert standardpakke og KI-prompt, CSV/XLSX-mapping, varige utkast og O-24. | Hele startreisen lagres og gjenåpnes korrekt. |
| **7B – Analyse og berikelse** | Vedvarende bakgrunnsarbeid, matching, avgrenset berikelse, bildeforslag og reell fremdrift. | Arbeidet fortsetter når nettleseren lukkes. |
| **7C – Gjennomgang** | Konsoliderte kandidater, kø, identitet/kilder, gule avklaringsinnganger og alle godkjente feltvalg. | Review bygger på serverens problemer, revisjoner og planlagte handlinger. |
| **7D – Sluttkontroll og fullføring** | Komplett offentlig før/etter-plan, bekreftelse, sikker lagring, kvittering og resultat. | Sammenhengende teknisk verifikasjon i staging og prøvd tilbakeføring. |
| **7E – Google Sheets og v1-lukking** | Valgt konto, regneark og faner som et versjonert kildesnapshot. | Samme etterfølgende importreise som CSV/XLSX. |

Hver etappe deles i små PR-er med en samlet funksjon eller invariant. Eksempelvis bør 6A leveres som additiv identitet/tilknytning, private data/tilgang, skrivetjenester, PUBLIC og image-home – med de separate aktiveringsportene ADR-011 allerede krever.

**Kode kan være levert mens aktivering fortsatt er avslått.** Delte person- og kontaktfunksjoner åpnes først når kontaktgrunnlaget og de gamle inngangene følger samme regler.

Checkin støttes gjennom Excel-mapping i v1. Direkte Checkin-API, Mailmojo-eksport, kart og XML-konvertering inngår ikke i kjerneimportens leveranser. Google Sheets følger etter CSV/XLSX, men før v1 lukkes, slik [UX §15][ux] fastsetter.

## 4. Grunnmuren som må være på plass

### Deling, private arbeidsdata og PUBLIC

Eksisterende aktør- og person-ID-er beholdes. Hvert objekt får først én tilknytning fra dagens tenant. Private notater, interne tags og lokalt arbeidsinnhold skilles fra den felles profilen før delt lesing åpnes.

Alle relevante serverhandlinger må kontrollere aktiv bruker, medlemskap, riktig SharingDomain, gjeldende avtaleaksept, handlingsrettighet og objektscope. Dette gjelder også gamle API-er, import, admin og bakgrunnsarbeid; de må bruke de samme tjenestene eller avvises kontrollert. [ADR-011][adr11]

PUBLIC får én felles beregning av hva som faktisk er offentlig. HTML har allerede en ID-basert aktørrute, mens public API fortsatt bruker organisasjonsnummer og mangler `canonical_id`. Det er vedtatt en additiv API-overgang med canonical ID og bevart entydig organisasjonsnummeralias. [PUBLIC API][publicapi] · [PUBLIC HTML][publichtml]

Image-home etableres som ansvar for framtidige private bildehandlinger. Historiske assets, selections, releases, nøkler og sikkerhetslogg flyttes ikke. En senere Musikkontortilknytning endrer ikke bildeansvar eller bildevalg.

### Kontakter og relasjoner

`PersonContact` blir eneste autoritative skrivekilde for personens kontaktverdier. Direkte personfelt beholdes som kompatibilitetsfelt gjennom overgangen.

Planen krever:

- Flere e-postadresser og telefonnumre, med høyst én primær per type, også ved samtidige lagringer.
- E-postnormalisering som en egen additiv løsning. Dagens normaliserte felt er begrenset til telefon/E.164.
- Rolle og tittel på aktør–person-koblingen.
- Offentlige kontaktvalg på den konkrete koblingen.
- Samme offentlige resultat i Editor-preview, API, PUBLIC og importens sluttkontroll.

Ny kontakt er intern som standard. Primærkontakt betyr ikke offentlig kontakt. Aktørens offisielle e-post følger fortsatt aktørens offentlighet; det innføres ikke et nytt e-postflagg. Disse grensene følger [ADR-005][adr5], nyere [ADR-011][adr11] og [UX v6][ux].

Full eksportutvidelse og fysisk sletting av gamle felt kan leveres senere. Hele ADR-005 skal samtidig ikke merkes ferdig før de resterende leveransene er fullført.

### Steder

Stedskjernen skal støtte norske og utenlandske steder, bevart originaltekst, kildegrunnlag og kontrollert gjenbruk/opprettelse. Et manuelt bekreftet sted kan brukes uten koordinater eller obligatorisk plattformgodkjenning.

Geografiske regler gir forklarte forslag, aldri automatisk Musikkontortilknytning. PersonPlace gir ingen personmarkør eller kartrettighet. Tvetydige steder blir ikke verifiserte eller offentlige uten avklaring.

Selvbetjent Place-opprettelse er den godkjente, uttrykkelige handlingen som kan lagre et felles sted før importen fullføres. Avbrutt import sletter derfor ikke dette stedet automatisk. [ADR-012 §§13–16][adr12]

## 5. Vedtatt kilde-, kandidat- og API-kontrakt

### Standardpakken: fire ark og flere kontakter

Vedtatt første produksjonsversjon er **`KN_IMPORT/1`**, med versjonsmarkør i arbeidsbokmetadata og de fire vedtatte arkene.

Følgende identitets- og kontaktkolonner er godkjent kontraktgrunnlag:

| Ark | Identitet og sentrale felt | Representasjon |
|---|---|---|
| **AKTØRER** | `actor_source_id`, navn, organisasjonsnummer og relevante profilfelt. | Én aktøridentitet i pakken. |
| **PERSONER** | `person_source_id`; valgfri kontaktgruppe: `contact_source_id`, `contact_type`, `contact_value`, `contact_primary`, `contact_country`. | Flere rader kan tilhøre samme person, med én kontakt per rad. Person uten kontakt er gyldig. |
| **KOBLINGER** | `link_source_id`, `actor_source_id`, `person_source_id`, `role`, `title`, `status`, `publish_person`; eventuelt `contact_source_id` og `publish_contact`. | Flere rader kan tilhøre samme kobling når flere kanaler skal angis. |
| **STEDER** | `place_assignment_source_id`, `entity_type`, `entity_source_id`, `original_place_value`, land/region/kommune/locality, stedstype, primær/offentlig valg og proveniens. | Følger stedskontrakten i ADR-012. |

Dette håndterer flere kontakter innen fire ark. En person med fem kontakt­rader blir fortsatt **én personkandidat** i Gjennomgang.

Kontrakten må håndheve at samme kontakt-ID tilhører samme person, og at samme koblings-ID alltid peker til samme aktør/person-par. Motstridende ikke-tomme verdier blir review; ingen rad får vinne fordi den står sist. Tomt betyr ikke oppgitt/bevar, mens uttrykkelig `false` beholdes som et faktisk valg.

Kilde-ID-er er lokale identiteter i pakken. De gir ingen rett til å endre en CRM-post. Alle publiseringsverdier går videre til review og offentlig sluttkontroll. Beslutningen konkretiserer de tidligere åpne formatvalgene i [UX §4][ux] og [ADR-012 §16][adr12].

Standardmal, validering og **«Last ned siste KI-prompt»** skal bruke samme versjonerte skjema. Egen CSV/XLSX og Checkin-Excel mappes til samme interne struktur.

### Varig importgrunnlag

Det er vedtatt å videreføre `ImportJob` med en tydelig arbeidsflytversjon og legge til disse logiske enhetene:

| Enhet | Hva den sikrer |
|---|---|
| **Kildesnapshot og filmanifest** | Eksakt kilde, checksum, formatversjon, ark/faner og tilgjengelighet. |
| **Kilderader og kandidater** | Sporbarhet fra én samlet kandidat tilbake til alle relevante rader/celler. |
| **Versjonert jobbutkast** | Mapping, Musikkontor, reviewer, telefonland, regler og berikelsesvalg. |
| **Reviewbeslutning og problemer** | Lagrede valg, revisjon, gjenstående avklaringer og riktige seksjonsinnganger. |
| **Fullføringsplan og kvittering** | Godkjente handlinger, forventede målrevisjoner, offentlig konsekvens og faktisk resultat. |

Den nye importkontrakten får egne versjonerte API-innganger. Gamle jobber konverteres ikke automatisk til v2.

API-et må skille mellom lagring av utkast, oppstart av analyse, kandidatlesing, reviewgodkjenning, offentlig bekreftelse og fullføring. En lagring returnerer uttrykkelig resultat og ny revisjon. Utdatert grunnlag gir en konkret konflikt; klienten kan ikke overstyre dette med et gammelt «godkjent»-flagg.

Problem- og handlingskontrakten fastsettes før review-UI bygges. Dermed bruker dashboard, gule knapper, godkjenning og sluttkontroll samme grunnlag.

## 6. Bakgrunnsarbeid, berikelse og bilder

### En liten, vedvarende bakgrunnsløsning

Det er vedtatt **én workerprosess i eksisterende applikasjonsimage, med PostgreSQL som varig arbeidsgrunnlag**.

En oppgave reserveres kort i databasen, utfører eksternt arbeid uten å holde databaselåser og lagrer resultatet bare dersom oppgaven og kandidatversjonen fortsatt er aktuelle. Restart kan gjenoppta avbrutt arbeid. Sene svar får ikke overskrive en godkjent vurdering.

Dette oppfyller kravet om å kunne lukke nettleseren. En større køplattform kan vurderes dersom målinger senere viser behov.

### Konkrete startgrenser for berikelse

Følgende er **vedtatte startgrenser for senere implementering og måling**, ikke målte tids-, pris- eller kvalitetsgarantier:

| Nivå | Tillatt arbeid per aktuell kandidat og analyseversjon |
|---|---|
| **Ingen ekstern berikelse** | Ingen ekstra BRREG-, profilside- eller modellkall for profilberikelse. |
| **Målrettet ekstern berikelse** | Ved konkret mangel: inntil 2 BRREG-kall, 2 relevante offisielle nettsider og 1 modellkall for strukturering. |
| **Utvidet beriket søk** | Samme registergrense, inntil 4 relevante offisielle nettsider og 1 modellkall totalt. I tillegg forslag til beskrivelse, sosiale/musikklenker og relevant klassifisering. |

Som vedtatt første tekniske ramme gjelder maksimalt to samtidige eksterne kall, ett per provider, og tre forsøk inklusive første ved forbigående feil. Modellgrunnlaget begrenses til 8 000 relevante kildetegn og 1 200 outputtokens; beskrivelsesforslag til 400 tegn. Vedtatte start-timeouter er 5 sekunder for HTML, 10 for BRREG/Brave og 20 for modellkall.

Feltgrensen er viktigere enn tallene:

- BRREG gir identitetskontekst med kilde.
- Kontaktforslag må kunne knyttes til riktig aktør/person i en identifisert kilde.
- Modellen strukturerer kildegrunnlag og gir forslag.
- Private notater, interne tags, private kontaktkanaler, avtaledata og hele råpakken sendes ikke som skjult providerinput.
- Berikelse godkjenner aldri identitet, publisering, tilknytning eller bilde.

Dagens AI-input sender hele det normaliserte innholdet og tenantens tags; denne grensen må derfor endres ved videreføring. [AI-tjenesten][ai]

Første leveranse bruker kjente offisielle kilder og en smal BRREG-adapter. Hvis kildegrunnlaget mangler, skal det vises ærlig. Løsningen skal ikke hevde at hele nettet er undersøkt.

### Automatisk bildekandidatfunn

Bildeløpet gjelder uavhengig av profilberikelsesnivå, som godkjent i [UX §6][ux]:

1. Behold et gyldig, låst og godkjent bilde.
2. Ved manglende bilde: bruk tillatt kjent kilde og offisiell nettside/Open Graph.
3. Ved behov: høyst ett automatisk Brave-søk per aktør/analyseversjon, når den eksisterende providergaten er oppfylt.
4. Vis et begrenset arbeidssett med kandidater. Bare valgt bilde går gjennom full bildebehandling.
5. Brukeren godkjenner bilde og utsnitt. Manglende bilde blokkerer ikke en ellers gyldig profil.

Repoet dokumenterer fortsatt Brave som operativt deaktivert for ordinære sluttbrukere frem til avtalegaten er lukket. Importautomatikken kan ikke omgå denne eksisterende grensen. Offisiell kilde, limt URL, opplasting og fallback kan fungere uten Brave. [ADR-007][adr7]

For nye aktører bindes bildeforberedelsen til jobb, kandidat, versjon, aktørgrunnlag, reviewer og faktisk eller planlagt image-home. Det opprettes ingen midlertidig CRM-aktør.

Ferdig bilde, utsnitt og godkjenning lagres varig. Kortlivede previewreferanser kan fornyes ved gjenåpning. Uvalgte providerresultater følger eksisterende transientregler og blir ikke kopiert inn i jobbens varige historikk.

For transport mellom worker og API er det vedtatt et lite, delt minneområde uten backup, med absolutt utløp på høyst 30 minutter. Cachetap betyr at uvalgte treff må oppfriskes; det mister ikke et lagret bildevalg. Denne løsningen avgrenses til transporten av kortlivede treff.

## 7. Fullføring: vedtatt transaksjons- og konfliktmodell

**Det er vedtatt én samlet databasetransaksjon for det uttrykkelig godkjente utvalget i en fast fullføringsplan.**

Uavklarte kandidater og avhengighetene deres må være avklart eller uttrykkelig utelatt før planen fryses. Det gir en enklere og mer forståelig førsteversjon enn delvis lagring rad for rad.

Fullføring følger denne kontrakten:

1. **Beregn planen på serveren.** Skill profilendring, private arbeidsdata, kontakt, relasjon, Musikkontortilknytning, sted, publisering og bildevalg.
2. **Beregn hele den offentlige konsekvensen.** Bruk samme regelverk som faktisk PUBLIC, inkludert endringer på allerede publiserte profiler.
3. **Bind bekreftelsen til planversjonen.** Relevant endring opphever gammel bekreftelse.
4. **Lås jobb og berørte objekter i stabil rekkefølge.** Kontroller rettigheter, avtale, revisjoner, avhengigheter og godkjent plan på nytt.
5. **Lagre handlinger, audit og kvittering samlet.** En feil før commit ruller tilbake disse databaseendringene.
6. **Gjentatt forespørsel returnerer kvitteringen.** Tapt HTTP-svar skal ikke opprette en ny aktør, kontakt, kobling eller tilknytning.

Samme gjentakelsesnøkkel med annet innhold avvises. To samtidige fullføringsforsøk kan ikke skrive samme plan to ganger.

Musikkontortilknytning får en egen handling. «Bruk eksisterende og legg til kontoret» går dermed ikke gjennom dagens generelle oppdatering av profilfelter.

### Filer og bilder har en egen grense

Fullføring gjør ingen nye providersøk, nedlastinger eller bildebehandling. Forberedte bildevalg bruker eksisterende selection- og auditfunksjoner. Lokal sikkerhetskontroll av bildets deny-status består.

Rapporter og eventuell offentlig bildelevereanse får varige etterarbeidsoppgaver og egen resultatstatus. Hvis disse feiler etter vellykket databaselagring, skal grensesnittet vise hva som faktisk er lagret og hva som trenger oppfølging. Forsøket gjentas uten en ny profilimport.

Dette viderefører skillet i den eksisterende [importbildekontrakten][imagedecisions] og [bildetestene][imagetests]. En databasetransaksjon gir ikke automatisk tilbakeføring av filer eller sikkerhetslogg.

## 8. UX-kontrakten som skal implementeres og bevises

### Jobbregler og O-24

De tre filtrene beholdes:

- Manglende hovedkategori.
- Manglende relevant underkategori.
- Telefon uten avklart land.

Utvalget beregnes på serveren før analyse og omfatter **alle treff i jobben**. Feltredigering endrer ikke dette utvalget. Nytt scopevalg beregner et nytt sett.

Under filtrerte kandidater er alle fire grupper tilgjengelige, også ved null treff. Utkastvalg med null effekt vises i gruppen, mens Kontroll før analyse viser faktisk anvendt effekt.

Stedsregelen påvirker bare stedsopplysningene til valgte profiler. Den endrer ikke en felles stedskandidat eller andre profiler med samme stedsverdi. Vanlige feltavhengigheter, som underkategoriens hovedkategori, består. [UX §§5.2–5.4 og O-24][ux]

### Kø og avklaringer

Det er vedtatt korte kandidatsammendrag, serverfiltrering og henting i puljer på 50, med én aktiv detaljflate. Køen ruller internt innen skjermrammen.

Klikk, knapper og Option/Alt følger samme søk og filter. Når godkjenning fjerner aktiv kandidat fra filteret, brukes et bevart sorteringsanker slik at neste kandidat ikke hoppes over. Siste feltavklaring lar kandidaten stå åpen til brukeren velger neste handling.

Én strukturert problemliste styrer både antallet øverst og gul knapp i riktig seksjon. Knappen åpner og fokuserer avklaringen; den godkjenner ikke innholdet.

### Offentlig sluttkontroll

Hele listen med kompakte oppsummeringer hentes når steget åpnes. Aktører og personvisninger inngår fra start. Før/etter-detaljer kan åpnes per oppføring.

En felles profilendring må også ta med eksisterende offentlige visninger den påvirker, selv om alle koblingene ikke kom fra importfilen. Én person hos to aktører kan derfor gi to personvisninger i planen.

Lukkede oppføringer holder seg innen de godkjente tre tekstlinjene. Bekreftelsen gjelder hele planen, ikke bare den synlige delen av listen. [UX §§8–9 og O-21–O-23][ux]

## 9. Migrering, lagring og aktivering

### Additiv migrering med kontrollert omlegging

Før første relevante datamigrering gjøres et nytt, avgrenset staginginventar. Det skal gi konkrete førverdier for identiteter, tilknytninger, kontaktpublisering, tags, steder og bildestate.

Migreringene skal bevare ID-er og råverdier, kunne kjøres idempotent og gi en kontrollert sammenligning mellom gammel og ny lesing før omlegging.

Tre databeslutninger plasseres ved riktig tidspunkt:

| Beslutning | Må være avklart før |
|---|---|
| Klassifisering av legacytags og private arbeidsdata | Relevant delt lesing og canonical PUBLIC-omlegging i 6A. |
| Mapping av global tittel og kontaktpublisering til konkrete relasjoner | Kontakt-/PUBLIC-omlegging i 6B. |
| Retensjon, kilde-/rapportlagring og ferdige, ennå ikke tilknyttede bilder | Første reelle lagring i den nye importflyten. |

Verken «alle tags blir felles» eller «alle tags blir private» er en nøytral migrering. Tilsvarende skal gammel global tittel eller kontaktpublisering ikke blindt kopieres til alle relasjoner. Entydige tilfeller kan migreres kontrollert; avvik krever navngitte databeslutninger. Dette er datakvalitetsarbeid, ikke nye brukertester. [ADR-011][adr11] · [ADR-005][adr5]

### Privat og persistent importlagring

Det er vedtatt et eget privat importfilområde i eksisterende driftsoppsett. Originalfil og rapport får checksum, størrelse, versjon og tilgjengelighetsstatus. Filen publiseres ferdig før databasen markerer den som klar.

Backup og isolert restore må kontrollere kjeden:

**jobb → kilde → kandidater → beslutninger → kvittering → rapporter og filer.**

Sletting må samordnes med backup, slik at databasedumpen ikke peker til filer som forsvinner før arkivering. Retensjon må omfatte både aktiv lagring, rådata i databasen og gjenoppretting fra backup.

5A fant historisk 53 kildefilreferanser uten tilgjengelige filer. Dette må måles på nytt; ny lagring gjenskaper ikke gamle filer. Manglende grunnlag skal vises ærlig. [5A-evidensen][impact]

### Aktiveringskrav

Eksisterende ADR-porter plasseres ved funksjonen de gjelder:

- Avtale-, personvern- og tilgangskrav før delte persondata aktiveres i produksjon.
- Storage, retensjon og restore før første reelle Import 2.0-opplasting.
- Providerkrav før den aktuelle provideren aktiveres.
- **Browser-aktiv Codex før første senere UI-implementering**, også nødvendige Editor-endringer i grunnmuren.

Syntetisk utvikling og teknisk testing kan gjennomføres før de konkrete produksjonsdata- og avtaleleveransene er ferdige.

## 10. Testplan, tilbakeføring og godkjenning

### Tester som skal følge leveransene

| Testområde | Bevis som kreves |
|---|---|
| **Deling og tilgang** | Feil domain, manglende medlemskap, utgått avtale og manglende rettighet avvises server-side. Private arbeidsdata lekker ikke gjennom API, matching, eksport eller PUBLIC. |
| **Migrering og bildeansvar** | Bevarte ID-er, korrekt legacytilknytning, idempotent backfill, beskyttet tenant-sletting og uendret historisk bildestate. |
| **Kontakter og PUBLIC** | Flere kontakter, samtidige primærbytter, samme telefon hos ulike personer, forskjellige kanaler hos to aktører og lik visning i alle offentlige flater. |
| **Pakke og mapping** | Fire ark, flerkontakt, kilde-ID-er, feil referanser, motstridende verdier, blank kontra `false`, arkvalg og Checkin-Excel. |
| **Jobbregler** | O-24: tre filtre × aktør/person × null/ikke-null treff, fire aktive grupper og riktig effekt på tvers av innlastede sider. |
| **Bakgrunn og berikelse** | Nettleserlukking, workerrestart, forsøkstak, sene svar, tilbakekalte rettigheter og korrekt providerpayload. |
| **Bilder før profil** | Bilde kan forberedes, godkjennes og gjenåpnes med null nye CRM-aktører før fullføring. Utløpt token mister ikke et lagret valg. |
| **Lagringsfeil og kø** | API-/nettfeil gir ikke «Lagret». To faner mister ikke endringer. Søkt/filtert kø, nabo, retur, fokus og Option/Alt fungerer. |
| **Offentlig plan** | Tre aktører og én personvisning gir fire oppføringer. Samme person hos flere aktører, allerede offentlige felt og avledede visninger tas med. |
| **Fullføring** | Samtidige forespørsler, feil midt i transaksjonen og tapt svar etter commit gir korrekt resultat uten duplikater. |
| **Storage og restore** | Prosess-/containerrestart, manglende eller korrupt fil, backup/sletting samtidig og isolert gjenoppretting med korrekt kvittering. |
| **Steder** | Tvetydighet, selvbetjent opprettelse, ingen personkart, ingen skjult publisering/tilknytning og alle geografiske regelutfall i ADR-012. |

Eksisterende telefon- og bilderegresjoner videreføres. Vitest, API-/Django-tester og Playwright brukes som eksisterende testgrunnlag; minst ett sammenhengende nytt importforløp må kjøre mot ekte backend. Mocktester alene beviser ikke lagring og fullføring. [Telefontester][phonetests] · [Bildetester][imagetests] · [CI][ci]

Den godkjente tekniske nettleserverifikasjonen skal dekke 1366 × 768 og 1440 × 900, lange navn/kilder og representative jobber med 100 og 500 kandidater. API-tid, datamengde, kørespons og fullføring måles i navngitt miljø. Produksjonsgrense fastsettes fra disse målingene.

**Ingen ny formell brukertest, manuell prototyperunde eller obligatorisk kollegatest legges inn.** Prototypekontrollene 45/45 og den separate O-24-kontrollen 8/8 beholdes som artefaktevidens; de er ikke runtimeverifikasjon. [UX §14][ux]

### Tilbakeføring

Før nye semantiske data er skrevet, kan additive endringer reverseres når dette er testet.

Etter delt skriving eller ny importfullføring er normal strategi å stoppe aktuelle skrivetjenester og nye bakgrunnsoppgaver, bevare data, filer og kvitteringer, og rette fremover. Eldre lesing brukes bare der den fortsatt kan representere data sikkert.

Det skal ikke automatisk gjeninnføres ett-tenant-eierskap etter flertilknytning, global kontaktpublisering etter relasjonsspesifikke valg eller gammelt image-home etter overføring. «Avbryt import» betyr heller ikke at tidligere fullførte profilendringer eller uttrykkelig opprettede Places slettes. [ADR-011][adr11] · [ADR-012][adr12]

### Eiergodkjente hovedvalg

Prosjekteier godkjente hele planen, inkludert disse hovedvalgene, 2026-10-13:

1. **6A → 6B → 6C → fase 7**, med den avgrensede ADR-012-presiseringen som holder kart utenfor importens kritiske sti.
2. **Firearksformatet `KN_IMPORT/1`**, med flere kilderader for flere kontakter og relasjonsspesifikke kanalvalg.
3. **Versjonerte kilder, kandidater og reviewbeslutninger**, med en egen ny importkontrakt.
4. **En liten PostgreSQL-forankret worker**, avgrenset berikelse og importtilpasset bildeforberedelse.
5. **Én samlet databasetransaksjon per godkjent fullføringsplan**, med kvittering og separat status for etterleveranser.
6. **De beskrevne test-, migrerings- og aktiveringskravene**, uten nye brukertestrunder.

Denne dokumentasjonsleveransen leverer planen gjennom [PR #74](https://github.com/fredrik-stack/kreative-norge-crm/pull/74), formaliserer [ADR-013](../decisions/ADR-013-IMPORT_2_0_EXECUTION_AND_COMMIT_CONTRACT.md), presiserer ADR-012s rekkefølge og synkroniserer roadmap/status. Kontrollert dokumentasjonsmerge er bestilt; senere oppstart av 6A krever separat avgrenset bestilling.

**Kildeplanens historiske utførelse:** read-only 5E-analyse og beslutningsklar plan, uten repo-, runtime- eller stagingendring. **Denne leveransen:** Markdown-dokumentasjon på `docs/phase5e-approved-plan`, med commit/push og [PR #74](https://github.com/fredrik-stack/kreative-norge-crm/pull/74), gjennomført review og bestilt kontrollert merge. Faktisk siste head, mergestatus, mergecommit og PR-/main-CI følger GitHub og leveranserapporten; reviewheadens CI erstatter ikke kontroll av senere head eller mergecommit. Deploy og runtimeimplementering er ikke utført.

[maincommit]: https://github.com/fredrik-stack/kreative-norge-crm/commit/18951b010d46eb7beea85e6c96b228e4472893af
[pr73]: https://github.com/fredrik-stack/kreative-norge-crm/pull/73
[prci]: https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/38306273325
[mainci]: https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/38306834660
[ux]: ../features/IMPORT_2_0_UX_SPEC_V6.md
[report]: PHASE_5D_USER_TEST_REPORT_2026-10-11.md
[adr11]: ../decisions/ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md
[adr12]: ../decisions/ADR-012-PLACE_IDENTITY_GEOGRAPHIC_CLASSIFICATION_AND_ACTOR_ONLY_MAPS.md
[adr5]: ../decisions/ADR-005-CONTACT_ARCHITECTURE.md
[adr7]: ../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md
[models]: https://github.com/fredrik-stack/kreative-norge-crm/blob/18951b010d46eb7beea85e6c96b228e4472893af/crm/models.py
[permissions]: https://github.com/fredrik-stack/kreative-norge-crm/blob/18951b010d46eb7beea85e6c96b228e4472893af/crm/permissions.py
[parser]: https://github.com/fredrik-stack/kreative-norge-crm/blob/18951b010d46eb7beea85e6c96b228e4472893af/crm/services/import/parsers.py
[preview]: https://github.com/fredrik-stack/kreative-norge-crm/blob/18951b010d46eb7beea85e6c96b228e4472893af/crm/services/import/preview.py
[commitcode]: https://github.com/fredrik-stack/kreative-norge-crm/blob/18951b010d46eb7beea85e6c96b228e4472893af/crm/services/import/commit.py
[importhook]: https://github.com/fredrik-stack/kreative-norge-crm/blob/18951b010d46eb7beea85e6c96b228e4472893af/frontend/src/hooks/useImportJobs.ts
[importui]: https://github.com/fredrik-stack/kreative-norge-crm/blob/18951b010d46eb7beea85e6c96b228e4472893af/frontend/src/pages/ImportExportPage.tsx
[ai]: https://github.com/fredrik-stack/kreative-norge-crm/blob/18951b010d46eb7beea85e6c96b228e4472893af/crm/services/import/ai_suggestions.py
[imagecandidates]: https://github.com/fredrik-stack/kreative-norge-crm/blob/18951b010d46eb7beea85e6c96b228e4472893af/crm/services/images/candidates.py
[imagedecisions]: https://github.com/fredrik-stack/kreative-norge-crm/blob/18951b010d46eb7beea85e6c96b228e4472893af/crm/services/import/image_decisions.py
[publicapi]: https://github.com/fredrik-stack/kreative-norge-crm/blob/18951b010d46eb7beea85e6c96b228e4472893af/crm/views_public.py
[publichtml]: https://github.com/fredrik-stack/kreative-norge-crm/blob/18951b010d46eb7beea85e6c96b228e4472893af/crm/views_public_site.py
[impact]: PHASE_5_SHARING_DOMAIN_IMPACT_2026-08-30.md
[phonetests]: https://github.com/fredrik-stack/kreative-norge-crm/blob/18951b010d46eb7beea85e6c96b228e4472893af/crm/test_phase4f_import_phones.py
[imagetests]: https://github.com/fredrik-stack/kreative-norge-crm/blob/18951b010d46eb7beea85e6c96b228e4472893af/crm/test_phase3f_import_images.py
[ci]: https://github.com/fredrik-stack/kreative-norge-crm/blob/18951b010d46eb7beea85e6c96b228e4472893af/.github/workflows/ci.yml


## 11. Beslutningsmatrise og videreført testspor

Alle seks hovedvalg er eiergodkjent. Referansene peker til normativ grense, planlagt etappe og senere bevis; ingen av bevisene er kjørt i denne dokumentasjonsøkten.

| Hovedvalg | Normativ grense | Etappe | Test-/aktiveringsbevis |
| --- | --- | --- | --- |
| 1: 6A → 6B → 6C → fase 7; kart separat | ADR-013 beslutning §1; ADR-012 §28 | 6A–6C før 7A–7E; storage parallelt | ID/scope/private data/kontakt/tekstlig sted/PUBLIC verifisert før full import; koordinat-/provider-/kartporter ved senere kartleveranse. |
| 2: KN_IMPORT/1, flerkontakt og kanalvalg | ADR-013 beslutning §2 | 6B, 6C, 7A og 7D | Fire ark, flere kilderader til én kandidat, kontakt- og koblingsidentitet, feil referanser, motstrid, blank mot false; samme mal/prompt/validator. |
| 3: Versjonerte kilder, kandidater og review | ADR-013 beslutning §3 | 7A–7D; revision-/skrivetjenester fra 6A | Gjenåpning, to faner, stale-kontroll, uttrykkelig lagringsresultat, problem-/handlingskontrakt før UI; ingen automatisk legacykonvertering. |
| 4: PostgreSQL-worker, avgrenset berikelse/bilder | ADR-013 beslutning §4; ADR-007/008/009 | 7B; lagring parallelt, image-home fra 6A | Workerrestart/lukket browser/sene svar/forsøkstak, korrekt dataminimert payload, bildeforberedelse uten CRM-aktør, transient utløp/backupfravær og vedvarende godkjent valg; providergate før aktivering. |
| 5: Samlet DB-transaksjon/kvittering/etterleveranser | ADR-013 beslutning §5 | 7D med 6A–6C-/7C-grunnlag | Samtidighet, konflikt, feil før commit og tapt svar etter commit, idempotensnøkkel-konflikt, full offentlig plan og separate etterarbeidsfeil; ingen fil-/ledgerrollbackpåstand. |
| 6: Tester, migrering og aktivering uten ny brukertest | ADR-013 beslutning §6, testkrav og rollback; ADR-012 kartkrav består | Alle etapper, hvert sitt scope | Nye inventories ved relevante datamigreringer, named dataporter, backup/isolert restore, ekte backendreise og teknisk UI i navngitt miljø, relevant staging/eiergodkjenning; ingen ny formell/kollegatest. |

### UX- og eierkorreksjonsspor

| Kravspor | Implementerings-/testspor |
| --- | --- |
| UX-01 | 7A/7C: normal steg-/kønavigasjon uten prototypeskjermmeny eller testinstrumentering. |
| UX-02, UX-14; O-11/O-12/O-14/O-20/O-24 | 7A: fire omfang, jobbfelles Musikkontor, direkte utkastvalg, tre føranalysefiltre, alle fire grupper og låst utvalg på tvers av sider; null effekt uten reservekandidater. |
| UX-03, UX-07; O-13 | 7A/7B/7E: tre profilnivåer, korrekt kildegren, automatisk bildekandidatfunn ved behov uavhengig av profilnivå; ingen automatisk approval. |
| UX-04/UX-05/UX-06 | 7A/7C: sammenfoldet mapping, Region som UI-begrep med bevarte råkolonner, eksplisitt land/landskode og ingen Norge-gjetning. |
| UX-08/UX-10; O-04/O-15 | 7B/7C: kildebasert matching/BRREG, eksisterende CRM-kort og kort kildepolicy; gul treffinngang uten skjult godkjenning eller automerge. |
| UX-09/UX-13/UX-14; O-03/O-10/O-17/O-18/O-19/O-23 | 7C/7D: etablerte 6 hoved-/14 underkategorier, farger, disjunkte statustall/reell historikk, komplett offentlig liste og tre tekstlinjer per lukket oppføring. Ingen tidligere tre-oppføringersavkutting. |
| UX-11 | 7A/7C/7D: jobb/review lagres underveis, profiler ved fullføring; uttrykkelig Place-create er separat, ikke skjult under reviewgodkjenning. |
| UX-12; O-16/O-21 | 7C: alle reelle valg peker til riktig gul seksjonsinngang fra samme problemliste, inkludert telefonland/eier; første reelle problem ved mislykket godkjenning. |
| UX-13/UX-14; O-05/O-22 | 7C: tre kolonner innen skjermrammen, bevarte filter/søk/rulling/fokus, felles Alt/Option-/knappenabo, tom kø og synlig retur ved avhengighetshopp. |
| Videreført O-02/O-07/O-08 | 6B/6C/7C: rolle/status per relasjon, ingen lang profilliste på stedssiden, selvbetjent kontrollert Place-opprettelse på samme side. |

Historiske O-01 og O-09 videreføres bare slik nyere godkjente korreksjoner presiserer dem. O-06s ekstra musikkontorbekreftelse er erstattet av O-11; gruppeaktivering/anvendelse, valgfritt bildesøk og avkutting av offentlig liste gjeninnføres ikke. Fullt revisjonsspor, R1–R12 og historisk 45/45 samt separat 8/8 står uendret i 5D-dokumentene.

## 12. Etappevis leveranseplan

Alle etapper nedenfor er **PLANLAGT / IKKE IMPLEMENTERT / IKKE AKTIVERT / IKKE STAGINGVERIFISERT**. En senere leveranse skal rapportere kode levert, funksjon aktivert og stagingverifisert hver for seg. PR-oppdelingen er faglig scope, uten reserverte numre eller kalenderdatoer. Ingen nye kontrollfaser eller testplattformer innføres.

For hver etappe gjelder relevant eksisterende workflow/CI, additive endringer, negative tester og relevante tenant-/PUBLIC-/telefon-/bilde-/safety-regresjoner. Faktiske migrasjoner, data-apply, staging og runtimeaktivering krever sine senere avgrensede bestillinger. Browser-aktiv Codex kreves før all senere UI, inkludert grunnmurens Editor. Tallene i §6/§8/§10 er vedtatte startgrenser eller testgrunnlag, ikke måleresultater eller produksjonsgarantier.

### 6A – Deling og tilgang

**Brukerreise/garanti:** Gjenbruke en felles profil i autorisert eget Musikkontor uten private datalekkasjer, skjult profilendring eller flyttet bildestate.

**Inngang/parallelitet:** ADR-011, ADR-013 og godkjent plan; nytt avgrenset inventar før datamigrering. Storage kan forberedes parallelt. Legacytag-/privatdatapolicy før relevant delt lesing og canonical PUBLIC; produksjonsavtale-/personvernporter ved relevant aktivering.

**Sammenhengende PR-scope:** Additiv identitet/assignments og beskyttet tenant-sletting → private overlays og tilgang uten global fallback → revision-/capabilitykontrollerte skrivetjenester og gamle innganger → canonical PUBLIC/API-overgang → image-home-backfill/oppretting og sikre private writes/transfer. Hvert scope beholder sine eksisterende ADR-011-aktiveringsporter; ikke åpne delt person-/kontaktfunksjon før 6B og gamle innganger følger kontrakten.

**Kodeområder:** Organization/Person/relations/assignments/overlays, permissions, API/admin/legacyimport/bakgrunnswrites, PUBLIC projection, image-scope. Navn og DDL fastsettes ved implementering.

**Aksept/test:** Bevarte PK-er og legacyassignment; idempotent backfill; feil domain/membership/avtale/capability avvises også gjennom gamle innganger; private data ute av matching/API/eksport/PUBLIC; canonical aktør én gang, `canonical_id` og entydig orgalias; negative CASCADE-, image-home-/transfer-/historikk- og publiseringstester.

**Data/tilbakeføring:** Shadow/sammenligning før omlegging; bevar råverdier og immutable bildehistorikk. Etter multiassignment/delt skriving stoppes relevante writes og rettes fremover; ingen retur til ett-tenant-eierskap eller reassosiering av assets/ledger.

**Stoppunkt:** Scope, PRIVATE/PUBLIC og image-home teknisk verifisert med relevante aktiveringer eksplisitt rapportert; delt kontaktaktivering avventer 6B. Ingen automatisk start av neste etappe.

### 6B – Kontakter og relasjoner

**Brukerreise/garanti:** Én person med flere kontakter, forskjellige roller/titler og ulike offentlige kanalvalg hos forskjellige aktører.

**Inngang/parallelitet:** 6A-scope/revisions-/skrivetjenester og ADR-005/010. Mapping av global tittel og `is_public` før kontakt-/PUBLIC-omlegging. Storage kan fortsette parallelt; steder kommer etter kontaktgrunnlaget.

**PR-scope:** Additiv relasjon/kontakt- og e-postnormalisering → kontrollert datamapping/backfill og legacykompatibilitet → autoritative writes med samtidighet/primærregler → felles offentlig resolver/API → samlet Editor-kontaktopplevelse og cutover. Full eksport og fysisk feltdropp ligger fortsatt senere under ADR-005.

**Kodeområder:** PersonContact, kompatible direkte personfelt, OrganizationPerson, relasjonsspesifikt kanalvalg, Editor/API/PUBLIC-preview/resolver og legacyimportinnganger.

**Aksept/test:** Flere kontakter og maks én primær/type ved samtidighet; samme E.164 hos flere personer er lovlig; privat ny kontakt, blank KEEP, eksplisitt false og ingen primær-/AI-publisering; forskjellige kanaler hos to aktører; rolle/status individuelt; lik PUBLIC/HTML/API/Editor-preview/fullføringsprojeksjon og negative tenant-/domain-/kanaltester.

**Data/tilbakeføring:** Nye relasjonsvalg må ikke blindt arve global tittel/kanalpublisering. Sammenligning før cutover, bevar legacyfeltene og mapping/proveniens. Etter relasjonsspesifikke writes stoppes nye writes; ingen retur til global publication eller privat direktefeltfallback.

**Stoppunkt:** Kontakt-/relasjonsgrunnlag og nødvendige Editor-/API-/PUBLIC-reiser verifisert i relevant staging, med godkjent omleggingsgrunnlag. Full ADR-005 merkes fortsatt ikke ferdig.

### 6C – Stedskjerne

**Brukerreise/garanti:** Velge, gjenbruke eller opprette entydig norsk/utenlandsk sted og få forklarte geografiske forslag uten kartprovider eller personkart.

**Inngang/parallelitet:** 6A og 6B, ADR-012s daterte §28-presisering; nytt avgrenset sted-/relasjonsinventar før relevant datamigrering. Koordinat/provider/kart er separat senere, ikke inngangsavhengighet for kjerneimport.

**PR-scope:** Place/offisiell kildeidentitet og kontrollert create/reuse → additive OrganizationPlace/PersonPlace med raw/proveniens → inventory/parser/code-matching/shadow og tvetydighetsreview → GeographicTenantRuleSet/shadow → nødvendige Editor-writes/additivt API og tekstlig PUBLIC med relevant cutover. Bevar ADR-012s indre stedskjernerekkefølge; ingen kartkrav slettes.

**Kodeområder:** Globale referansedata og typed aktør-/personrelasjoner, legacy municipality-/municipalities-felter, geografiske regler, kontrollert tjeneste, Editor/API/PUBLIC-tekst og senere STEDER-binding.

**Aksept/test:** Duplicate-/similarity-, scope-/revisionkontroll, entydig source-backed eller brukerbekreftet create/reuse uten obligatorisk plattform-superadmin; bare globale konflikter eskaleres. Ingen personkoordinater/-kart/providerinput med personidentitet; alle ADR-012s geografiske regelutfall, tvetydighet/private sted/publication og ingen automatisk assignment. Norsk kildegrunnlag og utenlandske/uavklarte utfall bevares.

**Data/tilbakeføring:** Bevar råtekst/ID-er, idempotens og shadow før typed writes. Uttrykkelig canonical Place-create før importcommit bevares ved avbrudd. Etter typed writes må sikker legacylesing bevises før eventuell bruk; ellers stopp writes og rett fremover. Fysisk cleanup er separat senere.

**Stoppunkt:** Stedskjerne/geografiske forslag/nødvendig Editor/additivt API/tekstlig PUBLIC teknisk verifisert. STEDER og Import 2.0 kan deretter leveres; koordinat-, provider- og karttester gjennomføres i separat kartleveranse.

### Parallell storageleveranse

**Brukerreise/garanti:** Originalpakke, rapport og lagrede valg overlever prosess-/containerrestart og kan gjenopprettes konsistent.

**Inngang/parallelitet:** ADR-008/009 og ADR-013s manifest-/filgrenser. Kan forberedes parallelt med 6A–6C. Retensjon for kilde/DB-rådata/rapporter og ferdige utilknyttede bilder avklares før første reelle v2-lagring/opplasting.

**PR-scope:** Privat persistent lagringskobling og filmanifest → samordnet backup/sletting/retensjonsmekanisme → isolert restore med hele jobbkjedens referanser og manglende/korrupt fil-status. Ingen credentials eller runtimeområder opprettes i denne planleveransen.

**Kodeområder:** Filmanifest/kildesnapshot/rapporter, storageadapter og senere deploymentmounts, eksisterende backup-/restoreoppsett og retensjonsarbeid. Transient providertransport holdes utenfor varig storage og alle backupkopier.

**Aksept/test:** Ferdig fil før DB-ready, checksum/størrelse/versjon/tilgjengelighet; restart, korrupt/manglende fil, backup/sletting samtidig og isolert jobb → kilde → kandidater → beslutninger → kvittering → rapport/filer. Bevis at kortlivet minnetransport med absolutt 30-minuttersutløp ikke følger backup.

**Data/tilbakeføring:** Nye lagringsområder gjenskaper ikke historisk tapte filer; gammelt manglende grunnlag vises ærlig. Ved feil stopp ny opplasting/etterarbeid og bevar eksisterende filer/kvitteringer; restore følger gjeldende retention- og deny-first-kontrakt uten reaktivering av utløpt providerdata.

**Stoppunkt:** Privat persistens, retensjonsgrunnlag og backup/isolert restore verifisert før første reelle v2-opplasting. Automatisk staging-deploy er ikke en avhengighet.

### 7A – Kilde, mapping og jobbregler

**Brukerreise/garanti:** Standardpakke eller egen CSV/XLSX/Checkin-Excel blir et varig utkast med presis kildeidentitet, flerkontakt, mapping og O-24-regler.

**Inngang/parallelitet:** Verifisert 6A–6C og normativ ADR-013; privat storageport før reelle uploads. Syntetiske kontrakt-/maltester kan forberedes uten produksjonsaktivering. Problem-/handlingskontrakt etableres før 7C-UI.

**PR-scope:** KN_IMPORT/1-skjema/standardmal/samme KI-prompt/validator → firearksparser, referanser og konsolidering → fri CSV/XLSX-mapping/arkvalg → versjonert utkast/API og gjenåpning → O-20/O-24-regler og start-UI.

**Kodeområder:** ImportJob/arbeidsflytversjon, kildesnapshot/manifest/rader/kandidater, parser/normalizer, API, frontend/jobbutkast og mal/prompt.

**Aksept/test:** Flere kontakt-/koblingsrader gir én riktig kandidat, feil source-ID/referanse og motstrid blir review, blank ikke false, person uten kontakt gyldig; samme mal/prompt/validatorversjon; eksplisitt Musikkontor uten ekstra radboks; tre filtre × aktør/person × null/ikke-null treff, fire aktive grupper med fast utvalg over innlastede sider og stedsvirkning uten andre profiler/felles stedskandidat; ekte lagringsresultat/to faner/gjenåpning.

**Data/tilbakeføring:** Ingen automatisk legacyjob-konvertering eller destruktiv rerepreview av v2-grunnlag. Før semantiske writes kan additiv kobling reverseres når bevist; etter ny lagring stopp nye writes, bevar kilde/revisjoner og rett fremover.

**Stoppunkt:** Hele startreisen teknisk verifisert mot backend med gjenåpning og korrekte regler. Analyse-/review-/fullføringsaktivering avventer følgende etapper.

### 7B – Analyse og berikelse

**Brukerreise/garanti:** Analyse fortsetter med lukket nettleser, sanne statustall og kildebelagte forslag; bilde kan forberedes før ny profil opprettes.

**Inngang/parallelitet:** 7A-versjoner/utkast, 6A-scope/image-home og lagringsgrenser. Provideren aktiveres bare etter sin eksisterende gate; kjente offisielle kilder/URL/upload/fallback kan fungere uten Brave. Ingen åpen modell-/pris-/volumkontrakt fylles inn med nye beslutninger.

**PR-scope:** Vedvarende PostgreSQL-reservasjon/restart/retry/stale-resultat → matching/kildeproveniens og avgrenset BRREG/profilmodellberikelse → importtilpasset bildekandidat/preview/processing/approval med transient transport → reell analyse-/dashboardstatus.

**Kodeområder:** Konseptuelle arbeidsoppgaver i eksisterende image, services/import, providers, AI-payload, images/candidates/image_decisions, API og dashboard. Ingen køplattform utover godkjent liten worker innføres uten målt behov.

**Aksept/test:** Nettleserlukking/restart, korte reservasjoner uten låser under providerkall, versjons-/rettighetsendring og sene svar; alle vedtatte kall-/forsøk-/input-/output-/timeoutgrenser fra ADR-013 §4; private payloadfelter ute; ingen identitets-/publiseringsapproval. Bilder ved alle profilnivåer, behold låst bilde, høyst ett automatisk Brave-søk ved tillatt gate, null nye CRM-aktører før commit og bevart approval ved utløpt preview/cachetap.

**Data/tilbakeføring:** Stopp nye oppgaver/providerarbeid ved feil; bevar varig kilde/valg/bildegrunnlag. Uvalgte transientdata må utløpe og aldri gjenopprettes via backup; retry kan oppfriske treff uten tapt godkjent asset eller ny profil.

**Stoppunkt:** Uavhengig serverkjøring og bildeforberedelse teknisk verifisert, med aktiverte/deaktiverte providers oppgitt og ærlig kildefravær. Ingen automatisk kandidatgodkjenning.

### 7C – Gjennomgang

**Brukerreise/garanti:** Rolig trekolonne-review med konsoliderte kandidater, synlige kilder, riktige avklaringshandlinger og bevart arbeidskontekst.

**Inngang/parallelitet:** 7A-problem-/handlings-/revisjonskontrakt og 7B-kandidat-/kildeforberedelse; 6B/6C-feltvalg. Browser-aktiv Codex før UI. Backendproblem-/navigationkontrakt kan kontrolleres før layoutarbeid, uten ny kontrollfase.

**PR-scope:** Kandidatsammendrag/serverfilter/50-puljer og én detaljflate → gul problemliste/første reelle problem/avhengighetsretur → identitet/kilder/feltkonflikter/kontakt/relasjon/sted/bilde/offentlig valg → autosave/gjenåpning/dashboard/køintegrasjon.

**Kodeområder:** Reviewbeslutninger/revisjoner/problemer, kandidat-/kilde-API, React-review/kø/sections og eksisterende felt-/bilde-/PUBLICkomponenter.

**Aksept/test:** O-21/O-22, Saga telefonland/eier, gul seksjonsinngang uten godkjenning; knapper/klikk/Option/Alt samme søk/filter/grenser, sorteringsanker uten nabo-overhopp, siste feltavklaring står åpen, tom kø uten reserve og synlig retur; to-faner-/nettfeil ikke Lagret; hoved-/underkategori og eksisterende taksonomi, individuelt rolle/status, jobbvalgt Musikkontor uten ekstra bekreftelse; ingen ny obligatorisk bildegodkjenning eller universelle feltkrav.

**Data/tilbakeføring:** Reviewgodkjenning skriver beslutning, ikke profil. Stale konflikt viser hva må revurderes og bevarer tillatt arbeid. Ved UI-/API-feil stopp nye reviews; eksisterende versjoner/kilde-/approvalspor slettes ikke.

**Stoppunkt:** Reviewreiser mot ekte backend og teknisk browserverifikasjon i godkjente skjermstørrelser og med 100 og 500 kandidater, med målte resultater i navngitt miljø. Ingen ny manuell prototypetest/formell brukertest/obligatorisk kollegatest.

### 7D – Sluttkontroll og fullføring

**Brukerreise/garanti:** Brukeren bekrefter hele offentlige forskjellen og får ett etterprøvbart DB-resultat med kvittering og tydelig etterleveransestatus.

**Inngang/parallelitet:** 7C-godkjente versjoner, 6A–6C-skrivetjenester og felles PUBLIC, varig lagring/restore og eksisterende bildesafety. Uavklart kandidat/avhengighet avklares eller uttrykkelig utelates før fast plan.

**PR-scope:** Serverplan/full offentlig projeksjon → fingerprint-/bekreftelses-/stale-kontrakt → stabil låserekkefølge/atomisk audit/kvittering/idempotens → varige rapport-/bildeetteroppgaver og resultat/retry → sammenhengende teknisk stagingreise/tilbakeføringsbevis.

**Kodeområder:** Fullføringsplan/kvittering, separate profil-/overlay-/kontakt-/relasjon-/assignment-/sted-/publication-/bildehandlinger, PUBLIC resolver, transaksjon/locks, etterarbeid/rapporter og slutt-/resultat-UI.

**Aksept/test:** Tre aktører og én personvisning gir fire synlige oppføringer; person hos flere aktører og eksisterende offentlige visninger utenfor importkilden tas med; O-23 trelinjersrader uten Vis alle, full bekreftelse oppheves ved endring. Samtidige fullføringer, nøkkel med annet payload, rettighets-/avtale-/objektrevisjonsendring, feil midt i DB-transaksjon og tapt svar etter commit gir ingen duplikater. Ingen provider/fetch/processing ved commit; deny-/stale-/image-home kontrolleres lokalt. Etterarbeidsfeil viser lagret DB-resultat og retry uten ny import.

**Data/tilbakeføring:** Før commit rollbackes DB-endringene samlet. Etter commit bevares data/audit/kvittering/filer/ledger og relevante writes/oppgaver stoppes ved feil; rett fremover, ingen falsk fil-/ledger-atomicitet. Restore følger samme kvittering og deny-first-vern.

**Stoppunkt:** Sammenhengende ny importreise mot ekte backend, relevant staging-/eiergodkjenning og prøvd tilbakeføring med målte API-/datamengde-/kø-/fullføringsresultater; produksjonsgrense fastsettes fra måling, ikke planens demotall.

### 7E – Google Sheets og v1-lukking

**Brukerreise/garanti:** Velge konto, regneark/faner og lagre ett kildesnapshot som går gjennom samme importreise som filkjernen.

**Inngang/parallelitet:** CSV/XLSX-kjerne 7A–7D og source-/storage-/tilgangskontrakt. Google/provider-/personvernkrav ved adapterens faktiske aktivering. Ingen synkronisering eller tilbakeskriving og ingen kart-/direkte Checkin-/Mailmojo-avhengighet.

**PR-scope:** Smal kildeadapter og autorisert konto/ark/faner → versjonert snapshot med referanser/tilgjengelighet → standardpakke- eller mappinggren og håndterte kildefeil → teknisk helreise og v1-lukking.

**Kodeområder:** Kildeadapter, snapshot/manifest og proveniens, API, kilde-UI og gjenbruk av mapping/review/fullføring.

**Aksept/test:** Én primær tilkobling, korrekte faner/antall, manglende tilgang og kildefeil uten tapt utkast, gjenåpning fra snapshot, ny innhenting bare uttrykkelig; standardpakke til kontroll, annet til mapping; idempotent review/commit/resultat gjennom samme backendreise og øvrige regresjoner.

**Data/tilbakeføring:** Stopp ny innhenting/adapter ved feil; bevar eksisterende jobb/snapshot/kvittering og faktisk lagret resultat. Ingen automatisk sletting eller fullføringsreplay fordi originalarket er endret eller utilgjengelig.

**Stoppunkt:** Sheets teknisk verifisert med relevant staging-/eiergodkjenning etter filkjernen og før v1 lukkes. Checkin-Excel er dekket i 7A; direkte API/Mailmojo/kart/XML inngår ikke som nye v1-blockere.
