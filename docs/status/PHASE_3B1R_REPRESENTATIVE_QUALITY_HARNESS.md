# Fase 3B.1R – representativ kvalitetsharness og beslutning

**Status:** GJENNOMFØRT / GODKJENT. Isolert lokal evidens og beslutning; ingen CRM-runtime.

**Harness levert:** 2026-08-06

**Representativ kjøring og beslutning godkjent:** 2026-08-07

## Formål og avgrensning

Fase 3B.1R utvider den syntetiske fase 3B.1-prototypen med lokal evaluering av rettighetsavklarte representative bilder. Leveransen fastsetter en konservativ MVP-kontrakt for decoded pixelmengde, dimensjon/no-upscale, advisory kvalitetsmål, logopresentasjon og sRGB-output.

Dette er arkitektur- og kvalitetsgrunnlag. Leveransen kobler ikke bildebehandling, storage-I/O, API, Editor, PUBLIC eller frontend til CRM-runtime, aktiverer ikke featureflagget og endrer ikke processing profile v1.

## Fase 3B.1R-A – implementert harness

- lokal `representative/private_dataset/` er Git-ignorert; repoet inneholder bare README, JSON Schema og anonymt eksempelmanifest
- manifestet krever anonym fixture-ID, relativ fil under `files/`, kategori, `contain`/`cover`, relevante varianter, rettighetsgrunnlag, redistribusjonsvalg, personindikator, forventet fargeprofil, reviewtemaer og korte ikke-identifiserende notater; en forventet kontrollert feil må i tillegg angi en eksakt, ikke-tom feilkode
- dupliserte IDs/filer, manglende filer, ukjente verdier, feil typer, absolutte paths, traversal og symlink-utgang avvises
- runneren krever eksplisitt dataset-root og tom, separat output-root, bruker ikke nettverk, skriver ikke til source og analyserer hver fixture i isolert child-prosess
- metadataregistrering begrenses til nøkkelnavn; genererte previews og renditions fjerner EXIF, kommentarer og øvrige kildeverdier. Opaque previews bruker JPEG, mens transparente previews bevarer alpha i PNG og vises/kompositeres mot et eksplisitt nøytralt checkerboard i HTML og JPEG-kontaktark
- gyldig sRGB, gyldig ikke-sRGB, untagged og korrupt ICC skilles. Gyldig ikke-sRGB konverteres før crop/resize. Korrupt ICC gir kontrollert feil, og untagged input registreres som en eksplisitt antakelse
- både profilfri konvertert sRGB og konvertert sRGB med standardprofil genereres som inspecterbare kandidater
- pixelnivåene 20, 36, 50, 64 og 100 MP evalueres; edge variance, blockiness, logowhitespace, tid og peak RSS måles som advisory evidens
- lokal `review.html`, CSV/JSON-reviewmal og kontaktark støtter manuell crop-, innholds-, farge-, skarphets-, komprimerings-, logo-, whitespace-, plakat-/tekst- og vannmerkevurdering
- `redacted-summary.json` inneholder anonyme tekniske målinger og aggregater, aldri previews eller base64-bilder

## Fase 3B.1R-B – representativ evidens

Den lokale kjøringen brukte 24 rettighetsavklarte fixtures. Alle var merket `rights_basis=owned` og `redistribution_allowed=false`. Harnesset fullførte 24/24 uten nettverk, og alle visuelle artefakter forble lokale.

Anonymiserte resultater:

- 20 MP avviste to representative, nyttige kilder
- 36 MP var den laveste testede kandidatgrensen som beholdt alle 24
- 50, 64 og 100 MP beholdt også alle 24, uten dokumentert produktgevinst i datasettet
- 17/24 kunne produsere `square`, 15/24 `landscape` og 13/24 `share` uten oppskalering; variasjonen viste at dimensjoner må vurderes per variant og faktisk cropområde
- edge variance og blockiness hadde både treff og tydelige moteksempler mot manuell visuell review; ingen numerisk verdi støttet automatisk hard fail
- stort målt logowhitespace kunne sammenfalle med dårlig presentasjon, men forholdstallet alene var ikke en pålitelig godkjenningsregel
- gyldig embedded non-sRGB ble konvertert før crop/resize; untagged input ble registrert som antatt sRGB; ingen kontrollert profilfeil oppstod i datasettet
- profilfri output etter sRGB-konvertering var byte-deterministisk i 45/45 sammenlignede outputs
- kandidaten med generert standard sRGB-profil ga identiske dekodede piksler, men ikke byte-identiske filer, og ble ikke valgt for MVP
- manuell analyseklassifisering ga 6 `pass`, 9 `manual_review` og 9 `reject`; dette var beslutningsevidens, ikke en automatisk produksjonspolicy

