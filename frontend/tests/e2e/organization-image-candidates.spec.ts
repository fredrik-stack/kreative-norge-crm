import { expect, test } from "@playwright/test";
import { loginAsEditor, setupMockEditorApi } from "./mockEditorApi";

test("official candidate can be processed, previewed, and explicitly locked", async ({ page }) => {
  const state = await setupMockEditorApi(page);
  state.organizations[0].image_asset_feature_enabled = true;
  let activeRevision = 0;

  await page.route("**/api/tenants/1/organizations/10/images/state/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        expected_revision: activeRevision,
        active_selection: activeRevision
          ? {
              id: 1,
              revision: activeRevision,
              status: "active",
              kind: "asset",
              alt_text: "Offisielt bilde av Kreativ Demo AS",
              public_credit: "Fotograf",
              rendition_preview_ref: "active-preview-ref",
              variants: ["square", "landscape", "share"],
            }
          : null,
      }),
    });
  });
  await page.route("**/api/tenants/1/organizations/10/images/discover/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        candidates: [
          {
            candidate_ref: "signed-candidate-ref",
            source_type: "open_graph",
            source_label: "Open Graph",
            source_domain: "official.example",
            provider: "official_website",
            width: 1400,
            height: 1000,
            technical_status: "ready_for_preview",
          },
        ],
      }),
    });
  });
  await page.route("**/api/tenants/1/organizations/10/images/candidate-preview/", async (route) => {
    await route.fulfill({ status: 200, contentType: "image/webp", body: "candidate-preview" });
  });
  await page.route("**/api/tenants/1/organizations/10/images/process/", async (route) => {
    const payload = route.request().postDataJSON();
    expect(payload).toMatchObject({ candidate_ref: "signed-candidate-ref", image_kind: "photo" });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        approval_ref: "signed-approval-ref",
        rendition_preview_ref: "signed-preview-ref",
        asset_id: 1,
        rendition_set_id: 2,
        variants: ["square", "landscape", "share"],
        warnings: ["untagged_assumed_srgb"],
        status: "created",
      }),
    });
  });
  await page.route("**/api/tenants/1/organizations/10/images/rendition-preview/", async (route) => {
    await route.fulfill({ status: 200, contentType: "image/webp", body: "rendition-preview" });
  });
  await page.route("**/api/tenants/1/organizations/10/images/approve/", async (route) => {
    const payload = route.request().postDataJSON();
    expect(payload).toEqual({
      approval_ref: "signed-approval-ref",
      expected_revision: 0,
      alt_text: "Offisielt bilde av Kreativ Demo AS",
      public_credit: "Fotograf",
    });
    activeRevision = 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ selection_id: 1, revision: 1, status: "active", event_id: 1 }),
    });
  });

  await page.goto("/organizations");
  await loginAsEditor(page);
  await page.getByRole("button", { name: "Rediger" }).click();
  await expect(page.getByRole("heading", { name: "Aktørbilde" })).toBeVisible();
  await page.getByRole("button", { name: "Finn bilder" }).click();
  await expect(page.getByText("official.example")).toBeVisible();
  await page.getByRole("button", { name: /Open Graph/ }).click();
  await page.getByRole("button", { name: "Prosesser valgt bilde" }).click();
  await expect(page.getByLabel("Intern processing-preview").getByRole("img")).toHaveCount(3);
  await page.getByLabel(/Alt-tekst/).fill("Offisielt bilde av Kreativ Demo AS");
  await page.getByLabel("Offentlig kreditering (valgfritt)").fill("Fotograf");
  await page.getByRole("button", { name: "Godkjenn og lås bilde" }).click();
  await expect(page.getByText("Aktivt låst bilde · revisjon 1")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Public Preview (legacy)" })).toBeVisible();
});
