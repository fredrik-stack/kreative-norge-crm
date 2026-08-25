import { expect, test, type Page } from "@playwright/test";
import { loginAsEditor, setupMockEditorApi } from "./mockEditorApi";

function linkedPersonForm(page: Page) {
  return page.locator("form.editor-form").filter({
    has: page.getByRole("button", { name: "Opprett og knytt kontaktperson" }),
  });
}

async function openFirstOrganization(page: Page) {
  await page.goto("/organizations");
  await loginAsEditor(page);
  await page.getByRole("button", { name: "Rediger" }).first().click();
  await expect(page.getByRole("heading", { name: "Opprett ny kontaktperson for denne aktøren" })).toBeVisible();
}

test("new linked person reuses backend-created private primary contacts", async ({ page }) => {
  const contactPosts: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().includes("/person-contacts/")) {
      contactPosts.push(request.url());
    }
  });
  const state = await setupMockEditorApi(page);

  await openFirstOrganization(page);
  const form = linkedPersonForm(page);
  await form.getByLabel(/^Fullt navn/).fill("Privat Kontakt");
  await form.getByLabel("E-post", { exact: true }).fill("privat@example.com");
  await form.getByLabel("Telefon", { exact: true }).fill("+47 900 00 001");
  await form.getByRole("button", { name: "Opprett og knytt kontaktperson" }).click();

  await expect(page.locator(".link-row").filter({ hasText: "Privat Kontakt" })).toBeVisible();
  const createdPerson = state.persons.find((person) => person.full_name === "Privat Kontakt");
  expect(createdPerson).toBeDefined();
  const createdContacts = state.personContacts.filter((contact) => contact.person === createdPerson?.id);
  expect(createdContacts).toHaveLength(2);
  expect(createdContacts.map((contact) => contact.type).sort()).toEqual(["EMAIL", "PHONE"]);
  expect(createdContacts.every((contact) => contact.is_primary && !contact.is_public)).toBe(true);
  expect(contactPosts).toHaveLength(0);
  expect(state.organizationPeople.find((link) => link.person === createdPerson?.id)?.publish_person).toBe(false);

  await expect(form.getByLabel(/^Fullt navn/)).toHaveValue("");
  await expect(form.getByRole("checkbox", { name: /Gjør denne e-postadressen offentlig/ })).not.toBeChecked();
  await expect(form.getByRole("checkbox", { name: /Gjør dette telefonnummeret offentlig/ })).not.toBeChecked();
  await expect(form.getByRole("checkbox", { name: /Vis ny person som kontaktperson offentlig/ })).not.toBeChecked();
  await expect(
    page.getByRole("checkbox", { name: "Vis eksisterende person som kontaktperson offentlig" }),
  ).not.toBeChecked();
});

test("explicit opt-in publishes existing primaries and link, then resets all choices", async ({ page }) => {
  const contactPatches: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "PATCH" && request.url().includes("/person-contacts/")) {
      contactPatches.push(request.url());
    }
  });
  const state = await setupMockEditorApi(page);

  await openFirstOrganization(page);
  const form = linkedPersonForm(page);
  await form.getByLabel(/^Fullt navn/).fill("Offentlig Kontakt");
  await form.getByLabel("E-post", { exact: true }).fill("offentlig@example.com");
  await form.getByLabel("Telefon", { exact: true }).fill("+47 900 00 002");
  await form.getByRole("checkbox", { name: /Gjør denne e-postadressen offentlig/ }).check();
  await form.getByRole("checkbox", { name: /Gjør dette telefonnummeret offentlig/ }).check();
  await form.getByRole("checkbox", { name: /Vis ny person som kontaktperson offentlig/ }).check();
  await page.getByRole("checkbox", { name: "Vis eksisterende person som kontaktperson offentlig" }).check();
  await form.getByRole("button", { name: "Opprett og knytt kontaktperson" }).click();

  await expect(page.locator(".link-row").filter({ hasText: "Offentlig Kontakt" })).toBeVisible();
  const createdPerson = state.persons.find((person) => person.full_name === "Offentlig Kontakt");
  expect(createdPerson).toBeDefined();
  const createdContacts = state.personContacts.filter((contact) => contact.person === createdPerson?.id);
  expect(createdContacts).toHaveLength(2);
  expect(createdContacts.every((contact) => contact.is_primary && contact.is_public)).toBe(true);
  expect(contactPatches).toHaveLength(2);
  expect(state.organizationPeople.find((link) => link.person === createdPerson?.id)?.publish_person).toBe(true);

  await expect(form.getByRole("checkbox", { name: /Gjør denne e-postadressen offentlig/ })).not.toBeChecked();
  await expect(form.getByRole("checkbox", { name: /Gjør dette telefonnummeret offentlig/ })).not.toBeChecked();
  await expect(form.getByRole("checkbox", { name: /Vis ny person som kontaktperson offentlig/ })).not.toBeChecked();
  await expect(
    page.getByRole("checkbox", { name: "Vis eksisterende person som kontaktperson offentlig" }),
  ).not.toBeChecked();
});

