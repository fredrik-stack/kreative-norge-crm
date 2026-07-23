---
name: undersok-feil-for-retting
description: Undersøk og dokumenter en feil i Kreative Norge CRM før kode endres. Bruk når symptomet er kjent, men rotårsaken er usikker, særlig ved dataflyt, publisering, import, Editor CRM eller PUBLIC.
---

# Undersøk feil før retting

Følg `docs/development/WORKFLOW.md` og les relevante arkitektur-, feature- og ADR-dokumenter.

1. Reproduser feilen med testdata eller sikre lokale metoder.
2. Følg dataflyten gjennom modell, serializer/API, frontend, import og visning.
3. Skill mellom kodefeil, feil i eksisterende data og konfigurasjonsfeil.
4. Finn første punkt der faktisk adferd avviker fra forventet adferd.
5. Kartlegg eksisterende testdekning og manglende regresjonstester.
6. Vurder personvern, permissions, tenant-isolasjon og risiko for å eksponere data.
7. Foreslå minste trygge rettelse, eventuell datareparasjon og berørte filer.
8. Rapporter bevis, rotårsak, omfang, risiko og anbefaling.
9. Stopp før implementering, commit og push med mindre Fredrik uttrykkelig ber om fullføring.