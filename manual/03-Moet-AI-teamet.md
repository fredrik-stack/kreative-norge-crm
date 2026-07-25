# Kapittel 3 – Møt AI-teamet: Hvem gjør egentlig hva?

På en vanlig arbeidsdag bruker jeg blant annet ChatGPT, Codex, VS Code, GitHub, Docker og Terminal. Tidligere så jeg dem som en samling tekniske programmer. Nå ser jeg dem som et team der hvert medlem har en bestemt jobb.

Det viktigste spørsmålet er derfor ikke «Hvordan fungerer hele dette verktøyet?», men «Hvilken rolle har det i arbeidsflyten?»

## Menneskene bestemmer

**Prosjekteieren** kjenner brukerne og vet hvilket problem systemet skal løse. Jeg bestemmer visjon, prioritering, rekkefølge og hva som er godt nok. Jeg beskriver behovet, tester resultatet og tar beslutningene. Dette ansvaret kan ikke delegeres til AI.

**Den menneskelige utvikleren** bidrar med erfaring og kritisk skjønn. Et spørsmål som «Hvorfor bruker dere Django?» er verdifullt selv om Django viser seg å være riktig valg. Prosjektet trenger mennesker som utfordrer etablerte antakelser og oppdager konsekvenser verktøyene ikke ser.

## AI hjelper på ulike måter

**ChatGPT** fungerer som lærer, arkitekt og sparringspartner. Jeg bruker det til å forstå begreper, vurdere alternativer, planlegge, formulere spesifikasjoner og kvalitetssikre tankegangen. ChatGPT kjenner ikke automatisk den lokale kodebasen, så råd må bygge på oppdatert kontekst.

**Codex** arbeider direkte i prosjektet. Det kan lese filer, implementere, rydde og omstrukturere kode, skrive tester, rette feil og gjennomføre avtalte leveransesteg. Codex er godt egnet når retningen er avklart, men skal ikke gjette hvilket produkt vi ønsker eller ta strategiske valg på egen hånd.

En enkel huskeregel er:

- «Hvordan bør vi løse dette?» hører hjemme i forståelse og planlegging.
- «Implementer den godkjente løsningen» hører hjemme i kodebasen.

## Arbeidsplassen og infrastrukturen

Resten av teamet er verktøy og maskiner med avgrensede roller:

- **VS Code** er arbeidsbenken der filene leses og endres.
- **Terminal** er kontrollrommet der jeg gir kommandoer til andre programmer. `git push` ber Git sende arbeid; Terminal gjør ikke jobben selv.
- **GitHub** er den delte kopien av prosjektet, med historikk, arbeidsgrener og lagrede versjoner, kalt branches og commits.
- **Docker** starter systemets tjenester i avgrensede containere slik at prosjektet kan kjøres mer likt lokalt og på serveren.
- **Linux-serveren** er en annen datamaskin. Når jeg kobler til med sikker fjerninnlogging, kalt SSH, kjører kommandoene der, ikke på Mac-en.

## En oppgave gjennom teamet

Hvis jeg ønsker Excel-eksport, går arbeidet gjennom flere roller:

1. Jeg beskriver behovet og avgjør prioriteten.
2. Løsningen undersøkes, utfordres og besluttes.
3. Codex eller en utvikler implementerer og tester.
4. Git lagrer versjonen, og GitHub deler historikken.
5. Docker starter den nye versjonen i riktig miljø.
6. Jeg kontrollerer at funksjonen løser brukerbehovet.

Ingen av deltakerne gjør alt. Forutsigbarheten kommer av at hver rolle har et tydelig ansvar.

## Takeaways

- Prosjekteieren eier behovet, prioriteringen og kvalitetskravet.
- ChatGPT hjelper med forståelse og planlegging; Codex arbeider i kodebasen.
- Menneskelig erfaring og kritiske spørsmål er fortsatt nødvendig.
- VS Code, Terminal, GitHub, Docker og serveren har ulike oppgaver.

## Prinsippet

Et godt AI-assistert team fungerer når riktig oppgave går til riktig rolle.
