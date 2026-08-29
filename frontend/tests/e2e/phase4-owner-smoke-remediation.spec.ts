import { expect, test } from "@playwright/test";
import { loginAsEditor, setupMockEditorApi } from "./mockEditorApi";

const now = "2026-08-29T00:00:00Z";

function organization(overrides: Record<string, unknown>) {
  return {
    id: 10,
    tenant: 1,
    name: "Svensk kontaktaktør",
    org_number: "123456789",
    email: "post@example.com",
    phone: "22 12 34 56",
    phone_region_used: "NO",
    phone_dial_uri: "tel:+4722123456",
    municipalities: "Oslo",
    note: null,
    description: "Owner-smoke testaktør",
    is_published: true,
    publish_phone: false,
    website_url: null,
    facebook_url: null,
    instagram_url: null,
    tiktok_url: null,
    linkedin_url: null,
    youtube_url: null,
    og_title: null,
    og_description: null,
    og_image_url: null,
    thumbnail_image_url: null,
    auto_thumbnail_url: null,
    og_last_fetched_at: null,
    primary_link: null,
    primary_link_field: null,
    preview_image_url: null,
    image_asset_feature_enabled: false,
    tags: [],
    categories: [],
    subcategories: [],
    created_at: now,
    updated_at: now,
    active_people: [],
    ...overrides,
  };
}

function person(overrides: Record<string, unknown>) {
  return {
    id: 20,
    tenant: 1,
    full_name: "Svensk Kontakt",
    title: "Produsent",
    email: null,
    phone: "070 123 45 67",
    phone_region_used: "SE",
    phone_dial_uri: "tel:+46701234567",
    municipality: "Stockholm",
    note: null,
    website_url: null,
    instagram_url: null,
    tiktok_url: null,
    linkedin_url: null,
    facebook_url: null,
    youtube_url: null,
    tags: [],
    categories: [],
    subcategories: [],
    created_at: now,
    updated_at: now,
    contacts: [],
    ...overrides,
  };
}

