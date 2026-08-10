# API

**Status:** implementert, detaljkartlegging gjenstår

API-et omfatter autentisering, tenants, taksonomi, aktører, personer, koblinger, kontaktkanaler, interne bildekandidathandlinger, public actors, importjobber og eksportjobber.

Tenant-scope Editor-API returnerer både interne og offentlige `PersonContact` for autoriserte brukere.

Det aktive public API-et under `/api/public/` bruker `crm.serializers_public.PublicActorSerializer`. Det returnerer bare kontaktpersoner fra aktive `OrganizationPerson`-koblinger med `publish_person=True`, og bare kontaktverdier fra `PersonContact` der `is_public=True`. Public API bruker ikke fallback fra `Person.email` eller `Person.phone`.

Personobjektet i public-kontrakten inneholder additivt `title` når `Person.title` har en verdi. Feltet utelates når tittelen er null eller tom. Tittelen er foreløpig global på `Person`; relasjonsspesifikk tittel er planlagt senere.

Import har egne handlinger for opplasting, preview, rader, AI-generering, beslutninger, commit og feilrapport.

Eksport har foreløpig grunnleggende oppretting, listing og visning av eksportjobber. Filgenerering og nedlasting er ikke bekreftet ferdig.

## Intern bildekandidatflyt og planlagt public bildekontrakt – ADR-007

[ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) er godkjent målarkitektur. Fase 3D.1 implementerer første interne Editor-flyt bak `IMAGE_ASSET_FEATURE_ENABLED`: offisiell discovery, kandidat-preview, valgt processing, rendition-preview, eksplisitt approval og tenant-scopet image state. Det aktive public API-et returnerer fortsatt bare legacy bilde-URL-er.

På én tenant-scopet Organization finnes følgende interne handlinger:

- `POST images/discover/` finner maksimalt seks kandidater fra `website_url`, lagret Open Graph og én kontrollert sidefetch
- `POST images/candidate-preview/` tar en kortlivet signert `candidate_ref` i body og returnerer et begrenset, privat/no-store rasterpreview
- `POST images/process/` verifiserer kandidaten og sender bare det valgte bildet gjennom processing profile v1
- `POST images/rendition-preview/` tar en signert previewref og én av `square`, `landscape` eller `share` i body; privat original og storage key eksponeres aldri
- `POST images/approve/` tar signert `approval_ref`, `expected_revision`, alt-tekst og eventuell offentlig kreditering og bruker eksisterende locking/replacement
- `GET images/state/` returnerer aktiv selection, expected revision og signert intern previewinformasjon

Referansene er tidsstemplet, omtrent 30 minutter gamle maksimalt, og bundet til tenant, Organization og autentisert bruker. Caller kan ikke levere fri kandidat-URL, proveniens, asset-ID eller rendition-sett ved approval. Lesere kan lese image state, men kan ikke starte discovery/fetch/processing eller godkjenne. Når featureflagget er av, feiler de nye rutene før nettverk, storage eller bildedomene-write.

Den planlagte overgangen er additiv:

- et strukturert bildeobjekt får `kind`, alt-tekst, eventuell offentlig kreditering og `square`-, `landscape`- og `share`-renditions med URL, bredde og høyde
- bare CRM-kontrollerte renditions eller systemfallback blir aktive bildekilder etter cutover
- offentlige rendition-URL-er blir absolutte HTTPS-URL-er
- intern kilde, proveniens, review, audit og privat original eksponeres ikke
- `thumbnail_image_url` og `preview_image_url` beholdes midlertidig som deprecated aliaser til dokumenterte rendition-URL-er
- aliasene fjernes bare i en senere eksplisitt API-versjon eller integrasjonsfase
- API-lesing gjør ingen ekstern bildefetch

Canonical app-URL-er og public rendition-URL-er skal bygges fra miljøkonfigurerte, allowlistede site- og media-origins, ikke fra vilkårlig request-host.

Eksakt public toppnivåfeltnavn, enum og alias-til-variant-mapping fastsettes før public API-implementering. De interne refsene og previewene er ikke public projection eller public serving.

Endelig endepunktliste skal genereres fra aktive ruter og kontrolleres mot Swagger/OpenAPI.
