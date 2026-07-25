# Kapittel 21 – Sikkerhet

Jeg tenkte tidligere på sikkerhet som beskyttelse mot hackere. I et CRM handler den like mye om tillit: Riktige personer skal få tilgang, og publisering skal skje bevisst.

Sikkerhet er derfor ikke en funksjon vi legger til til slutt. Den må finnes i alle lag.

## Identitet, tilgang og avgrensning

**Autentisering** svarer på hvem brukeren er. **Autorisering** avgjør hva den innloggede brukeren kan gjøre.

Kreative Norge CRM bruker Django-sesjoner og CSRF-beskyttelse. CSRF hindrer at en annen nettside lurer nettleseren til å sende uønskede handlinger med en aktiv innlogging.

Rollene superadmin, gruppeadmin, redigerer og leser har ulike rettigheter. Bare de to høyeste kan slette. Tenant-avgrensning hindrer tilgang til en annen organisasjons data.

Dette følger prinsippet om minste privilegium: Hver bruker, integrasjon og AI-agent skal bare få tilgangen oppgaven krever.

## Internt er ikke det samme som offentlig

CRM-et kan lagre en aktør eller kontakt internt uten å publisere den. Organisasjoner, personkoblinger, telefonnumre og kontaktkanaler har egne publiseringsregler. Importens AI-forslag får ikke sette publiseringsflagg.

Sikkerhetsgrunnlaget finnes, men er ikke ferdig. Editor, public API og offentlig HTML bruker fortsatt ulike kontaktregler. Målarkitekturen skal samle dem, men er ikke implementert. Kontrollen må bygge på dagens kode, ikke bare planen.

## Transport, hemmeligheter og AI

I servermiljø skal HTTPS kryptere trafikken. Django har innstillinger for sikre cookies og HTTPS når debug er av, men det konkrete TLS-oppsettet må verifiseres i miljøet.

Passord, API-nøkler og andre secrets skal ikke ligge i kode, dokumentasjon eller logger. Før data sendes til en AI-tjeneste, må jeg også vurdere hvilke opplysninger som er nødvendige, hvem som behandler dem, og om resultatet krever menneskelig kontroll.

## Takeaways

- Autentisering bekrefter identitet; autorisering begrenser handlinger.
- Roller og tenant-avgrensning må håndheves i backend.
- Intern lagring og offentlig publisering er separate sikkerhetsvalg.
- Minste privilegium gjelder mennesker, integrasjoner og AI.
- Dokumentert sikkerhet må kontrolleres mot faktisk kode og miljø.

## Prinsippet

God sikkerhet gjør det trygt å samarbeide uten å gi flere data eller rettigheter enn oppgaven krever.