test("canonical dial targets, internal actor phones and effective PUBLIC state stay aligned", async ({ page }) => {
  const swedishPhone = {
    id: 30,
    tenant: 1,
    person: 20,
    type: "PHONE" as const,
    value: "070 123 45 67",
    phone_region_used: "SE",
    phone_dial_uri: "tel:+46701234567",
    is_primary: true,
    is_public: true,
    created_at: now,
  };
  const privatePhone = {
    id: 31,
    tenant: 1,
    person: 21,
    type: "PHONE" as const,
    value: "900 00 002",
    phone_region_used: "NO",
    phone_dial_uri: "tel:+4790000002",
    is_primary: true,
    is_public: false,
    created_at: now,
  };
  const linkedPeople = [
    { id: 40, tenant: 1, organization: 10, person: 20, status: "ACTIVE" as const, publish_person: false, created_at: now },
    { id: 41, tenant: 1, organization: 10, person: 21, status: "ACTIVE" as const, publish_person: true, created_at: now },
  ];
  const nestedPeople = [
    {
      id: 40,
      status: "ACTIVE",
      publish_person: false,
      created_at: now,
      person: {
        id: 20,
        full_name: "Svensk Kontakt",
        title: "Produsent",
        municipality: "Stockholm",
        public_contacts: [swedishPhone],
      },
    },
    {
      id: 41,
      status: "ACTIVE",
      publish_person: true,
      created_at: now,
      person: {
        id: 21,
        full_name: "Intern Kontakt",
        title: null,
        municipality: "Oslo",
        public_contacts: [],
      },
    },
  ];
  const state = await setupMockEditorApi(page, {
    organizations: [
      organization({ active_people: nestedPeople }),
      organization({
        id: 11,
        name: "Offentlig telefonaktør",
        phone: "23 45 67 89",
        phone_dial_uri: "tel:+4723456789",
        publish_phone: true,
      }),
      organization({ id: 12, name: "Aktør uten telefon", phone: null, phone_region_used: null, phone_dial_uri: null }),
    ],
    persons: [
      person({ contacts: [swedishPhone] }),
      person({
        id: 21,
        full_name: "Intern Kontakt",
        phone: "900 00 002",
        phone_region_used: "NO",
        phone_dial_uri: "tel:+4790000002",
        contacts: [privatePhone],
      }),
    ],
    organizationPeople: linkedPeople,
    personContacts: [swedishPhone, privatePhone],
  });

  const contactPatches: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "PATCH" && request.url().includes("/person-contacts/")) {
      contactPatches.push(request.url());
    }
  });

  await page.goto("/people");
  await loginAsEditor(page);

  const overviewPhone = page.getByRole("link", { name: "070 123 45 67" }).first();
  await expect(overviewPhone).toHaveAttribute("href", "tel:+46701234567");
  await page.getByRole("button", { name: "Svensk Kontakt", exact: true }).click();
  await expect(page.getByRole("dialog").getByRole("link", { name: "070 123 45 67" })).toHaveAttribute(
    "href",
    "tel:+46701234567",
  );
  await page.getByRole("dialog").getByRole("button", { name: "Rediger" }).click();
  await expect(page.getByLabel("Telefon", { exact: true })).toHaveValue("070 123 45 67");
  await page.getByRole("button", { name: "Lagre person" }).click();
  await expect(page.getByText(/Sist lagret/)).toBeVisible();
  await expect(page.getByText(/Koblet til 1 aktør: 0 viser personen offentlig, 1 skjuler personen/)).toBeVisible();
  const savedContactCard = page.locator("article.modal-contact-card").first();
  await expect(savedContactCard.getByText("Kan vises offentlig", { exact: true })).toBeVisible();
  await expect(savedContactCard.getByText(/vises bare på aktører der personen også er satt til/)).toBeVisible();

  await page.getByRole("link", { name: /^Aktører/ }).click();
  const internalActor = page.locator("article.editor-card").filter({ hasText: "Svensk kontaktaktør" });
  await expect(internalActor.getByText("Telefon · Kun intern")).toBeVisible();
  await expect(internalActor.getByRole("link", { name: "22 12 34 56" })).toHaveAttribute("href", "tel:+4722123456");
  const publicActor = page.locator("article.editor-card").filter({ hasText: "Offentlig telefonaktør" });
  await expect(publicActor.getByText("Telefon · Offentlig")).toBeVisible();
  await expect(publicActor.getByRole("link", { name: "23 45 67 89" })).toHaveAttribute("href", "tel:+4723456789");
  await expect(page.locator("article.editor-card").filter({ hasText: "Aktør uten telefon" }).getByRole("link")).toHaveCount(0);

  await internalActor.getByRole("heading", { name: "Svensk kontaktaktør" }).click();
  const actorDialog = page.getByRole("dialog");
  await expect(actorDialog.getByText("Telefon · Kun intern")).toBeVisible();
  await expect(actorDialog.getByRole("link", { name: "22 12 34 56" })).toHaveAttribute("href", "tel:+4722123456");
  await expect(actorDialog.getByRole("link", { name: "070 123 45 67" })).toHaveAttribute("href", "tel:+46701234567");
  await actorDialog.getByRole("button", { name: "Rediger" }).click();

  const swedishRow = page.locator(".link-row").filter({ hasText: "Svensk Kontakt" });
  await expect(swedishRow.getByText(/vises ikke på denne aktøren fordi personen er skjult/)).toBeVisible();
  await swedishRow.getByRole("checkbox", { name: "Vis person offentlig" }).click();
  await expect(swedishRow.getByText("Kan vises offentlig på denne aktøren: telefon.")).toBeVisible();
  expect(contactPatches).toHaveLength(0);
  expect(state.personContacts.find((contact) => contact.id === 30)?.is_public).toBe(true);

  const noPublicContactsRow = page.locator(".link-row").filter({ hasText: "Intern Kontakt" });
  await expect(noPublicContactsRow.getByText("Personen vises offentlig, men ingen kontaktkanaler er valgt offentlig.")).toBeVisible();
});
