# Kapittel 5 – Git: prosjektets hukommelse

Når en ny endring ødelegger noe som fungerte i går, er det umulig å huske alle forskjellene i hundrevis av filer. Git løser dette problemet. Det er et system for versjonskontroll: en historikk over hvordan prosjektfilene utvikler seg.

Git gjør det tryggere å endre CRM-et fordi jeg kan undersøke hva som er gjort og finne tilbake til en tidligere, lagret versjon.

## Git lagrer utviklingen

Uten versjonskontroll ender dokumenter ofte som `bok_ny.docx`, `bok_endelig.docx` og `bok_endelig2.docx`. Git lar prosjektet beholde de vanlige filnavnene og registrerer i stedet utvalgte øyeblikksbilder av hele prosjektet.

Et slikt øyeblikksbilde kalles en **commit**. En commit betyr: «Dette er en avgrenset versjon jeg vil bevare i historikken.» Den bør samle endringer som hører naturlig sammen, for eksempel:

- `Legg til Excel-eksport`
- `Rett feil ved offentlig publisering`
- `Oppdater tester for kontaktimport`

En melding som `diverse endringer` blir lite nyttig når jeg prøver å forstå historikken et halvt år senere.

Git arbeider lokalt i prosjektmappen på Mac-en. Det fungerer uten internett. GitHub kommer først inn når historikken sendes dit. Git lager historikken; GitHub oppbevarer og deler en ekstern kopi.

## Fra endring til commit

Når Codex eller en utvikler redigerer en fil, registrerer Git at arbeidskopien er forskjellig fra siste commit. Endringen blir ikke automatisk en del av historikken.

Den vanlige flyten består av fire kommandoer:

```bash
git status
git add <fil>
git commit -m "Beskriv endringen"
git push
```

`git status` viser situasjonen: endrede og nye filer, hva som er valgt til neste commit, og hvilken branch – altså arbeidsgren – jeg står på. Når jeg er usikker, starter jeg her.

`git add <fil>` velger en bestemt fil til neste commit. Dette området kalles ofte **staging area**, eller klargjøringsområdet. Filen er ikke committet ennå. Ved å angi relevante filer i stedet for å bruke `git add .` uten kontroll, reduserer jeg risikoen for å ta med uvedkommende endringer.

`git commit` lagrer de valgte endringene som et nytt punkt i den lokale historikken. Før commit bør jeg kontrollere omfanget med:

```bash
git status
git diff
git diff --staged
```

`git push` sender nye commits til GitHub. Push betyr ikke «lagre filene»; filene og commiten finnes allerede lokalt. Kommandoen deler historikken med prosjektets eksterne repo.

## Arbeidsflyten i CRM-prosjektet

En trygg, liten utviklingsøkt ser slik ut:

1. Be om en tydelig avgrenset endring.
2. La Codex eller utvikleren implementere.
3. Kjør relevante automatiske tester.
4. Prøv funksjonen manuelt når brukeropplevelsen berøres.
5. Kjør `git status` og les hvilke filer som er endret.
6. Se gjennom diffen, altså den konkrete forskjellen fra forrige versjon.
7. Legg bare de riktige filene til commiten.
8. Commit med en beskrivende melding.
9. Push til GitHub når arbeidet skal deles eller leveres videre.

Commit og push er to separate handlinger. Jeg kan committe flere ganger uten nett, og pushe senere.

## Hva Git kan og ikke kan redde

Git gjør det mulig å sammenligne versjoner, reversere en commit eller hente tilbake en tidligere fil. Men det er ikke en garanti mot alle feil. Endringer som aldri ble committet, kan være vanskeligere å gjenopprette. Git sikkerhetskopierer heller ikke automatisk den levende PostgreSQL-databasen, opplastede filer eller hemmeligheter som holdes utenfor repoet.

Derfor må tilbakeføring gjøres med omtanke. Hvis en commit også innførte en databasemigrasjon eller masseendret CRM-data, er det ikke nødvendigvis nok å gå tilbake i kodehistorikken. Da trengs en egen plan for data og backup.

## Takeaways

- Git registrerer prosjektets utvikling lokalt på Mac-en.
- En commit er et bevisst valgt øyeblikksbilde med en forklarende melding.
- `status`, `add`, `commit` og `push` dekker den vanligste grunnflyten.
- Diffen bør leses før filer committes.
- Git-historikk og databasebackup løser forskjellige problemer.

## Prinsippet

Lag små, forståelige commits som gjør det mulig å se hva som skjedde og gå trygt videre.
