import { describeEffectivePublication } from "./editorPublication";
import type { PersonContact } from "./types";

function contact(type: "EMAIL" | "PHONE", isPublic: boolean): PersonContact {
  return {
    id: type === "EMAIL" ? 1 : 2,
    type,
    value: type === "EMAIL" ? "person@example.com" : "070 123 45 67",
    phone_region_used: type === "PHONE" ? "SE" : null,
    phone_dial_uri: type === "PHONE" ? "tel:+46701234567" : null,
    is_primary: true,
    is_public: isPublic,
    created_at: "2026-08-29T00:00:00Z",
  };
}

describe("describeEffectivePublication", () => {
  it("explains public contacts hidden by publish_person=false", () => {
    const result = describeEffectivePublication({
      linkStatus: "ACTIVE",
      publishPerson: false,
      contacts: [contact("PHONE", true)],
    });

    expect(result.tone).toBe("warning");
    expect(result.message).toContain("vises ikke på denne aktøren fordi personen er skjult");
  });

  it("lists channels that can be shown when both gates are open", () => {
    const result = describeEffectivePublication({
      linkStatus: "ACTIVE",
      publishPerson: true,
      contacts: [contact("EMAIL", true), contact("PHONE", true)],
    });

    expect(result.tone).toBe("public");
    expect(result.message).toBe("Kan vises offentlig på denne aktøren: e-post og telefon.");
  });

  it("explains a public person with no eligible contacts", () => {
    const result = describeEffectivePublication({
      linkStatus: "ACTIVE",
      publishPerson: true,
      contacts: [contact("PHONE", false)],
    });

    expect(result.tone).toBe("warning");
    expect(result.message).toBe("Personen vises offentlig, men ingen kontaktkanaler er valgt offentlig.");
  });

  it("shows the simple hidden state without changing contact flags", () => {
    const contacts = [contact("PHONE", false)];
    const before = contacts.map((item) => item.is_public);
    const result = describeEffectivePublication({
      linkStatus: "ACTIVE",
      publishPerson: false,
      contacts,
    });

    expect(result.tone).toBe("hidden");
    expect(result.message).toBe("Personen og kontaktkanalene er skjult på denne aktøren.");
    expect(contacts.map((item) => item.is_public)).toEqual(before);
  });
});
