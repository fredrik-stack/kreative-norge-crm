import { expect, test } from "@playwright/test";
import { loginAsEditor, setupMockEditorApi } from "./mockEditorApi";

test("create, update and remove organization-person link", async ({ page }) => {
  await setupMockEditorApi(page, {
    persons: [
      {
        id: 20,
        tenant: 1,
        full_name: "Ada Editor",
        title: "Manager",
        email: "ada@example.com",
        phone: "+4799999999",
        municipality: "Oslo",
        note: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        contacts: [],
      },
      {
        id: 21,
        tenant: 1,
        full_name: "Bjarne Kontakt",
        title: "Kontaktperson",
        email: "bjarne@example.com",
        phone: null,
        municipality: "Bergen",
        note: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        contacts: [],
      },
    ],
  });

  await page.goto("/organizations");
  await loginAsEditor(page);

  await page.getByRole("button", { name: "Rediger" }).click();
  await expect(page.getByRole("heading", { name: "Personkoblinger" })).toBeVisible();
  await page.getByRole("button", { name: "Knytt eksisterende person" }).click();

  const row = page.locator(".link-row").filter({ hasText: "Ada Editor" }).first();
  await expect(row).toBeVisible();
  await expect(row.getByRole("combobox").first()).toHaveValue("ACTIVE");
  await expect(row.getByRole("checkbox", { name: "Publiser" })).toBeChecked();

  await row.getByRole("combobox").first().selectOption("INACTIVE");
  await row.getByRole("checkbox", { name: "Publiser" }).click();
  await expect(row.getByRole("combobox").first()).toHaveValue("INACTIVE");
  await expect(row.getByRole("checkbox", { name: "Publiser" })).not.toBeChecked();

  page.once("dialog", (dialog) => dialog.accept());
  await row.getByRole("button", { name: "Fjern" }).click();

  await expect(page.getByText("Ingen personer koblet til denne organisasjonen.")).toBeVisible();
});
