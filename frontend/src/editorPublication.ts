import type { PersonContact } from "./types";

export type EffectivePublicationStatus = {
  tone: "hidden" | "warning" | "public";
  message: string;
};

function publicChannelLabels(contacts: PersonContact[]): string[] {
  const labels = contacts
    .filter((contact) => contact.is_public)
    .map((contact) => (contact.type === "EMAIL" ? "e-post" : "telefon"));
  return [...new Set(labels)];
}

export function describeEffectivePublication(input: {
  linkStatus: "ACTIVE" | "INACTIVE";
  publishPerson: boolean;
  contacts: PersonContact[];
}): EffectivePublicationStatus {
  const publicChannels = publicChannelLabels(input.contacts);
  if (input.linkStatus !== "ACTIVE") {
    return {
      tone: "hidden",
      message: "Koblingen er inaktiv, så personen og kontaktkanalene vises ikke på denne aktøren.",
    };
  }
  if (!input.publishPerson && publicChannels.length > 0) {
    return {
      tone: "warning",
      message:
        "Kontaktkanaler er markert offentlige på personen, men vises ikke på denne aktøren fordi personen er skjult.",
    };
  }
  if (input.publishPerson && publicChannels.length > 0) {
    return {
      tone: "public",
      message: `Kan vises offentlig på denne aktøren: ${publicChannels.join(" og ")}.`,
    };
  }
  if (input.publishPerson) {
    return {
      tone: "warning",
      message: "Personen vises offentlig, men ingen kontaktkanaler er valgt offentlig.",
    };
  }
  return {
    tone: "hidden",
    message: "Personen og kontaktkanalene er skjult på denne aktøren.",
  };
}
