import { test, expect } from "@playwright/test";
import { loginAsEditor, setupMockEditorApi } from "./mockEditorApi";

test("login and show unsaved changes modal on internal navigation", async ({ page }) => {
  await setupMockEditorApi(page);

  await page.goto("/organizations/10");
  await loginAsEditor(page);

  await expect(page.getByLabel(/Navn/)).toHaveValue("Kreativ Demo AS");
  await page.getByLabel(/Navn/).fill("Kreativ Demo AS endret");
  await page.getByRole("link", { name: /Personer/ }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("Aktørskjema", { exact: true })).toBeVisible();
});
