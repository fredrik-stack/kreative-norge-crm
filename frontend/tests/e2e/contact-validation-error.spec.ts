import { test, expect } from "@playwright/test";
import { loginAsEditor, setupMockEditorApi } from "./mockEditorApi";

test("shows backend validation error when creating person contact", async ({ page }) => {
  await setupMockEditorApi(page);

  await page.route("**/api/tenants/1/person-contacts/", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 400,
      contentType: "application/json",
      body: JSON.stringify({
        value: ["Denne kontaktverdien er allerede i bruk for valgt person."],
      }),
    });
  });

  await page.goto("/people/20");
  await loginAsEditor(page);

  await expect(page.getByRole("button", { name: /Ada Editor/ })).toBeVisible();
  await page.locator(".contact-create input[placeholder*='verdi']").fill("dupe@example.com");
  await page.getByRole("button", { name: "Legg til kontakt" }).click();

  await expect(page.getByText("Denne kontaktverdien er allerede i bruk for valgt person.")).toBeVisible();
});
