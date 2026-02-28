import { test, expect } from "@playwright/test";
import { loginAsEditor, setupMockEditorApi } from "./mockEditorApi";

test("edit person and create/update contact", async ({ page }) => {
  await setupMockEditorApi(page);

  await page.goto("/people/20");
  await loginAsEditor(page);

  await expect(page.getByRole("button", { name: /Ada Editor/ })).toBeVisible();
  await expect(page.getByText("Person #20")).toBeVisible();

  await page.getByLabel(/Fullt navn/).fill("Ada Editor Oppdatert");
  await page.getByRole("button", { name: "Lagre person" }).click();

  await expect(page.getByRole("button", { name: /Ada Editor Oppdatert/ })).toBeVisible();
  await expect(page.getByText(/Sist lagret/)).toBeVisible();

  await page.locator(".contact-create input[placeholder*='verdi']").fill("ada.ny@example.com");
  await page.getByRole("button", { name: "Legg til kontakt" }).click();

  await expect(page.getByText("EMAIL · ada.ny@example.com")).toBeVisible();

  const inlineContactInput = page.locator(".contact-inline-input").first();
  await inlineContactInput.fill("ada.updated@example.com");
  await inlineContactInput.blur();

  await expect(page.getByText("EMAIL · ada.updated@example.com")).toBeVisible();
});
