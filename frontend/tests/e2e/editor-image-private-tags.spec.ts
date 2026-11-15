import { expect, test } from "@playwright/test";
import { loginAsEditor, setupMockEditorApi } from "./mockEditorApi";

for (const kind of ["organizations", "persons"] as const) {
  test(`${kind}: private tags hydrate and save with the profile in yellow`, async ({page}) => {
    await page.setViewportSize({width: 1440, height: 1000});
    const state = await setupMockEditorApi(page);
    const target = kind === "organizations" ? state.organizations[0] : state.persons[0];
    target.internal_tags = [{id: 800, name: "Syntetisk intern", slug: "syntetisk-intern"}];
    await page.route("**/api/tenants/1/internal-tags/", route => route.fulfill({status: 200, contentType: "application/json", body: JSON.stringify(target.internal_tags)}));
    await page.route(`**/api/tenants/1/${kind}/${target.id}/`, async route => {
      if (route.request().method() === "PATCH") {
        const payload = route.request().postDataJSON();
        if (payload.internal_tag_names) target.internal_tags = payload.internal_tag_names.map((name: string, index: number) => ({id: 900+index, name, slug: `private-${index}`}));
        Object.assign(target, Object.fromEntries(Object.entries(payload).filter(([key]) => key !== "internal_tag_names")));
      }
      await route.fulfill({status: 200, contentType: "application/json", body: JSON.stringify(target)});
    });
    await page.goto(kind === "organizations" ? `/organizations/${target.id}` : `/people/${target.id}`);
    await loginAsEditor(page);
    await page.locator("summary").filter({hasText: "Kategorisering og tags"}).click();
    const input = page.getByRole("textbox", {name: "Interne tags", exact: true});
    await expect(input).toHaveValue("Syntetisk intern");
    await input.fill("Syntetisk intern, Ny privat");
    const chip = page.getByLabel("Valgte interne tags").getByText("Ny privat", {exact: true});
    await expect(chip).toHaveCSS("background-color", "rgb(200, 250, 0)");
    await expect(chip).toHaveCSS("color", "rgb(0, 0, 0)");
    const write = page.waitForRequest(request => request.method() === "PATCH" && request.url().endsWith(`/${kind}/${target.id}/`));
    await page.getByRole("button", {name: kind === "organizations" ? "Lagre aktør" : "Lagre person", exact: true}).first().click();
    expect((await write).postDataJSON().internal_tag_names).toEqual(["Syntetisk intern", "Ny privat"]);
    await expect(page.getByText(kind === "organizations" ? "Aktørskjema lagret" : "Personskjema lagret", {exact: true}).first()).toBeVisible();
    if (process.env.EDITOR_REFINEMENTS_EVIDENCE_DIR) {
      await input.scrollIntoViewIfNeeded();
      await input.locator("xpath=ancestor::details[1]").screenshot({path: `${process.env.EDITOR_REFINEMENTS_EVIDENCE_DIR}/${kind}-private-tags.png`});
    }
  });
}

test("an actor without an approved image shows its name inside the thumbnail", async ({page}) => {
  const state = await setupMockEditorApi(page);
  state.organizations[0].preview_image_kind = "system_fallback";
  state.organizations[0].preview_image_url = "/static/generic-fallback.png";
  await page.goto("/organizations"); await loginAsEditor(page);
  const fallback = page.locator(".editor-card-grid .editor-card-thumb-fallback").first();
  await expect(fallback).toHaveText(state.organizations[0].name);
  await expect(fallback.locator("img")).toHaveCount(0);
  if (process.env.EDITOR_REFINEMENTS_EVIDENCE_DIR) await page.screenshot({path: `${process.env.EDITOR_REFINEMENTS_EVIDENCE_DIR}/named-thumbnail.png`});
});
