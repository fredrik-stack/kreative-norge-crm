# Editor og PUBLIC – samlet UI/UX-ferdigstilling

**Dato:** 2026-10-24. **Status:** Eierbestilt planpresisering; ingen UI er implementert eller nyverifisert i denne leveransen.

## Mandat og styrende grunnlag

Planen plasserer resterende brukerflater i navngitte leveranser og definerer
samlet v1-aksept. Mandatet omfatter bare dokumentasjon, én PR, faktisk separat
skrivebeskyttet review, ordinær merge og grønn CI. Ingen kode, migrasjon,
database-/browser-/stagingkjøring, deploy eller provideraktivering. Baseline er
`f621db52a51b059b3bb8ed5f0116138783dbd2fb` etter PR #85–86.

Dette er et tverrgående ferdigstillingsspor innen vedtatt **6A → 6B → 6C →
7A–7E**, med eksport i fase 8. Leveransenavnene nedenfor deler opp UI-arbeidet;
de innfører ingen ny backendfase, generell redesign eller ny ADR-/5E-/UX-runde.
[Roadmap](ROADMAP.md) angir rekkefølgen; denne matrisen styrer flatedekning og
aksept. Arkitektur-/datagater i eksisterende ADR-er består.

Kilder brukt i matrisene:

- **F:** [Roadmap fase 1](ROADMAP.md#fase-1--verifiser-staging--og-frontend-baseline) og [datert frontendbaseline](FRONTEND_BASELINE_2026-07-29.md): hoveddesignet på Editor-/PUBLIC-forsidene er referanse; baseline er historisk, ikke dagens visuelle godkjenning av alle sider.
- **E/P:** [Editor](../architecture/EDITOR.md), [PUBLIC-arkitektur](../architecture/PUBLIC.md) og [PUBLIC-produkt](../features/PUBLIC.md): implementert grunnløsning og avgrensninger.
- **K:** [ADR-005](../decisions/ADR-005-CONTACT_ARCHITECTURE.md), særlig §6 og leveransene for samlet Editor-kontaktopplevelse, samt [5E §12/6B](PHASE_5E_IMPLEMENTATION_AND_TEST_PLAN_2026-10-13.md#6b--kontakter-og-relasjoner).
- **D:** [ADR-011](../decisions/ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md), særlig §§5–10 og migreringsstrategien; [notatrutematrise](../operations/TENANT_NOTE_OVERLAYS.md#faktiske-ruter-og-senere-omlegging) og [stagingevidens](STAGING_PHASE_6A_NOTE_OVERLAYS_2026-10-24.md).
- **S:** [ADR-012](../decisions/ADR-012-PLACE_IDENTITY_GEOGRAPHIC_CLASSIFICATION_AND_ACTOR_ONLY_MAPS.md), særlig §§8,12–13,17–23,28, og [5E §12/6C](PHASE_5E_IMPLEMENTATION_AND_TEST_PLAN_2026-10-13.md#6c--stedskjerne).
- **I:** [UX v6 revisjon 4/O-24](../features/IMPORT_2_0_UX_SPEC_V6.md), [godkjent 5E-plan](PHASE_5E_IMPLEMENTATION_AND_TEST_PLAN_2026-10-13.md#12-etappevis-leveranseplan) og [ADR-013](../decisions/ADR-013-IMPORT_2_0_EXECUTION_AND_COMMIT_CONTRACT.md). Krav/artefakt er owner-approved; dette er ikke godkjenning av implementert Import 2.0.

## 1. Status og bevis – per flate

**Kode** betyr kontrollert repo, **aktiv** krever dokumentert miljø/flaggbasis,
og **visuelt godkjent** gjelder bare datert, avgrenset eierbevis. Et API/en modell
eller grønn CI er ikke ferdig UI. Ingen ny browser-/visuell kvalitetskontroll er
utført her. ID-ene kobler statusmatrisen til leveranse-/akseptmatrisen i §2.

| ID / flate eller reise | Godkjent krav / kilde | Faktisk kode, aktivering og bevisnivå ved baseline |
| --- | --- | --- |
| U1 Navigasjon og aktivt Musikkontor | F, E, D: gjenbruk godkjent form; tydelig autorisert arbeidskontekst | AppShell har tenantvelger, Aktører/Personer/Import-eksport og URL-ruter. Legacyrolle-/tenantscope er aktiv grunnløsning; shared membership/agreement/capabilities er ikke aktivert. Historisk forsidereferanse, ingen ny samlet visuell verifikasjon. |
| U2 Aktør-/personoversikt, søk og filtre | F, E: viderefør oversiktene og eksisterende kategori-/underkategori-/taggfiltre innen godkjent retning | OrganizationsPage/PeoplePage og App/useEditorData har lister/kort/modal, søk og filtre. [Fase-4-eiergodkjenning](PHASE_4_OWNER_APPROVAL_2026-08-29.md) dekker konkrete telefon-/knappepunkter; øvrig oversiktsaksept er ikke dermed bevist. |
| U3 Detalj, oppretting og redigering | F, E, D: konsistente kort/skjemaer/handlinger; forklar felles endring | Eksisterende profilruter og legacy CRUD, ulagrede endringer og bildearbeidsflyt finnes. Bilde-/fase-4-godkjenninger er avgrensede; hele profilreisen er ikke ferdigmeldt. |
| U4 Kontakter, relasjoner, publisering og preview | K, D, 5E/6B: én kontaktseksjon, kanalvalg per kobling, felles offentlig projeksjon | Direkte personfelt + PersonContact og global is_public/publish_person er aktiv mellommodell. Relasjonsspesifikk kanalpublisering og full samlet kontaktopplevelse er ikke implementert. |
| U5 Private arbeidsdata, visning/søk/lagring | D: eksakt tenantprivat scope, tydelig felles/privat | Legacy note/tags brukes i UI/søk/import. PR #85–86 ga bare tomme overlaytabeller og gate av; tekniske API/admin-lesebevis er ikke privat overlay-UI eller visuell godkjenning. |
| U6 Stedsvalg/-redigering og tekstlig offentlig sted | S, 5E/6C: søk/velg/gjenbruk/kontrollert opprett Place; PersonPlace uten kart | Fritekst municipality/municipalities er implementert. Typed Places/relasjoner, create/reuse og nytt steds-UI er målarkitektur, ikke aktiv funksjon. |
| U7 Importstart, kilde/mapping/regler | I §§3–6/O-24 og 5E/7A | Legacy ImportExportPage/motor finnes. Godkjent v6-prototype/krav er ikke ny runtime; 7A er ikke implementert. |
| U8 Analyse og dashboard | I §7 og 5E/7B | Legacy preview-/jobbflate finnes; nytt vedvarende analyse-/dashboardløp med sanne statusantall er ikke implementert. |
| U9 Importgjennomgang | I §8/O-20–22 og 5E/7C | Godkjent desktopreise/prototype; ny trekolonners backendkoblet gjennomgang er ikke implementert. |
| U10 Sluttkontroll og resultat | I §§9–10/O-23 og 5E/7D | Legacy commit finnes; ny komplett offentlig før/etter-plan, kvitterings-/etterarbeidsreise og resultat er ikke implementert. |
| U11 Google Sheets-kilde | I og 5E/7E | Vedtatt v1-importomfang; ingen implementert adapter. Ingen kontinuerlig synkronisering eller tilbakeskriving er bestilt. |
| U12 Eksport | Roadmap fase 8, E/P og notatrutematrise | UI for felter/type/format, jobbmetadata og eventuell fillenke finnes. ExportJob/API er teknisk grunnlag; generell CRM CSV/XLSX-generering og ferdig nedlastingsreise er ikke implementert som produkt. |
| U13 PUBLIC-liste, søk/filtrering | F, P, D: kontrollert publisert utvalg, senere én canonical aktør én gang | HTML-listen har q/tag/category/subcategory og kort. API har egen read-only kontrakt; samme filtermuligheter som HTML er ikke bevist/vedtatt. HTML brukes i staging; bildeprojection er dokumentert aktiv. Endelig helhetsdesign/filtrering er uavklart. |
| U14 PUBLIC-detalj, kontakt-/stedsvisning | P, K, D, S: canonical identitet og felles offentlig resolver | HTML har ID-detalj og entydig orgnr.-redirect; API bruker fortsatt orgnr.-oppslag. Dagens kontaktmellomregel og bildeprojection er aktive/dokumentert. Framtidig canonical_id, relasjonsspesifikke kontakter og typed steder er ikke ferdig UI. |
| U15 Google Maps-aktørkart i Editor og PUBLIC | S §§17–23/28 og vedtatt v1-omfang: begge kart, ingen personkart | Ingen implementert kartflate eller provideraktivering. Sted-/provider-/koordinat-/vilkårsporter gjenstår. Valgfri/deaktiverbar Google-adapter betyr ikke at de to avtalte v1-kartene kan utelates. |
| U16 Administrasjon/forvaltning | Eksisterende Django admin, D og S: sikre gamle innganger og global konfliktforvaltning | Django admin er implementert; notatgrunnmuren er ikke registrert. ADR-roller/modeller gir ikke automatisk omfang for nye selvbetjente adminskjermer. Ingen ny samlet visuell adminaksept. |

Kodegrunnlaget er kontrollert i `frontend/src/App.tsx`, `hooks/useEditorData.ts`,
`pages/OrganizationsPage.tsx`, `PeoplePage.tsx`, `ImportExportPage.tsx`,
`crm/views.py`, `views_public.py`, `views_public_site.py`, serializers/admin og
PUBLIC-templates. Seneste notatstaging gjelder backend/schema, ikke ny frontend.

## 2. Leveranse, gjenstående arbeid og ferdigkriterier

Alle rader må også oppfylle felles aksept i §4. V1–V6 viser til reelle valg i §5.
Ingen rad gir implementerings-/aktiveringsfullmakt uten separat bestilling.

| ID | Navngitt leveranse / plassering | Gjenstående UI/UX og faktisk avhengighet | Konkret ferdigkriterium / valg |
| --- | --- | --- | --- |
| U1 | **UI-6-NAV – navigasjon og Musikkontor-kontekst**, fase 6/6A | Konkretiser felles shell i UI-6-FELLES; koble rettigheter/avtaletilstand når 6A-kontrakten er klar | Bytte Musikkontor, navigere og returnere med forståelig kontekst/ulagret-varsel; feil tenant eller manglende tilgang gir korrekt tilstand uten datalekkasje. |
| U2 | **UI-6-OVERSIKT – aktør- og personoversikter**, fase 6 | Ferdigstill kort/tabell, søk/filter, tomtilstand og overgang til detalj; assignment-/privatscope fra 6A, kontakt-/stedstillegg fra 6B/6C | Søk → filtrer → åpne → tilbake bevarer forståelig utvalg; lange navn/mange treff fungerer. Privat note-/taggsøk følger U5, ikke domenebred legacylesing. |
| U3 | **UI-6-PROFIL – profilvisning og skjemaer**, fase 6 | Felles utforming kan konkretiseres nå; shared writes/revision/publication i 6A før aktivering, U4/U6 integreres i 6B/6C | Opprett → rediger → lagre → gjenåpne med korrekt resultat, konflikt/feil/ulagret tilstand og tydelig felles effekt. Etablerte bildevalg/safety bevares. |
| U4 | **6B-KONTAKT – samlet kontakt-/relasjonsopplevelse** | Flere kanaler, primær, individuell rolle/tittel/status, kanalpublisering per aktør, preview, synlig lagring/sticky handling og bedre desktopplass; 6A + kontakt-/tittelmapping og felles resolver | Samme person kan ha forskjellige kanaler/roller hos to aktører; interne verdier blir ikke offentlige; oppretting/kobling/lagring er sammenhengende og preview stemmer med PUBLIC. Ingen full ADR-005-ferdigmelding før øvrige leveranser. |
| U5 | **UI-6-PRIVAT – private notater og avtalte arbeidsdata**, 6A | Egen notatflytting, samlet reader/writer/søk-omlegging og tilgang/audit før UI-aktivering. Taggpolicy og eventuell ny intern-tagmodell er separate leveranser, ikke levert grunnmur | Tydelig felles/kun eget Musikkontor i visning og lagring; NULL/tom/tekst håndteres uten gammel fallback; ingen cross-tenant visning, søk eller providerpayload. V1/V2 før relevant omlegging; ingen nye generiske arbeidsstatus-/samtykkeflater utledes av ADR-listen. |
| U6 | **6C-STED – stedskjerne og stedsopplevelse** | Velg/gjenbruk/kontrollert opprett, norsk/utenlandsk/uavklart, forklarte forslag og tekstlig PUBLIC; krever 6A/6B og Place-tjenester/migreringsgrunnlag | Autorisert normalbruker kan fullføre stedslagring uten plattformadmin, tvetydighet gir eksplisitt valg og ingen skjult publisering/assignment. Person uten kart. Fungerer uten Google. |
| U7 | **7A-START – kilde, mapping og jobbregler** | Implementer godkjent startreise etter 6A–6C; persistent storage før reelle uploads; O-24 består | Fil/standardpakke/Checkin-Excel → korrekt utkast/mapping/regler → lagre/gjenåpne. Alle fire regelgrupper virker under alle tre filtre for aktør/person, også null treff. |
| U8 | **7B-ANALYSE – analyse og dashboard** | Vedvarende worker, kilde-/berikelsesstatus og bildegrunnlag før ny profil; krever 7A/storage og eksisterende providergater | Lukk/gjenåpne nettleser under analyse; reelle statusantall, fremdrift/neste handling og nylige jobber stemmer med backend. Feil skjules ikke som manglende data. |
| U9 | **7C-GJENNOMGANG – konsolidert review** | Implementer vedtatte tre kolonner/kø/kilder/avhengighetsretur; krever analyse og problem-/handlingskontrakt | Godkjent desktop-/skjermkontrakt, puljer på 50, bevart søk/filter/fokus/rulling/nabo, riktige gule innganger og ærlig lagring mot ekte backend; ikke full mobilimport. |
| U10 | **7D-FULLFØRING – offentlig sluttkontroll og resultat** | Hele offentlige endringsplanen, eksplisitt bekreftelse/stale, kvittering og etterarbeid; krever 7C og 6A–6C-writers/resolver/storage | Hele planen vises, bekreftelse ugyldiggjøres ved endring; ett etterprøvbart lagringsresultat, tydelig etterarbeidsfeil/retry uten ny import; helreise og tilbakeføring verifisert. |
| U11 | **7E-SHEETS – kildeadapter og importsporets lukking** | Konto/ark/faner → snapshot gjennom samme reise, etter 7A–7D og relevante provider-/tilgangsporter | Snapshot kan gjenåpnes uten ny innhenting, kildefeil mister ikke utkast og samme review/commit/resultat fungerer. Lukker importsporet, ikke hele produktet. |
| U12 | **8-EKSPORT – eksportopplevelsen**, fase 8 | Fullfør vedtatte felt-/filter-/formatvalg, generering, jobbstatus og sikker nedlasting; kontakt-/privat-/PUBLIC-kontrakter og nødvendig lagring først | Valgt intern arbeidsliste, offentlig katalog eller e-postliste kan faktisk genereres/nedlastes med riktige data/rettigheter; feil/manglende fil og tomt utvalg forstås. V6 før konkret eksportbestilling; ingen ny integrasjon utledes av modellen. |
| U13 | **PUBLIC-V1-LISTE**, del av **PUBLIC-V1 – helhetlig PUBLIC** | Ferdigstill liste/kort/søk/filter etter godkjent retning; kan konkretiseres parallelt, runtime mot nødvendige 6A–6C-kontrakter | Publisert aktør én gang, forståelige kombinerte filtre/null treff/tilbakestilling, lange navn og responsive kort. Ingen private tags eller notater. V3/V4 før detalj-/API-omlegging. |
| U14 | **PUBLIC-V1-DETALJ**, samme PUBLIC-V1 | Samlet aktørdetalj, kontakt/sted/lenker/bilde og retur; krever canonical PUBLIC, 6B-resolver og 6C-tekstlige steder | Aktør uten orgnr. har fungerende side; entydig alias; kontakt-/sted-/bildevisning følger felles PUBLIC-kontrakt uten private data. V3/V4 avklart før implementering. |
| U15 | **KART-V1 – begge Google Maps-aktørkart**, separat etter nødvendig sted-/providergrunnlag og før samlet v1 | Editor-listesamspill og PUBLIC-kart; gyldige koordinater, restore-sikker providerlivssyklus, tillatelser/vilkår og separat aktivering etter S. Kan leveres parallelt med import når egne porter er klare | Begge flater verifisert: tillatte aktører/steder, liste↔markør, ingen personer/private data/doble assignments; manglende koordinat/provider/key gir fortsatt brukbar liste. Deaktiverbar fallback er ikke bevis på ferdig kart. |
| U16 | **UI-6-ADMIN – avgrenset forvaltning og gamle innganger**, innen berørte 6A–6C-leveranser | Bevar/sikre eksisterende admin og nødvendige konflikthåndteringsinnganger; ikke bygg nytt adminprodukt fra rollematriser | Eksisterende tillatte oppgaver virker, nye writes omgår ikke kontraktene; uautorisert handling avvises. V5 avgrenser eventuelle nye v1-skjermer før bestilling. |

## 3. Parallellitet og milepæler

**UI-6-FELLES – felles utforming og restflater** konkretiseres under fase 6 fra
godkjente forsider og eksisterende komponenter: navigasjon, kort/tabell,
detalj/skjema, handlinger og tilstander for U1–U6/U16. Neste avgrensede bestilling
kan beskrive disse flatene uten å åpne import-UX på nytt. PUBLIC-listens/detaljens
visuelle konkretisering og V3/V4 kan gå parallelt. Dette er utforming/avklaring;
ny privat-/shared-/kontakt-/stedfunksjon venter på sin backend-/dataport.

Runtime følger 6A → 6B → 6C → Import 2.0. UI-6-OVERSIKT/PROFIL leveres med
nødvendige 6A-funksjoner, får sine kontakt-/stedstillegg i 6B/6C og lukkes i
Editor-kjernemilepælen. Ikke utsett disse til en ubestemt polishkategori.
**PUBLIC-V1** kan implementeres parallelt med import etter nødvendige
6A–6C-kontrakter; den trenger ikke vente på 7E. **KART-V1** kan gå parallelt når
sted-/koordinat-/providerportene er oppfylt og skal ikke blokkere kjerneimporten.
Fase 8 fullfører eksportreisen; det legges ikke til frister eller estimater.

| Milepæl | Hva som faktisk må være ferdig | Hva milepælen ikke ferdigmelder |
| --- | --- | --- |
| M-EDITOR-KJERNE | UI-6-NAV/OVERSIKT/PROFIL/PRIVAT, 6B-KONTAKT, 6C-STED og avtalt UI-6-ADMIN, med §4-bevis | Import, eksport og aktørkart |
| M-IMPORT-KJERNE | 7A–7D sammenhengende mot ekte backend/staging etter 5E | Sheets og samlet v1 |
| M-IMPORT-7E | Kjerne + 7E-SHEETS; importens godkjente v1-reise | Hele Editor, PUBLIC, eksport eller kart |
| M-PUBLIC-KJERNE | PUBLIC-V1-LISTE/DETALJ og nødvendige 6A–6C-kontrakter, §4-bevis og avklart V3/V4 | Kart eller produksjonssetting |
| M-KART | Begge avtalte aktørkart teknisk/visuelt verifisert med egne provider-/aktiveringsporter | Manglende øvrige produktflater |
| M-EKSPORT | 8-EKSPORTs faktiske genererings-/nedlastingsreise og §4-bevis | Ikke-avtalte integrasjoner |
| **EDITOR V1 FERDIG** | Editor-kjerne + Import 7E + eksport + Editor-aktørkart + avklart avtalt adminscope | Ekstra funksjoner uten eierbestilling |
| **PUBLIC V1 FERDIG** | PUBLIC-kjerne + PUBLIC-aktørkart + avklart publiserings-/integrasjonsgrense | Automatisk deploy til Musikkontoret.no/produksjon |
| **SAMLET PRODUKT V1** | Begge foregående ferdigkriterier oppfylt, avtalte reiser akseptert og relevante data-/tilgangs-/driftsporter oppfylt | Hele langsiktige ADR-er eller framtidig uavklart funksjonsomfang |

«7E – Google Sheets og v1-lukking» beholder sin historiske tittel i 5E. **Lukking
gjelder importsporet.** Formuleringer om at kart ikke er nye v1-blockere leses i
importsporets avhengighetskontekst: Google Maps-aktørkart i **både Editor og
PUBLIC inngår fortsatt i samlet v1**. Ingen personkart. Ingen ny formell
brukertest, manuell prototyperunde eller obligatorisk kollegatest innføres.

## 4. Felles aksept ved senere implementering

Hver flate får en konkret start→handling→lagret/tilgjengelig resultat→retur-reise,
med tillatt og avvist tilgang. Før UI implementeres kreves browser-aktiv Codex;
senere verifikasjon må gå mot ekte backend og relevant staging-/eiergodkjenning.
Lagre faktisk versjon, miljø, kontrollert reise/bredde og resultat i leveransens
evidens; ikke erstatt bevis med et generelt «ferdig» eller en CI-status.

- Godkjent visuell retning videreføres konsistent i navigasjon, kort, skjemaer og primærhandlinger. Tastatur/fokus, forståelige navn og tekst ved fargestatus følger eksisterende UX-prinsipper.
- Vis ulagret/lagrer/lagret, validering, konflikt/nettverksfeil og sikker retry ærlig. Tomme treff, tom profil, manglende felt, manglende tilgang og deaktivert funksjon skal ha forståelig neste handling der relevant.
- Verifiser lange navn/stedsverdier, mange oppføringer, intern rulling og relevante skjermbredder uten bortgjemte handlinger. Editor/PUBLICs relevante desktop-/smalere visninger konkretiseres per flate; import beholder godkjent desktop- og skjermkontrakt i UX §§8.1/12 og 5E, uten utvidelse til full mobilimport.
- Felles opplysninger, bare eget Musikkontors arbeidsdata og offentlig innhold må være forståelig forskjellige. Publiserings-/kanalvalg, global endring og offentlig før/etter/preview skal stemme med backend; ingen frontendfallback som gjeninnfører privat eller gammel tekst.
- Fullfør relevante tekniske regresjoner og faktisk visuell kontroll for endret scope; bevar allerede godkjente telefon-/bilde-/importkontrakter. En historisk godkjenning av ett felt eller forsiden dekker ikke automatisk resten av reisen.

## 5. Reelle valg – anbefaling og beslutningstidspunkt

| Valg | Hva som fortsatt er uavklart | Konkret anbefaling / tidspunkt |
| --- | --- | --- |
| V1 Notatautoritet | Egen flytteplan og samlet visning/søk/writeromlegging er ikke godkjent av denne planen | Konkretiser tapsfri flytting bare til egen eksisterende assignment, uten NULL/tom-fallback; alle aktive API/Editor/admin/import/direkte baner må håndteres samlet. Prosjekteier godkjenner konkret data-/overgangsbestilling før relevant apply/privat UI-aktivering. |
| V2 Legacytags/andre private arbeidsflater | Ingen foreslått taggmapping-policy fra notatleveransen er valgt. ADR-listen er ikke en ferdig v1-skjermbestilling | Avgjør eksplisitt mapping-/redaksjonell prosess før relevant shared lesing/PUBLIC og intern-tag-UI; ingen automatisk klassifisering etter navn/tenant/publisering. Avgrens eventuell ekstra arbeidsstatus-/oppfølgings-UI før bestilling. |
| V3 PUBLIC-detalj og filtrering | Endelig detaljdisponering, filtersett og eventuell API-filter-/versjonskontrakt er åpne | Gjenbruk godkjent forside og dagens fungerende liste/detalj som utgangspunkt; spesifiser synlige felter, filterkombinasjoner, retur og mobil/smal visning. Prosjekteier avgjør detaljvalg og CTO kontraktvalg før PUBLIC-V1-implementering. Ingen nye filtre utledes av datamodellen. |
| V4 Musikkontoret.no | Standalone/lenking/innbygging/API-forbruk og faktisk publiserings-/driftsgrense er ikke avgjort | Hold kjernen uavhengig av nettsideintegrasjonen mens grensesnittet avklares; eier/CTO fastsetter konkret løsning før integrasjonsbestilling og endelig PUBLIC-v1-aksept. Denne planen velger ingen integrasjon eller produksjonssetting. |
| V5 Administrasjon | Nye medlemskaps-/avtale-/globalforvaltningsskjermer i v1 er ikke gitt av roller/modeller alene | Bruk eksisterende sikrede admininnganger der tilstrekkelig; eier/CTO avgrenser nødvendige brukerreiser før UI-6-ADMIN-bestilling. Ikke-avtalte nye adminflater blir ikke implisitte v1-blockere. |
| V6 Eksportdetaljer | Roadmapens eksporttyper er grunnlag, ikke ferdig vedtatt felt-/segment-/nedlastingsdesign | Konkretiser de allerede beskrevne eksportreisene med privat/PUBLIC-kontaktkontrakt før fase-8-bestilling; ikke lov nye integrasjoner eller automatisk utsending. |

Dette er beslutningsbehov for senere leveranser, ikke blokkering av denne
publiseringen. Provider-, avtale-, retensjons- og datamigreringsporter følger
respektive ADR-er/5E; de godkjennes eller aktiveres ikke gjennom UI-planen.
