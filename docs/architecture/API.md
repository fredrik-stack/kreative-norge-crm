# API

**Status:** implementert, detaljkartlegging gjenstår

API-et omfatter autentisering, tenants, taksonomi, aktører, personer, koblinger, kontaktkanaler, public actors, importjobber og eksportjobber.

Tenant-scope Editor-API returnerer både interne og offentlige `PersonContact` for autoriserte brukere.

Public API returnerer bare kontaktpersoner fra aktive `OrganizationPerson`-koblinger med `publish_person=True`, og bare kontaktverdier fra `PersonContact` der `is_public=True`. Public API bruker ikke fallback fra `Person.email` eller `Person.phone`.

Import har egne handlinger for opplasting, preview, rader, AI-generering, beslutninger, commit og feilrapport.

Eksport har foreløpig grunnleggende oppretting, listing og visning av eksportjobber. Filgenerering og nedlasting er ikke bekreftet ferdig.

Endelig endepunktliste skal genereres fra aktive ruter og kontrolleres mot Swagger/OpenAPI.