Datasettet er representativ MVP-evidens, ikke en påstand om statistisk universelle terskler. Nye kildeklasser, driftsmålinger eller konkrete problemer kan utløse en senere revurdering.

## Godkjente beslutninger

### Decoded pixel- og bytegrenser

- 36 MP er konfigurerbar standard for maksimal decoded pixelmengde.
- 36 MP er et konservativt MVP-valg og kan revurderes ved ny evidens.
- Maksimal kildefilstørrelse forblir 15 MiB som konfigurerbar standard.

### Dimensjon og no-upscale

- Det finnes ingen universell minimumsbredde eller minimumshøyde.
- Automatisk oppskalering er ikke tillatt.
- Logo bruker `contain` og skal aldri crop-es.
- Foto bruker `cover` og vurderes separat for `square`, `landscape` og `share` ut fra faktisk cropområde og scaling margin.
- Alle obligatoriske renditions må kunne produseres uten oppskalering før et asset er klart for godkjenning.
- Manglende obligatorisk rendition gir `NOT READY FOR APPROVAL`, men sletter eller avviser ikke nødvendigvis kildekandidaten. Redaksjonell flyt skal be om bedre kilde, annet bilde eller fallback.

### Kvalitetsmål og tekniske blokkeringer

- Edge variance og blockiness er informational/advisory.
- Tydelige outliers kan gi warning og, kombinert med liten kilde, synlig komprimering, mye tekst, vannmerkerisiko eller et annet visuelt problem, trigge manual review.
- Ingen numerisk edge-variance-, blur- eller blockinessgrense er automatisk hard fail. Prototypeintervallene fra fase 3B.1 er ikke produksjonsgrenser.
- Decodefeil, unsupported/ugyldig input, korrupt eller uleselig ICC og en manglende obligatorisk rendition under no-upscale-kontrakten kan blokkere teknisk readiness. Dette er ikke en subjektiv kvalitetsdom.

### Logo-whitespace og lesbarhet

- Mye internt whitespace kan gi warning og manual review, men er ikke hard fail alene.
- Numerisk whitespaceprosent er ikke alene en godkjenningsregel.
- Faktisk lesbarhet og presentasjon ved relevante UI-størrelser er avgjørende.

### sRGB-outputkontrakt

MVP-kontrakten er:

```text
gyldig kilde
    → eksplisitt normalisering eller konvertering til sRGB
    → crop og resize
    → offentlig rendition uten innebygd ICC-profil
```

- Embedded sRGB går gjennom samme normaliseringskontrakt.
- Gyldig embedded non-sRGB konverteres eksplisitt til sRGB før crop og resize.
- Untagged behandles som antatt sRGB, registreres som `untagged`/`assumed-sRGB` og er ikke automatisk hard fail.
- Korrupt eller uleselig ICC ignoreres ikke; det er en kontrollert teknisk feil som krever en annen eller reparert kilde.
- Kildeprofiler kopieres ikke til offentlig rendition.
- Fast innebygd standard sRGB-profil er ikke valgt for MVP. En senere vurdering krever separat deterministisk test av en kanonisk profil uten variabel metadata.

## Processing profile v1 – uendret

- Foto `square`: 512 × 512 WebP quality 82
- Foto `landscape`: 800 × 450 WebP quality 82
- Foto `share`: 1200 × 630 JPEG quality 85, ikke-progressiv
- Logo med alpha: PNG
- No-upscale beholdes
- Pillow er primær MVP-retning bak intern adapter
- Statisk JPEG, PNG og WebP er de eneste MVP-inputformatene

## Private data og outputpolicy

Harness, schema, eksempelmanifest og dokumentasjon kan committes. Private kilder, privat manifest, full evidens, `review.html`, kontaktark, thumbnails, previews og renditions committes aldri fra denne kjøringen. Dokumentasjonen bruker bare anonymiserte aggregater som ikke identifiserer personer eller aktører.

## Fortsatt åpne senere gater

Fase 3B.1R er gjennomført og godkjent, men hele fase 3B er ikke ferdig. Før reell processing og offentlig serving aktiveres, gjenstår blant annet:

- lokal private/public serving og permissions
- cache, purge og verifikasjon
- permanent deny-journal, read-model og cursor
- endelig API-schema og aliasmapping
- public release key-struktur
- retention og cleanupmekanisme
- sync/async-grense og eventuell worker
- observability
- SVG-policy og eventuell sikker rasterisering
- eventuell skadevarekontroll

CRM-runtime, legacybildebruk og det avslåtte featureflagget er uendret av fase 3B.1R.
