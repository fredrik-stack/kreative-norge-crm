# Import Architecture

**Status:** implementert og under kvalitetssikring

Importflyten omfatter:

1. opprette importjobb
2. laste opp fil
3. parse og normalisere rader
4. validere og matche eksisterende data
5. generere AI- og heuristiske forslag
6. radvis review og beslutninger
7. commit
8. commit-logg og feilrapport

Faktisk støttede filformater skal valideres videre. Google Sheets, Checkin og Mailmojo er kun reserverte kildetyper for senere implementering.