test("switching organization clears linked-person draft, errors, status and publication choices", async ({ page }) => {
  const state = await setupMockEditorApi(page);
  state.organizations.push({
    ...state.organizations[0],
    id: 11,
    name: "Zeta Kultur AS",
    org_number: "987654321",
  });

  await openFirstOrganization(page);
  const firstForm = linkedPersonForm(page);
  await firstForm.getByLabel(/^Fullt navn/).fill("Skal ikke følge med");
  await firstForm.getByLabel("Tittel", { exact: true }).fill("Midlertidig tittel");
  await firstForm.getByLabel("Telefon", { exact: true }).fill("123");
  await firstForm.getByRole("checkbox", { name: /Gjør denne e-postadressen offentlig/ }).check();
  await firstForm.getByRole("checkbox", { name: /Gjør dette telefonnummeret offentlig/ }).check();
  await firstForm.getByRole("checkbox", { name: /Vis ny person som kontaktperson offentlig/ }).check();
  const existingLinkForm = page.locator("form.link-create");
  await existingLinkForm
    .getByRole("checkbox", { name: "Vis eksisterende person som kontaktperson offentlig" })
    .check();
  await existingLinkForm.getByRole("combobox").selectOption("INACTIVE");

  await page.getByRole("button", { name: "Lagre endringer" }).click();
  await expect(page.getByText(/Sist lagret/)).toBeVisible();
  await expect(firstForm.getByLabel(/^Fullt navn/)).toHaveValue("Skal ikke følge med");
  await expect(firstForm.getByRole("checkbox", { name: /Vis ny person som kontaktperson offentlig/ })).toBeChecked();
  await expect(
    existingLinkForm.getByRole("checkbox", { name: "Vis eksisterende person som kontaktperson offentlig" }),
  ).toBeChecked();

  await firstForm.getByRole("button", { name: "Opprett og knytt kontaktperson" }).click();
  await expect(page.getByText("Ugyldig telefonnummer.", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Aktører", exact: true }).click();
  await page.getByRole("button", { name: "Rediger" }).last().click();

  const secondForm = linkedPersonForm(page);
  await expect(secondForm.getByLabel(/^Fullt navn/)).toHaveValue("");
  await expect(secondForm.getByLabel("Tittel", { exact: true })).toHaveValue("");
  await expect(secondForm.getByLabel("Telefon", { exact: true })).toHaveValue("");
  await expect(secondForm.getByRole("combobox").last()).toHaveValue("ACTIVE");
  await expect(secondForm.getByRole("checkbox", { name: /Gjør denne e-postadressen offentlig/ })).not.toBeChecked();
  await expect(secondForm.getByRole("checkbox", { name: /Gjør dette telefonnummeret offentlig/ })).not.toBeChecked();
  await expect(secondForm.getByRole("checkbox", { name: /Vis ny person som kontaktperson offentlig/ })).not.toBeChecked();
  await expect(
    page.getByRole("checkbox", { name: "Vis eksisterende person som kontaktperson offentlig" }),
  ).not.toBeChecked();
  await expect(page.locator("form.link-create").getByRole("combobox")).toHaveValue("ACTIVE");
  await expect(page.getByText("Ugyldig telefonnummer.", { exact: true })).toHaveCount(0);
  await expect(
    page
      .getByRole("heading", { name: "Opprett ny kontaktperson for denne aktøren" })
      .locator("..")
      .getByText("Klar", { exact: true }),
  ).toBeVisible();
});
