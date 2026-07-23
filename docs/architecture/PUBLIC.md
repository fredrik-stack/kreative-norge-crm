# Public Architecture

**Status:** implementert grunnløsning, videreutvikling planlagt

Public består av:

- åpent API for publiserte aktører
- HTML-visning som foreløpig kun brukes i staging

Publisering styres blant annet av:

- `Organization.is_published`
- `Organization.publish_phone`
- `OrganizationPerson.publish_person`
- `PersonContact.is_public`

Løsningen skal videreutvikles før ekstern integrasjon med Musikkontoret.no.