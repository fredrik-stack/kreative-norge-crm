# UI-6-FELLES – felles utforming av eksisterende Editor-flater

**Dato:** 2026-10-24. **Status:** Kodeforankret anbefaling til senere implementering; publisering er ikke ny designgodkjenning eller ferdigstilt UI.
**Baseline:** `00ac0d9fcc78656ca1144baf893beb65e003c8d1` etter PR #87.

## 1. Mandat, bevis og avgrensning

Eierbestillingen autoriserer konkretisering, lagring, én dokumentasjons-PR,
faktisk separat skrivebeskyttet review, retting, ordinær merge og grønn main-CI.
Ingen applikasjonskode, data, migrasjon, flagg, provider, UI-implementering,
prototype, browser-/stagingkjøring eller deploy endres/utføres her.

**Videreført godkjent retning (G):** [samlet ferdigstillingsplan U1–U6/U16](../status/EDITOR_PUBLIC_UI_COMPLETION_PLAN_2026-10-24.md),
[roadmapens godkjente forsider](../status/ROADMAP.md#fase-1--verifiser-staging--og-frontend-baseline),
[Editor](../architecture/EDITOR.md), [PUBLIC](../architecture/PUBLIC.md),
[ADR-005](../decisions/ADR-005-CONTACT_ARCHITECTURE.md),
[ADR-011](../decisions/ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md) og
[ADR-012](../decisions/ADR-012-PLACE_IDENTITY_GEOGRAPHIC_CLASSIFICATION_AND_ACTOR_ONLY_MAPS.md).

[Frontendbaselinen 2026-07-29](../status/FRONTEND_BASELINE_2026-07-29.md) og
[fase-4-eiergodkjenningen 2026-08-29](../status/PHASE_4_OWNER_APPROVAL_2026-08-29.md)
er historiske, avgrensede bevis; de er ikke ferske observasjoner av disse
forslagene. **N** nedenfor betyr ny anbefaling, **Å** et senere beslutningsbehov.
**K** betyr faktisk kontrollert kode, uten ny runtime-/visuell verifikasjon.
Alle anbefalte mål i §§3–6 krever senere avgrenset implementeringsbestilling.

6A → 6B → 6C → Import 2.0 består. Godkjent import-UX v6 rev.4/O-24 og 5E
endres ikke; ingen full mobilimport eller ny brukertestrunde. Begge Google
Maps-aktørkart er fortsatt v1 i KART-V1, uten å blokkere kjerneimporten.

## 2. Eksisterende komponenter og avgrenset gjenbruk

| Kilde / K i dagens kode | Gjenbruk / N-tilpasning / konkret mangel | U-rad og leveranse |
| --- | --- | --- |
| [App.tsx](../../frontend/src/App.tsx): shell/hero, tenantvelger, top-nav, søk/filter og session | Behold ruter, autentisering, komponentstruktur og eksisterende meny. N: kompakter kontekstområdet og gjør profilens retur/aktiv seksjon tydelig; ikke ny global sidebar | U1–U3 / UI-6-NAV, OVERSIKT, PROFIL |
| [styles.css](../../frontend/src/styles.css): panel, grid.two, actions, save-pill, kort, tabell, modal og responsive regler | Gjenbruk klasser/tokens. N: små seksjonsspesifikke tillegg for handlinger, min-width:0, omslag og avstand; ingen generell CSS-opprydding/nytt designsystem | U1–U6 / UI-6-FELLES |
| [Field](../../frontend/src/components/Field.tsx): omsluttende label, required og feltfeil | Gjenbruk enkle felt. N ved berørt felt: unik control-id, feilmeldings-id og aria-describedby/aria-invalid; flere kontroller i samme feltgruppe trenger egne navn/fieldset, ikke én label som navngir både telefon og region | U3/U4/U6 / PROFIL, 6B, 6C; ikke del av første pakke |
| [OrganizationsPage](../../frontend/src/pages/OrganizationsPage.tsx), [PeoplePage](../../frontend/src/pages/PeoplePage.tsx): oversikt, read-only detaljmodal og egne redigerings-/new-ruter | Behold kort versus persontabell og modal→Rediger-reisen. N: konkret gruppering/retur etter §4; ingen ny generell profilmodus/rute | U2/U3 / OVERSIKT, PROFIL |
| Samme sider: hovedformens actions ligger nederst, save-pill i header; kontakters separate writes ligger også inne i personformens DOM | N: skjemabundet handling/status med uttrykkelig scope. Mangler én sann, nær forklaring av profilsubmit versus separate writes; DOM-nesting betyr ikke felles lagring | U3/U4 / første pakke §8; senere 6B |
| [useEditorData](../../frontend/src/hooks/useEditorData.ts): drafts, submit/CRUD, reset, dirty og saveAllPendingChanges | Behold eksisterende API-/writekontrakter. Ingen generell autosave/undo/atomisk lagring legges til. §5 er kontraktgrunnlag | U1–U6 / 6A, 6B, PROFIL |
| [useUnsavedChangesGuard](../../frontend/src/hooks/useUnsavedChangesGuard.ts), [ConfirmNavigationModal](../../frontend/src/components/ConfirmNavigationModal.tsx), [useRouteSyncedSelection](../../frontend/src/hooks/useRouteSyncedSelection.ts) | Gjenbruk eksisterende blokkering/rutesynk. N: riktig scopeforklaring/fokus. Dekningshull nevnt i §5 må få egen kontroll før bred NAV-ferdigmelding | U1/U3 / NAV, PROFIL |
| [PhoneLink](../../frontend/src/components/PhoneLink.tsx), [PhoneRegionSelect](../../frontend/src/components/PhoneRegionSelect.tsx), editorPublication/editorTaxonomy | Gjenbruk raw/canonical-telefon, region og eksisterende effektiv offentlig status/taksonomi; ikke endre publiseringsregler | U2–U4 / OVERSIKT, 6B |
| OrganizationImagePanel og OrganizationPreviewPanel i OrganizationsPage | Behold egne bilde-/previewhandlinger og deres busy/error/revision. Ikke legg dem under profilknappens «lagret» | U3/U4 / PROFIL, senere 6A-image-home/6B-preview |
| [PUBLIC-listetemplate](../../crm/templates/crm/public_actor_list.html), [detaljtemplate](../../crm/templates/crm/public_actor_detail.html) | Del prinsipper for hierarki, taksonomifarger, bilde/tekst og tomtilstand. Behold PUBLICs varme palett og Django-rendering; ingen React-overgang/felles komponentbibliotek | U13/U14 / PUBLIC-V1; V3/V4 fortsatt åpne |

## 3. Anbefalte utformingsregler (N innen G)

| Område | Konkret anbefaling til implementering |
| --- | --- |
| Kontekst/navigasjon | Behold Aktører, Personer og rollebegrenset Import/eksport. Merk aktiv hovedseksjon også på detaljrute, ikke bare eksakt oversikts-URL. Synlig «Aktivt Musikkontor», navn og gjeldende rolle; endring går gjennom eksisterende navigasjonsvern. Ikke kall dette ny shared-autorisasjon. Profilheader: «Til aktøroversikt»/«Til personoversikt», type + navn, gjeldende modus og separat offentlig status |
| Bredde | Behold full bredde på oversikter, shell-padding som eksisterende clamp(.9rem,1.5vw,1.25rem). N: profilarbeidsflate max-width:1440px, sentrert; aktør main minmax(0,1fr) + preview 320px, gap16px. Ved <=1200px flyttes preview etter hovedinnholdet. Personprofil har én hovedkolonne, max-width:1040px; ingen tom bildekolonne |
| Felt/grupper | Seksjonsavstand24px, intern gap12px, panelpadding16px, labels 6px over kontroll. To kolonner for korte felt, full rad for notat/beskrivelse/URL og sammensatte kontakter. Ved <=860px én feltkolonne. Kontroll/handling min-height44px; textarea min-height100px og vertikal resize. Ingen global endring av alle importfelt |
| Hierarki/farge | Behold IBM Plex Sans/Space Grotesk/fallbacks fra Editor; profilnavn h2 ca1.25rem, seksjon h3 1.1rem, label .85rem/600, støttetekst .85rem, brødtekst1rem. Behold Editor --ink/--muted/--accent/--danger og eksisterende paneluttrykk. Kategori #6B493D, underkategori #38A8EC, redaksjonell tag #4A8755 videreføres; lime #C8FA00 gjelder bare framtidig eksplisitt intern-tag-kontrakt. Dagens legacytags omklassifiseres ikke |
| Aktørkort | Behold auto-fill minmax(290px,1fr), men bruk min(290px,100%) som nedre grense så 320–390px skjerm ikke sprenges. Kvadratisk84px-bilde, navn opptil to linjer, kategori/underkategori/tags i wrap, kommune/sted og lenke. Telefon forblir utenfor hovedkortet etter fase-4-godkjenningen. Status «Offentlig»/«Intern» er tekst, ikke ny privatklassifisering. Fullt navn/metadata tilgjengelig i modal; skjulte ekstra chips får navngitt «+N»/detaljtilgang |
| Persontabell | Behold ni kolonner: navn, tittel, aktører, primærlenke, e-post, telefon, kommune, kategori, tags. Navn/aktører kan bryte linjer; lenketekst kan forkortes visuelt med fullt tilgjengelig mål. Behold min-width960px og avgrenset horisontal rulling på smal skjerm; gi rulleområdet navn/tastaturtilgang. Ikke fjern kontaktfelt eller lag mobilkort som nytt prosjekt. Kort/lesemodal gir fortsatt samlet lesbar visning |
| Søk/filter | Synlig label «Søk aktører»/«Søk personer», ikke bare placeholder. Behold eksisterende søkefelt, kategori→underkategori og taggforslag; valgt tilstand i oppsummering. Antall = faktisk filtrert, innlastet utvalg; ikke påstå backendtotal/paginering som ikke finnes. «Nullstill filtre» tømmer søk/kategori/underkategori/tagg, ikke aktivt Musikkontor eller profilutkast |
| Handlinger | Én hovedhandling per form: Opprett aktør/person eller Lagre aktør/person. Sekundær: Forkast profilutkast for eksisterende profil; ved ny profil «Nullstill profilfelt» med synlig beskjed om at taggtekst beholdes av dagens reset. Retur er navigasjon, ikke lagring. Slett/fjern ligger separat i relevant lagringsområde, med eksisterende bekreftelse/slettevern; ikke samme visuelle vekt som Lagre. Nytt/Rediger vises bare når gjeldende tillatelse støtter det |
| Lagre/status | Skjemabundet rad nederst i hovedformen, sticky bottom:0 mens den formen er i visningsområdet, egen ugjennomsiktig panelbakgrunn, top-border, padding12px, z-index under dialoger. Knappene på høyre side, scope/status til venstre, gap8–12px; wrap ved smal bredde. Ingen global fixed-lagrelinje som ser ut til å styre bilde/kontakter/koblinger. En liten toppstatus kan speile samme scope, ikke gi et annet lagringsløfte |

Dette er anbefalte verdier, ikke målte kvalitetsfunn. Kontroller særlig om sticky
faktisk følger riktig scrollcontainer, ikke dekker fokus/feil, og avsluttes før
andre lagringsområder. På <=800px skal rad og tekst bryte naturlig; ingen
horisontal sidescroll. Relevant skjerm-/zoom-/tastaturkontroll kreves før levering.
PUBLIC kan gjenbruke avstand, omslag, tydelige handlinger og taksonomihierarki;
Editorens grønne app-handling erstatter ikke automatisk PUBLICs palett.

## 4. Fire representative skjermdisposisjoner (N)

### S1 Aktøroversikt

1. Shell: produkt/nav og aktivt Musikkontor/rolle/session; ingen duplisert sidevelger.
2. Overskrift «Aktører», antall filtrerte treff, hovedhandling «Ny aktør» hvis tillatt.
3. Søk og dagens tre filtertyper; oppsummering + Nullstill filtre under dem.
4. Kortgrid etter §3: bilde/navn → taksonomi → kommune/sted/primærlenke → offentlig status. Ikke notattekst eller privat arbeidsstatus på offentliglignende kort uten riktig scope.
5. Kort/navnehandling åpner read-only modal: navn/bilde/status → beskrivelse → intern kontakt/sted/taksonomi → tilknyttede personer/lenker; Lukk og tillatt Rediger. Modal er intern, ikke PUBLIC-preview. Aktørens eksisterende openOrg-query brukes; ikke ny modalrute.
6. Rediger går til /organizations/:id, Ny til /organizations/new. Retur til oversikt beholder tilgjengelig klientfilter og gjenfinner åpneren; hjemlenken er fortsatt en egen, bevisst filterreset. Ingen garanti om filterpersistens etter reload uten egen bestilling.

Lange navn brytes; kommune/tags utvider innholdet uten å skyve handlinger ut.
Under800px én filterkolonne og kort etter tilgjengelig bredde; modal maks
viewport minus24px, intern rulling og synlige Lukk/Rediger. Typed steder venter
på6C; private søk/kortmetadata på6A/V1–V2 i hovedplanen.

### S2 Personoversikt

1. Samme shell, «Personer»/antall, tillatt «Ny person» og samme filterplassering.
2. Tabell med de ni eksisterende kolonnene etter §3, tydelig navneknapp for lesing og eksplisitte aktørlenker. Tom tittel/kontakt vises som «—», ikke som valideringsfeil.
3. Navn åpner read-only modal: navn/tittel → interne kontaktkanaler → tilknyttede aktører → notat/taksonomi/sted/lenker. Gjeldende legacy-note er intern; framtidig privat felt avhenger av6A. Modalens Rediger går til /people/:id, Ny til /people/new.
4. Lukk returnerer fokus til navneknappen; personmodalen har i dag lokal state, ingen ny URL-persistens loves. Aktørlenke kan bruke eksisterende /organizations?openOrg=:id.

På smalere skjerm ruller bare tabellområdet horisontalt; heading, filtre og
primærhandling blir igjen lesbare. Ingen kolonner fjernes uten annen tilgang.
Framtidige relasjonstitler/kanalvalg kommer i6B, structured sted i6C.

### S3 Aktørprofil – lesing, oppretting og redigering

Lesing skjer i S1-modalen, som i dag. Egen side er arbeidsflate for tillatt
oppretting/redigering, ikke en ny read-only rute med nye rettigheter.

| Rekkefølge på egen side | Innhold / handling / scope |
| --- | --- |
| Header | Til aktøroversikt; Ny aktør eller navn, type, offentlig status og tydelig skjemastatus |
| 1 Profilgrunnlag | Navn/orgnr., offisiell e-post/telefon med region, dagens kommune. Navn på full rad, korte felter i par. Ingen automatisk assignment/place-create |
| 2 Innhold og kategorisering | Beskrivelse, kategori/underkategori og legacytags; deretter internt notat tydelig navngitt. Description er ikke privat notat. Skill framtidig felles core og kun eget Musikkontors overlay når6A-overgangen er levert |
| 3 Lenker og publikasjon | Nett-/sosiallenker, aktørpublisering og eget telefonvalg. Tilstand beskrives fra dagens kontrakt; framtidig global canonical effekt krever6A |
| 4 Hovedformens handlingsrad | Opprett/Lagre aktør, Forkast profilutkast og status etter §5/§6. Omfatter ikke følgende områder |
| 5 Aktørbilde | Eksisterende kilde→preview→processing→eksplisitt godkjenning; egne feil/busy/revision. Ikke erstatt godkjent bilde ved profilsubmit |
| 6 Personkoblinger | Eksisterende ny-kontaktperson-/knytt-eksisterende-former og separate koblingswrites. Senere samlet atomisk kontakt-/relasjonsreise i6B |
| Sideområde / etter hovedkolonnen <=1200px | Eksisterende preview blander utkastfelt (blant annet navn, beskrivelse, kontakt og taksonomi) med lagret bilde/OG-metadata og API-hentede personer. Behold separat Oppdater preview, som oppdaterer metadata. Merk kildene; dette er ikke en samlet, autoritativ PUBLIC-projeksjon eller ferdig 6B-resolver |

Ny aktør må opprettes før ID-avhengige bilde/koblingshandlinger. Retur mens
hovedutkastet er skittent går gjennom vernet; reset omfatter bare hovedutkastet, med nyprofil-unntaket for taggtekst i §5.
Lange navn har naturlig omslag, URL-er/beskrivelse/notat full feltbredde; ved
<=860px felt i én kolonne. Framtidige OrganizationPlace-plassvalg under grunnlag
og privat overlay under «Kun eget Musikkontor» krever respektive6C/6A.

### S4 Personprofil – lesing, oppretting og redigering

Lesing er S2-modalen; oppretting/redigering er /people/new eller /people/:id.

| Rekkefølge på egen side | Innhold / handling / scope |
| --- | --- |
| Header | Til personoversikt, Ny person/navn og profilskjemastatus |
| 1 Profilgrunnlag | Navn, dagens globale tittel, primære kompatibilitetsfelt e-post/telefon+region og kommune. Ikke presenter dagens globale tittel som relasjonstittel |
| 2 Kontaktkanaler | Eksisterende kanaler med eget «lagres ved endring»-område, feltfeil og separate primær/offentlig-valg; ny kontakt har separat Opprett kontakt. Krever person-ID. Området er separat selv om DOM er inne i hovedformen |
| 3 Kategorisering, notat og lenker | Dagens profilfelter. Framtidige tenantprivate data venter på6A, typed PersonPlace på6C; ingen personkart |
| 4 Hovedformens handlingsrad | Opprett/Lagre person og Forkast profilutkast, med uttrykkelig unntak for kontaktområdet |
| 5 Aktørrelasjoner / offentlig forklaring | Vis eksisterende tillatte koblinger/lenker og effektiv synlighet. Senere6B gir roller/titler og kanalvalg per aktør med felles preview. Ikke oppfinn nye inline-writes i dagens personflate |

På ny person er kontaktområdet forklarende deaktivert til personen har ID;
primære profilkontaktfelt kan fylles før Opprett person. Under860px én kolonne,
lange kontakter/navn omslås og handlinger wrap. En leser kan fortsatt lese modal;
ny redigeringsrute/tilgang for leser bestilles ikke.6B erstatter senere den todelte
kontaktpresentasjonen med én funksjon; det er et eget backend-/migreringsscope.

## 5. Lagringskontrakt – K nå og mål senere

Følgende navn kan søkes i useEditorData/sidekomponentene. En frontendhandler er
ikke en transaksjonsgaranti på tvers av API-kall.

| Skjema/område | Utløser og faktisk K-write | Hva lagrestatus/forkasting kan bety |
| --- | --- | --- |
| Aktørens hovedutkast | onChange endrer draft; onSubmit→submitOrganizationDraft lager tags først ved behov, deretter createOrganization/patchOrganization og reload/tagghenting. Inkluderer profilfelter, taksonomikoblinger, legacy note, publiseringsvalg | saveState=saved etter hele frontendsekvensen, ikke etter bare første200. For eksisterende profil setter reset utkast/taggtekst fra sist innlastet valgt profil og state=idle. For ny profil nullstilles draft/feltfeil, men taggtekst og SaveState beholdes; taggtekst kan fortsatt gi dirty. Ingen rollback av tags eller andre allerede fullførte kall. Feil kan komme etter persistens |
| Personens hovedutkast | onChange endrer personDraft; onSubmitPerson→submitPersonDraft oppretter/patcher profil etter taggresolusjon og henter kontakter/tags. Primærkontaktkompatibilitet kan berøres av backend | personSaveState/personLastSavedAt gjelder hovedsubmit, ikke alle kontakt-/koblingshandlinger. For eksisterende profil tilbakestilles personutkast/taggtekst og state=idle; for ny profil nullstilles draft/feltfeil, men taggtekst og SaveState beholdes. Ingen av grenene nullstiller nykontaktutkast eller lagrede kanaler |
| Ny kontaktkanal | Knappen «Legg til kontakt» er type=button og kaller createContactFromDraft etter ID; separat POST. Ved primær oppdateres lokale kompatibilitetsfelt/baseline. Hovedknappen Lagre person kaller ikke dette | Må opprettes separat; ingen eksisterende egen SaveState for hver kanal. Global error/field errors og retur fra POST er dagens respons. Slett/angre via profilreset finnes ikke |
| Eksisterende kontaktverdi | Ukontrollert input/defaultValue; onBlur sender PATCH bare når trimmet verdi er ikke-tom og forskjellig. Telefonnummer sender valgt region; regionselect endrer alene bare lokal kontekst | Tom input på blur sletter ikke kontakt og inngår ikke som vanlig personDraft-dirty. Ikke vis «profilutkast lagret» som bekreftelse på en slik redigering |
| Eksisterende kontaktvalg/sletting | is_primary/is_public onChange→updateContact PATCH; Slett→bekreftelse→removeContact DELETE | Umiddelbare, separate writes. Tilbakestilling/forlat uten å lagre kan ikke angre dem. Kanalens globale is_public er dagens mellommodell, ikke6B-valg per kobling |
| Eksisterende personkobling | Status/publish_person onChange→updateLink PATCH. Fjern→bekreftelse→removeLink DELETE | Lagres separat med global feilvisning, uten egen rad-SaveState; ikke del av aktørsubmit/reset |
| Knytt eksisterende person | onCreateLink med egen submit→POST relasjon→reload | Eget kall/resultat; valg før submit er lokalt. Ingen profilsubmit eller automatisk publisering utover uttrykkelige lagrede valg |
| Opprett og knytt ny kontaktperson | onCreateLinkedPerson: POST person, hent/opprett/patch kontakter, POST kobling og reload; linkedPersonSaveState | Flere kall, ingen samlet klient-/API-transaksjon. Delvis resultat kan bestå ved feil; ikke blindt gjenta create eller love «ingenting lagret».6B-målet om atomisk person/kontakt/kobling/publisering er ikke levert |
| Bilde og preview-refresh | Egen processing/godkjenning med expected_revision og egen busy/error. onRefreshOrganizationPreview har separat serverkall/previewRefreshState og oppdaterer lagret metadata | Profilreset/navigasjonsforkasting opphever ikke godkjent bilde, behandlet grunnlag eller fullført preview-refresh. Ikke generell autosave eller samlet publiseringsknapp |
| Lagre og fortsett i navigasjonsdialog | saveAllPendingChanges prøver aktørutkast, personutkast, ny kontakt i rekkefølge og stopper ved false | Flere kall; første kan være lagret selv om senere feiler. Ved feil bli igjen. Forkast kaller reset av profil-/kontakt-/linked-personutkast; profilreset har nyprofil-unntaket for taggtekst ovenfor. Allerede lagrede writes blir stående |

**K-dekning av dirty/vern:** organizationHasUnsavedChanges omfatter hovedutkast/
taggtekst. peopleHasUnsavedChanges omfatter personutkast/taggtekst og ny kontakt
(type/verdi/primær/offentlig); personDraftHasUnsavedChanges omfatter bare profilen.
Eksisterende kontaktinputs/region alene, koblingsvalg og linkedPersonDraft er ikke
omfattet på samme måte; sistnevnte inngår ikke i hasUnsavedChanges/saveAllPendingChanges.
App bruker route-/tenantvern, beforeunload brukes ved registrert dirty, mens Logg
ut kaller onLogout direkte. Dette er kodeavgrensninger, ikke ferskt reproduserte
UI-feil. Bred NAV-ferdigmelding må kontrollere dem særskilt; første pakke lover
ikke full arbeidsflate-autosave eller heldekkende forkasting.

**N nå:** bruk scope-navngitt status for hovedformen, tekst ved kontakt/koblings-
området «Disse endringene lagres separat», og forkast-tekst som ikke lover undo.
Ny radvis busy/lagret/feil krever faktisk egen request-state før den vises; dagens
saveState kan ikke gjenbrukes som bevis. Ikke utvid første pakke til dette.
**G senere6B:** én kontaktopplevelse og reell atomisk skrivekontrakt før UI kan
love én samlet lagring; inkluder migrering/legacyinnganger og PUBLIC-resolver.
**6A:** revisions-/capability-/auditkontrakt og separat privat autoritetsovergang
før shared/overlay-UI. **6C:** typed stedstjeneste før typed stedslagring.

## 6. Tilstander, handlinger og tilgjengelighet (N)

| Situasjon | Presentasjon / handling / scope |
| --- | --- |
| Laster | Behold shell/kontekst, vis «Henter aktør/person…» i berørt område, aria-busy på området. Ikke vis «0 treff» eller Ny som om data var ferdig hentet |
| Tomt arbeidsutvalg / søk uten treff | Skill ingen profiler i innlastet scope fra filtrert0. Tillatt Ny ved tomt scope; «Ingen treff – endre/nullstill filtre» ved søk. Feil ved lasting er ikke tomtilstand |
| Manglende verdi / ugyldig felt | Read-only «Ikke oppgitt»/«—»; krev bare backendens faktiske felter. Synlig label og lokal feiltekst knyttes til input; ved submitfeil fokus på første ugyldige felt/oppsummering, ikke på et annet skjema |
| Ulagret profil | «Ulagrede profilfelt» fra riktig dirty, ikke fra generell SaveState alene. Nytt tomt objekt: «Ikke opprettet». Ingen lagret-timestamp fremstilles som bekreftelse på nyere utkast |
| Lagrer | «Lagrer aktørskjema…»/«Lagrer personskjema…», disable duplikat-submit/utkastforkasting i området; behold tekst/status utover farge. Ikke global arbeidsflate-spinner |
| Lagret | «Aktørskjema lagret»/«Personskjema lagret», tidspunkt for sist vellykket hovedsubmit når tilgjengelig. Dirty overstyrer gammel saved etter nye endringer. Kontakt-/bilde-/koblingsscope bekreftes ikke av teksten |
| Feil / ukjent utfall | «Lagring ikke bekreftet» + eksisterende konkret feil/feltpekere. Ingen påstand om at alle writes rullet tilbake. Ved mulig persistens/reloadfeil kontroller lagret resultat før ny create; ikke automatisk/blind retry |
| Konflikt | Bruk faktisk konfliktkode/revisjon der backend har den, blant annet bildeapproval. Vis behov for ny kontroll/lasting, ikke automatisk overskriving. Vanlige profilskjema har ikke generell stale-/mergekontrakt i dag; ikke lov versjonsgjenoppretting/undo |
| Manglende tilgang / deaktivert funksjon | Forklar ingen tilgang eller funksjon ikke aktiv uten å vise privat data. Behold gjeldende serververn og safe read-only alternativer. Ikke vis ny overlay-/Place-/kartkontroll som operativ før porten er oppfylt |
| Retur / avbryt / Musikkontor | Ren retur går til riktig oversikt. Registrert dirty bruker Bli her / Lagre og fortsett / Forkast utkast og fortsett; forklar separate writes. Save-and-continue kan være delvis lagret og fortsetter ikke ved false. Endring av Musikkontor forkaster ikke allerede lagret data; behold gjeldende scope-reset |

Tab følger DOM-/leserekkefølge; Enter submitter riktig form, type=button for
andre handlinger. Statusregion role=status/aria-live=polite kunngjør request-
resultat uten fokusflytting per tastetrykk; feil får programmatisk feltkobling.
Modaldialog skal få forståelig navn, fokus ved åpning, Tab/Shift+Tab kun på
aktiverte kontroller i DOM-rekkefølge, Escape=Bli her/Lukk der trygt, og retur til
åpner ved lukking. Dagens navigasjonsvern har egne refs/Tab-håndtering; fullt
fokus-/disabled-/busy-samsvar er kontrollpunkt, ikke allerede bevist kvalitet.

Navn, URL og kontakttekst: min-width:0/overflow-wrap:anywhere på tekstområder,
behold normal linjebryting og tilgjengelig full verdi. Begrens visuell
korttekst, ikke selve dataverdien. Dialog max-height:calc(100dvh - 24px) og intern
rulling; sidekontekst/knapper må være tilgjengelige ved tastatur/zoom. Sticky
handling må ikke dekke siste felt/feilmelding; reserver radens faktiske høyde
og bruk passende scroll-margin på fokusmål. Ikke legg tabell-/modal-/formscroll
oppå hverandre uten å verifisere hvilken flate som ruller.

## 7. Beslutninger og leveransegrenser

| Klasse | Hva / anbefaling / tidspunkt |
| --- | --- |
| G – videreføres | Forsidenes uttrykk, legacy telefon/bilde/publiseringskontrakter,6A→6B→6C, importv6/O-24/5E, begge aktørkart iv1. U16 gjelder eksisterende/uttrykkelig avtalte admininnganger |
| N – publiseres for senere bestilling | §§3–6: konkrete mål, tetthet, fire disposisjoner og scoped sticky handling. Anbefal første pakke §8; ingen vesentlig ny navigasjonsmodell eller felles bibliotek |
| Å –6A/V1–V2 | Notatflytting, samlet reader/writer/søk-autoritet, private tags og øvrig tilgang. Ingen taggpolicy velges, ingen NULL/tom-fallback. Visuell privatmerking må følge reell tenantautoritet, ikke bare et grønt kort |
| Å –6B | Kontakt-/tittelmapping, atomisk lagring, relasjonsspesifikk publication og felles preview før samlet kontakt-UI. Dagens OrganizationPerson.status er relasjonsstatus, ikke privat arbeidsstatus |
| Å –6C | Typed Places/endring av eget objekts stedskobling kontra global rettelse etter ADR-012, før ny stedskontroll aktiveres |
| Å – V3/V4/V5 | Endelig PUBLIC-detalj/filter og Musikkontoret.no-integrasjon samt eventuelle nye adminskjermer avgrenses før sine bestillinger; ingen valg tas her |

Ingen datamodell-/API-/migreringsendring er nødvendig for første
presentasjonspakke. Felles komponentprinsipper gir ikke nye brukerrettigheter.
Øvrige skjermer har egne backend-/dataporter; senere visuell aksept må være
bundet til faktisk versjon og scope. Fersk browserkontroll før implementering
må spesielt se footerens scrollcontainer/fokusdekning, personkontaktblur ved
klikk på lagre, modalfokus/retur og hva aktuell backend faktisk har lagret.

## 8. Anbefalt første implementeringsbestilling – skjemabundet handling/status

**Anbefaling, ikke startet/godkjent som kodeleveranse:** lever én liten pakke for
aktør-/personhovedskjemaets lagre-/forkast-/statuspresentasjon. Behovet er
kodepåvist: hovedhandlinger nederst i lange former, generisk Lagret i header,
og blandede writes i samme arbeidsflate. En kompakt shell-ombygging ville berøre
alle ruter og løser ikke lagringsuklarheten; en global lagrelinje ville overdrive
scope. Derfor velges en lokal handlingsrad før NAV-/kort-/tabellombygging.

**Ferdig formulert bestilling til senere bruk:**

> Implementer skjemabundet handlingsrad i OrganizationEditorPanel og PeopleEditorPanel etter denne spesifikasjonen §§3,5–6/8. Behold eksisterende hovedformsubmit/reset/API-/tagg-/publiserings-/telefonkontrakter. Flytt eksisterende hovedactions til en scope-avgrenset sticky rad, uten dupliserte submitknapper eller ny global handler. Bruk «Lagre aktør»/«Lagre person» og eksisterende Opprett-varianter, «Forkast profilutkast» for eksisterende profil og «Nullstill profilfelt» for ny profil, profilspesifikk status/tid og kort forklaring om separate writes. Personstatus bygger på personDraftHasUnsavedChanges, ikke hele peopleHasUnsavedChanges; ny kontakt er separat. Gjenbruk lagringsstates, men la pågående request ha prioritet, deretter nye dirty felt fremfor gammel saved; idle alene betyr ikke lagret. Bevar dagens resetgren for ny profil og forklar synlig at taggtekst beholdes; ikke lov at hele nyutkastet forkastes. Ingen generell autosave/undo/atomisk lagring, ingen API-/hook-/rolle-/navigasjons-/kontakt-/bilde-/PUBLIC-/importendring. Før kodeendring: browser-aktiv Codex og relevant visuell baseline mot ekte backend. Test og lever gjennom separat review/ordinær merge/CI og relevant bestilt staging-/eierkontroll. Stopp etter denne pakken; den ferdigstiller ikke hele UI-6-PROFIL eller andre UI-6-leveranser.

- **Filer:** `frontend/src/pages/OrganizationsPage.tsx`, `PeoplePage.tsx`, scoped tillegg i `styles.css`; målrettede tester i eksisterende frontend-teststruktur. Ingen omfattende uttrekk eller ny generell komponentmotor.
- **Detaljregel:** raden er del av riktig hovedform. Profilsubmit skaper ikke ny kontaktkanal eller kobling; ved personkontaktområdet og aktørens senere separate områder vises scopeforklaring. Ny kontakt som ikke er opprettet kan fortsatt utløse dagens navigasjonsvern selv om profilfeltene nettopp er lagret. Ikke skjul dette med «alt lagret».
- **Aksept:** samme payloads/kall og uendrede onBlur-/onChange-writes; nøyaktig én hovedsubmit per form; korrekt navn/mode/status ved ny/eksisterende, dirty/saving/saved/error; ingen gammel Lagret over nye profilendringer; ingen generell retry ved ukjent create-resultat. Retur/reset/guards fungerer som før, med presis tekst om hva forkasting betyr, særlig beholdt taggtekst/dirty ved nyprofil-reset. Målrettet endring av resetfunksjonen krever separat valg, ikke skjult hook-retting i denne pakken. Sticky slutter ved hovedformens grense og dekker ikke felt/feil, bilde- eller koblingshandlinger.
- **Tester:** gjenbruk [App.test.tsx](../../frontend/src/App.test.tsx), [navigasjonsverntest](../../frontend/src/hooks/useUnsavedChangesGuard.test.tsx) og [dialogtest](../../frontend/src/components/ConfirmNavigationModal.test.tsx). Legg bare til målrettet scope/status-test for hovedformene, særlig personkontaktutkast versus profil-dirty, gammel saved etter ny endring, og ny aktør/person med taggtekst → reset → taggtekst/dirty fortsatt synlig med riktig knapp/forklaring. Bevar [bildeprøvene](../../frontend/src/pages/OrganizationsPage.image.test.tsx), telefon/publication-kontrakter og relevante eksisterende Playwright-reiser for CRUD/preview/ulagret navigasjon. Ikke gjør brede backend-/DB-testrunder til ny gate for denne presentasjonsendringen.
- **Senere browser/staging:** faktisk lang aktør-/personform på1440×900,1366×768,1024×768 og smal Editor390×844, tastatur og200%zoom; kontrollér save-area/fokus/siste feil, isolert kontaktwrite/nykontaktutkast, feil og retur med ekte backend. Smal Editor-kontroll bestiller ikke mobilimport. Visuell eiergodkjenning gjelder faktisk endret scope etter teknisk bevis; ingen ny formell brukertest/prototype-/kollegarunde.
- **Avhengigheter/valg:** ingen6A–6C-aktivering trengs når kontraktene beholdes. Prosjekteier må separat bestille pakken; nye vesentlige valg eller målt blocker eskaleres da. Radvis kontaktstate, dekkende navigasjonsvern og full6B atomisk kontaktreise ligger utenfor.
- **Tilbakeføring:** revert de avgrensede frontend-/CSS-endringene og bygg/deploy forrige verifiserte frontend etter relevant mandat. Ingen schema/datareversering; allerede lagrede separate writes står fortsatt.
- **Bidrag:** konkret del av U3/UI-6-PROFIL og tydelig grense mot U4; ikke fullført UI-6-NAV/OVERSIKT/PROFIL/PRIVAT,6B eller samlet Editor-v1.
