# Kapittel 20 – Oppstart av et nytt prosjekt

Jeg trodde et programvareprosjekt startet med kode. CRM-et lærte meg at problem, dataeierskap, levetid og mulighet for overtakelse må avklares først.

## Start med problemet

«Hvordan lager vi et CRM?» er et teknisk spørsmål. Et bedre utgangspunkt er: «Hvorfor trenger vi et CRM?»

Kreative Norge manglet én oversikt over personer, organisasjoner, relasjoner og offentlig publisering. Kalender, fakturering og økonomi kunne vært nyttig, men var ikke kjernen.

Problemformuleringen blir et filter: Løser forslaget hovedproblemet, eller gjør det bare prosjektet større?

## Avgrens første produkt

En **MVP**, *Minimum Viable Product*, er den minste versjonen som gir reell nytte og lar oss lære. Den er ikke en tilfeldig halvferdig løsning.

CRM-et ble delt i autentisering, aktører, personer, publisering, import, eksport og integrasjoner. Slik kunne produktet vokse gradvis.

Før arbeidet starter, bør jeg avklare:

- målgruppe og viktigste brukerreise
- dataeierskap og regler for publisering
- hva første versjon må kunne, og hva som skal vente
- levetid, vekst og mulighet for overtakelse
- personvern, sikkerhet og eksterne tjenester

## Velg teknologi etter behovet

Teknologistacken velges etter at produktet er forstått. Django, React, PostgreSQL, Docker og GitHub passet CRM-ets datamodell, API, Editor, drift og arbeidsform.

Valget må også ta hensyn til kompetanse, vedlikehold, kostnader og framtidig drift. En spennende teknologi er et dårlig valg hvis ingen kan overta den.

## Bestem hvordan prosjektet skal arbeide

Arbeidsformen er en del av arkitekturen. I Kreative Norge CRM:

1. Prosjekteieren beskriver behov og godkjenner retning.
2. ChatGPT bidrar med design og beslutningsgrunnlag.
3. Codex implementerer, tester og rapporterer fra repoet.
4. GitHub lagrer felles historikk.
5. Lokal Docker og staging brukes etter risiko.

Større endringer krever en godkjent ADR. Stabil kunnskap lagres i `docs/`, og en funksjon er ikke ferdig før dokumentasjonen er oppdatert eller kontrollert.

AI kan hjelpe med krav, datamodell, API-design, skisser og risiko. Den strukturerer beslutningsgrunnlaget; prosjekteieren bestemmer mål, prioriteringer og akseptabel risiko.

De vanligste oppstartsfeilene er å velge teknologi først, bygge for mye og utsette dokumentasjonen.

## Takeaways

- Begynn med behovet og brukerne, ikke teknologistacken.
- Avgrens en MVP som gir nytte uten å forsøke å romme alt.
- Avklar dataeierskap, personvern, levetid og overtakelse tidlig.
- Velg teknologi og arbeidsform som prosjektet kan vedlikeholde.
- Bruk AI til beslutningsgrunnlag, ikke til å overta beslutningsansvaret.

## Prinsippet

Et godt prosjekt starter med en felles forståelse av problemet, grensene og ansvaret – før den første kodelinjen skrives.
