# API

**Status:** implementert, detaljkartlegging gjenstår

API-et omfatter autentisering, tenants, taksonomi, aktører, personer, koblinger, kontaktkanaler, public actors, importjobber og eksportjobber.

Tenant-scope Editor-API returnerer både interne og offentlige `PersonContact` for autoriserte brukere.

Det aktive public API-et under `/api/public/` bruker `crm.serializers_public.PublicActorSerializer`. Det returnerer bare kontaktpersoner fra aktive `OrganizationPerson`-koblinger med `publish_person=True`, og bare kontaktverdier fra `PersonContact` der `is_public=True`. Public API bruker ikke fallback fra `Person.email` eller `Person.phone`.

Personobjektet i public-kontrakten inneholder additivt `title` når `Person.title` har en verdi. Feltet utelates når tittelen er null eller tom. Tittelen er foreløpig global på `Person`; relasjonsspesifikk tittel er planlagt senere.

Import har egne handlinger for opplasting, preview, rader, AI-generering, beslutninger, commit og feilrapport.

Eksport har foreløpig grunnleggende oppretting, listing og visning av eksportjobber. Filgenerering og nedlasting er ikke bekreftet ferdig.

Endelig endepunktliste skal genereres fra aktive ruter og kontrolleres mot Swagger/OpenAPI.
