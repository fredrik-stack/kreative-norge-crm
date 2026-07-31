# API

**Status:** implementert, detaljkartlegging gjenstår

API-et omfatter autentisering, tenants, taksonomi, aktører, personer, koblinger, kontaktkanaler, public actors, importjobber og eksportjobber.

Tenant-scope Editor-API returnerer både interne og offentlige `PersonContact` for autoriserte brukere.

Det aktive public API-et under `/api/public/` bruker `crm.serializers_public.PublicActorSerializer`. Det returnerer bare kontaktpersoner fra aktive `OrganizationPerson`-koblinger med `publish_person=True`, og bare kontaktverdier fra `PersonContact` der `is_public=True`. Public API bruker ikke fallback fra `Person.email` eller `Person.phone`.

Personobjektet i public-kontrakten inneholder additivt `title` når `Person.title` har en verdi. Feltet utelates når tittelen er null eller tom. Tittelen er foreløpig global på `Person`; relasjonsspesifikk tittel er planlagt senere.

Import har egne handlinger for opplasting, preview, rader, AI-generering, beslutninger, commit og feilrapport.

Eksport har foreløpig grunnleggende oppretting, listing og visning av eksportjobber. Filgenerering og nedlasting er ikke bekreftet ferdig.

## Planlagt bildekontrakt – ADR-007

[ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) er godkjent som målarkitektur, men er ikke implementert. Det aktive public API-et returnerer fortsatt legacy bilde-URL-er.

Den planlagte overgangen er additiv:

- et strukturert bildeobjekt får `kind`, alt-tekst, eventuell offentlig kreditering og `square`-, `landscape`- og `share`-renditions med URL, bredde og høyde
- bare CRM-kontrollerte renditions eller systemfallback blir aktive bildekilder etter cutover
- offentlige rendition-URL-er blir absolutte HTTPS-URL-er
- intern kilde, proveniens, review, audit og privat original eksponeres ikke
- `thumbnail_image_url` og `preview_image_url` beholdes midlertidig som deprecated aliaser til dokumenterte rendition-URL-er
- aliasene fjernes bare i en senere eksplisitt API-versjon eller integrasjonsfase
- API-lesing gjør ingen ekstern bildefetch

Canonical app-URL-er og public rendition-URL-er skal bygges fra miljøkonfigurerte, allowlistede site- og media-origins, ikke fra vilkårlig request-host.

Eksakt toppnivåfeltnavn, enum og alias-til-variant-mapping fastsettes i fase 3B før API-implementering.

Endelig endepunktliste skal genereres fra aktive ruter og kontrolleres mot Swagger/OpenAPI.
