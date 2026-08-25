import { test, expect } from "@playwright/test";
import { loginAsEditor, setupMockEditorApi } from "./mockEditorApi";

test("create organization and verify preview updates", async ({ page }) => {
  await setupMockEditorApi(page);

  await page.goto("/organizations");
  await loginAsEditor(page);

  await expect(page.getByRole("button", { name: "Ny aktør" })).toBeVisible();
  await page.getByRole("button", { name: "Ny aktør" }).click();

  await page.getByLabel(/Navn/).fill("Ny Kulturaktør");
  await page.getByLabel("Org.nr").fill("987654321");
  await page.getByLabel("E-post").fill("kontakt@kultur.no");
  await page.getByRole("textbox", { name: "Telefon" }).fill("22 12 34 56");
  await expect(page.getByLabel("Land/region for telefonnummer")).toHaveValue("NO");
  await page.getByLabel("Kommune(r)").fill("Bergen");

  const preview = page.locator(".panel.preview");
  await expect(preview.getByRole("heading", { name: "Ny Kulturaktør" })).toBeVisible();
  await expect(preview.getByText("987654321")).toBeVisible();
  await expect(preview.getByText("kontakt@kultur.no")).toBeVisible();
  await expect(preview.getByText("Skjult")).toBeVisible();

  const createRequest = page.waitForRequest(
    (request) =>
      request.method() === "POST" && request.url().endsWith("/api/tenants/1/organizations/"),
  );
  await page.getByRole("button", { name: "Opprett aktør" }).click();
  expect((await createRequest).postDataJSON()).toMatchObject({
    phone: "22 12 34 56",
    phone_region: "NO",
  });

  await expect(page.getByLabel(/Navn/)).toHaveValue("Ny Kulturaktør");
  await expect(page.getByText(/Sist lagret/)).toBeVisible();
  await expect(page.locator(".panel.editor .editor-header h2")).toHaveText("Ny Kulturaktør");

  const organizationForm = page.locator(".panel.editor form").first();
  await organizationForm.getByRole("textbox", { name: "Telefon" }).fill("+4711111111");
  await expect(organizationForm.getByLabel("Land/region for telefonnummer")).toHaveValue("");
  await page.getByRole("checkbox", { name: /Publiser telefon/ }).check();
  await page.getByRole("button", { name: "Lagre endringer" }).click();

  await expect(preview.getByText("+4711111111")).toBeVisible();
  await expect(page.getByText(/Sist lagret/)).toBeVisible();
});
