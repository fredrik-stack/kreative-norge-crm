# Feature: Public


## Ett bekreftet aktørbilde – stagingverifisert 2026-11-09

Foto kan zoomes ut til10 % med hvit bakgrunn, eller inn til300 %. Standard er100 %.
Etter preview, rettighetsbekreftelse og eventuell kreditering brukes én handling:
«Bekreft og bruk bildet». Separate PUBLIC-/standardbildeknapper fjernes. Bildet
klargjøres også for en upublisert aktør, men blir først offentlig når aktøren
selv er bekreftet for offentlig visning. Samme release følger senere publisering;
avpublisering sperrer bilde-URL-ene igjen. Ved teknisk feil kan bekreftelsen
fullføres eksplisitt uten nytt bildevalg eller automatisk retry.
[Kontrakt, tester og status](../architecture/SECURITY_AND_ROLES.md#samlet-bildebekreftelse-og-zoom-ut--2026-11-08).
PR #113 /efba875 og bare0040 er stagingverifisert med leseprober; nye positive
bildereiser er syntetisk testet lokalt/CI. Editor viser upubliserte bilder privat,
mens PUBLIC forblir sperret. Eldre v1-bildevalg omskrives ikke.

## Bilderedigering – avgrenset retting, stagingverifisert 2026-11-08

PUBLIC-handlingen ligger etter preview og intern rights approval. Editor bruker
samme autoritative bilde som PUBLIC ved aktiv cutover og oppdaterer kort/modal
straks; en intern approval uten release viser fortsatt fallback. Legacykandidater
består. Brave har synlige alternative queryer og opptil200 transient treff i
puljer på12; «Vis flere» sender ikke et nytt søk og skjulte treff previewhentes
ikke. Ingen automatisk publisering eller garanti for Facebook-/operatorresultater.
[Kontrakt, visuelt grunnlag og stagingstatus](../architecture/SECURITY_AND_ROLES.md#avgrenset-bilderetting--2026-11-08).
PR #111 / eksakt API/frontend `2a86bb4` er stagingverifisert uten bildewrites.
Alle 122 publiserte Editor-previews samsvarer med PUBLIC (4 asset /118 fallback);
syntetiske lokale E2E viser umiddelbar oppdatering og PUBLIC-handling nederst.


## Eksplisitt bildeflyt – stagingverifisert2026-11-08

Editor skiller internt godkjent bilde fra bildet som brukes offentlig. Etter
preview og eksplisitt rettighetsbekreftelse velger redaktøren separat «Ta bildet
i bruk på PUBLIC». Aktørprofilen må allerede være publisert. Preview fra PUBLIC
bruker samme projeksjon som kort, detalj og bilde-URL-er. Ingen gamle URL-er
konverteres automatisk. «Bruk standardbilde i stedet» bevarer bildehistorikken;
rettighets-/personvernkrav håndteres fortsatt med formell takedown.
[Server-, Brave- og driftskontrakt](../architecture/SECURITY_AND_ROLES.md#editor-bildepublisering-og-en-brave-konto--kodeleveranse-2026-11-08).
PR #109 er stagingverifisert med syntetisk aktør, erstatning/fallback og tre
serverte bildevarianter. Brave er aktivert bare for eierkontoen. Reelle aktørbilder
er ikke endret; eier kan ferdigstille dem med separat rettighets- og PUBLIC-valg.


## Helhetlig ferdigstilling – presisering 2026-10-24

[PUBLIC-V1 og samlet produktaksept](../status/EDITOR_PUBLIC_UI_COMPLETION_PLAN_2026-10-24.md)
samler liste/søk/filter og aktørdetalj med offentlig kontakt-/stedsvisning.
Konkretisering kan gå parallelt under fase 6; implementering krever nødvendige
6A–6C-kontrakter og kan gå parallelt med import. Begge Google Maps-aktørkart er
fortsatt v1-omfang i separat KART-V1, uten å blokkere kjerneimport. PUBLIC er ikke
ferdig bare fordi 7E/importen lukkes. Detaljdesign, filter-/API-valg og forholdet
til Musikkontoret.no er fortsatt åpne; ingen ny integrasjon eller administrasjons-
flate vedtas. Daterte bevis nedenfor er ikke en ny visuell helhetsgodkjenning.


**Status:** grunnløsning implementert; kontakt-, lenke- og tittelregel stabilisert i fase 2; 3E.3-bilde-/head-cutover er `CLOSED / ACTIVE` i staging

Public skal vise et kontrollert utvalg av publiserte aktørdata i et symmetrisk og skalerbart grensesnitt.

Dagens public API fungerer, og HTML-visningen brukes i staging. Public API og public HTML bruker samme kontaktregel: personer vises bare når `OrganizationPerson.status=ACTIVE` og `OrganizationPerson.publish_person=True`, og e-post/telefon vises bare fra `PersonContact` med `is_public=True`.

`Person.email` og `Person.phone` brukes ikke som offentlig fallback. PUBLIC HTML-kort lenker til kanoniske ID-baserte aktørsider, slik at publiserte aktører uten organisasjonsnummer fortsatt får fungerende detaljside.

På PUBLIC HTML beholdes telefonens rå skrivemåte som synlig tekst. Når kontakten
har lagret canonical E.164-identitet, bruker lenken dette som `tel:`-mål;
manglende canonical identitet gir ikke-klikkbar råtekst. Public API-shape og
publiseringsreglene er uendret.

Når en publisert kontaktperson har `Person.title`, vises tittelen både i public API og på PUBLIC HTML-kortet. Null eller tom tittel gir ikke en tom visningsrad eller et tomt API-felt.

Etter 3E.3-gaten bruker API, PUBLIC list/detail og delingsmetadata samme read-only bildeprojection i staging. Kort og hero bruker square, Open Graph/Twitter bruker share, og canonical kommer fra konfigurert site-origin. Manglende eller ikke-autorisert asset gir production fallback v1 med blank alttekst, aldri legacybilde. Kode-/eksempelstandarden `PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=False` bevarer sikker opt-in; den ignorerte stagingverdien er `True` etter dokumentert aktivering og rollbacktest.

Nye publiseringsvalg i Editor starter avslått. En telefon fra legacy-feltet kan repareres til en privat primær `PersonContact` gjennom en eksplisitt, dry-run-først-kommando, men blir aldri offentlig som bivirkning.

Editor viser nå den effektive kombinasjonen av `publish_person` og
`PersonContact.is_public` per aktørkobling. Dette er forklarende UX rundt dagens
mellommodell, ikke relasjonsspesifikk kontaktpublisering og ikke full ADR-005.

Staging-data ble rettet 2026-07-26 slik at eksisterende e-postkontakter er offentlige, unntatt at tre navngitte aktør-person-koblinger er interne via `publish_person=False`.

`ADR-005` har besluttet at personkontakt senere skal publiseres per aktør–person-kobling gjennom én felles offentlig projeksjon. Den langsiktige omleggingen er ikke implementert. Endelig visuelt design, filtrering, API-versjonering og integrasjon mot Musikkontoret.no er fortsatt uavklart.

[ADR-011](../decisions/ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md)
har i tillegg godkjent én framtidig PUBLIC-identitet og global publication state
per canonical Organization. Dette er ikke implementert: dagens aktører og tags
er fortsatt direkte tenant-eide. Målprojeksjonen skal returnere aktøren én gang,
bruke bare shared editorial tags og aldri eksponere assignments eller private
overlays. Offisiell `Organization.email` følger aktørens PUBLIC-state uten et
nytt `publish_email`-flagg; telefon beholder eget publiseringsvalg. Structured
places og actor-only maps følger nå den godkjente
[ADR-012](../decisions/ADR-012-PLACE_IDENTITY_GEOGRAPHIC_CLASSIFICATION_AND_ACTOR_ONLY_MAPS.md),
men er ikke implementert. PUBLIC-kartet gjelder bare Organizations med
eksplisitt offentlig OrganizationPlace, tilstrekkelig source-backed/system- eller
brukerbekreftet Place og gyldig godkjent koordinat. Autoriserte tenantbrukere kan
publisere relasjonen med riktig capability; plattform-superadmin er ikke et
kartkrav, og OrganizationPlace kopieres ikke per assignment. Tvetydige Places og
personer får aldri kartpunkter, Organizations uten koordinat forblir i listen,
og Google skal kunne være deaktivert uten at PUBLIC-listen eller aktørsidene
slutter å fungere. Google krever i tillegg en separat, juridisk godkjent Customer
Application-vilkårsgate med gjeldende End User Additional Terms- og
Privacy-lenker.
