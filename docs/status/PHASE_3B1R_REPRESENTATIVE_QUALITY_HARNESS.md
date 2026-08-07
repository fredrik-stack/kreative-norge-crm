# Fase 3B.1R-A – representativ kvalitets-harness

**Status:** Isolert analyse-, datasett- og reviewramme. Ingen representativ kjøring eller endelig kvalitetsbeslutning.

**Dato:** 2026-08-06

## Formål

Fase 3B.1R-A gjør den eksisterende fase 3B.1-prototypen klar for en senere, lokal evaluering av rettighetsavklarte representative bilder. Leveransen avgjør ikke produksjonsterskler og kobles ikke til CRM-runtime.

PR #23 og fase 3C.6 er merget. Ordinær selection-livssyklus er dermed komplett bak avslått feature, men det finnes fortsatt ingen bildebehandling, storage-I/O, API-, Editor- eller PUBLIC-flyt.

## Implementert harness

- lokal `representative/private_dataset/` er Git-ignorert; repoet inneholder bare README, JSON Schema og anonymt eksempelmanifest
- manifestet krever anonym fixture-ID, relativ fil under `files/`, kategori, `contain`/`cover`, relevante varianter, rettighetsgrunnlag, redistribusjonsvalg, personindikator, forventet fargeprofil, reviewtemaer og korte ikke-identifiserende notater; en forventet kontrollert feil må i tillegg angi en eksakt, ikke-tom feilkode
- dupliserte IDs/filer, manglende filer, ukjente verdier, feil typer, absolutte paths, traversal og symlink-utgang avvises
- runneren krever eksplisitt dataset-root og tom, separat output-root, bruker ikke nettverk, skriver ikke til source og analyserer hver fixture i isolert child-prosess
- metadataregistrering begrenses til nøkkelnavn; genererte previews og renditions fjerner EXIF, kommentarer og øvrige kildeverdier. Opaque previews bruker JPEG, mens transparente previews bevarer alpha i PNG og vises/kompositeres mot et eksplisitt nøytralt checkerboard i HTML og JPEG-kontaktark
- gyldig sRGB, gyldig ikke-sRGB, untagged og korrupt ICC skilles. Gyldig ikke-sRGB konverteres før crop/resize. Korrupt ICC gir kontrollert feil, og untagged input registreres som en eksplisitt antakelse
- både profilfri konvertert sRGB og konvertert sRGB med standardprofil genereres som inspecterbare kandidater. Ingen av dem er godkjent som endelig kontrakt
- pixelnivåene 20, 36, 50, 64 og 100 MP evalueres som kandidater; edge variance, blockiness, logowhitespace, tid og peak RSS er advisory målinger
- lokal `review.html`, CSV/JSON-reviewmal og kontaktark støtter manuell crop-, innholds-, farge-, skarphets-, komprimerings-, logo-, whitespace-, plakat-/tekst- og vannmerkevurdering
- `redacted-summary.json` inneholder anonym ID, checksum, tekniske målinger og aggregater, aldri previews eller base64-bilder

## Outputpolicy

Harness, schema, eksempelmanifest og dokumentasjon kan committes. Private kilder og manifest committes aldri. Full evidens og visuell rapport er lokal. Kontaktark eller annen visuell evidens kan bare vurderes committet når alle inkluderte manifestposter har `redistribution_allowed=true`; denne leveransen committer ingen generert evidens.

## Ikke besluttet

- endelig maksimal pixelmengde
- dimensjonsregler per assettype, fit, variant og crop
- blur-, edge-variance-, blockiness-, logolesbarhets- eller whitespacegrenser
- warning-, manual-review- eller hard-fail-klassifisering
- profilfri versus standard sRGB-profil i offentlig output
- produksjonsavhengighet, workergrense eller runtimeplassering

Processing profile v1 og no-upscale står uendret. ADR-007 er ikke endret som om disse åpne valgene er avgjort.

## Neste gate: fase 3B.1R-B

1. Legg et lite rettighetsavklart lokalt sett i `representative/private_dataset/` med brede/høye logoer, liten tekst og whitespace, portrett/grupper, mørke foto, komprimerte nettsidebilder, plakater/årstall, vannmerker, høyoppløselige mobilbilder og reelle ICC-profiler.
2. Kjør harnesset til en lokal output-root.
3. Gjennomfør manuell visuell og teknisk review.
4. Legg frem redacted evidens og et uttrykkelig ikke-besluttet forslag.
5. La prosjekteier/ChatGPT godkjenne eller avvise hver endelig pixel-, dimensjons-, warning- og sRGB-regel separat.

Fase 3B.1R er ikke gjennomført før denne gaten er grønn.
