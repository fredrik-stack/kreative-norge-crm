import { expect, test } from "@playwright/test";
import { loginAsEditor, setupMockEditorApi } from "./mockEditorApi";

for (const kind of ["organizations", "persons"] as const) {
  test(`${kind}: classification summary follows saved values and unsaved choices`, async ({ page }) => {
    const state = await setupMockEditorApi(page);
    state.subcategories[0].name = "Konsertarrangører";
    state.subcategories[0].slug = "konsertarrangorer";
    state.categories.push({ ...state.categories[0], id: 101, name: "Film", slug: "film" });
    const target = kind === "organizations" ? state.organizations[0] : state.persons[0];
    // Existing records can derive their main category from the subcategory.
    target.categories = [];
    target.subcategories = [state.subcategories[0]];
    target.tags = [state.tags[0]];
    target.internal_tags = [{ id: 800, name: "Syntetisk intern", slug: "syntetisk-intern" }];
    await page.goto(kind === "organizations" ? `/organizations/${target.id}` : `/people/${target.id}`);
    await loginAsEditor(page);
    const section = page.locator("details").filter({ has: page.locator("summary strong", { hasText: "Kategorisering og tags" }) });
    const summary = section.locator("summary small");
    await expect(summary).toHaveText("Kategori: Musikk · Underkategori: Konsertarrangører · Tags: Etablert · Interne tags: Syntetisk intern");
    const writes: string[] = [];
    page.on("request", request => {
      if (["POST", "PATCH", "PUT", "DELETE"].includes(request.method()) && request.url().includes(`/${kind}/`)) writes.push(request.url());
    });
    await section.locator("summary").click();
    await section.getByRole("combobox", { name: "Hovedkategori", exact: true }).selectOption("101");
    await section.getByRole("textbox", { name: "Tags", exact: true }).fill("Ny tagg");
    await section.getByRole("textbox", { name: "Interne tags", exact: true }).fill("Ny intern");
    await section.locator("summary").click();
    await expect(summary).toHaveText("Kategori: Film · Tags: Ny tagg · Interne tags: Ny intern");
    await section.locator("summary").click();
    await section.getByRole("combobox", { name: "Hovedkategori", exact: true }).selectOption("");
    await section.getByRole("textbox", { name: "Tags", exact: true }).fill("   ");
    await section.getByRole("textbox", { name: "Interne tags", exact: true }).fill("");
    await expect(summary).toHaveText("Ingen kategorier eller tags valgt");
    expect(writes).toEqual([]);
  });
}
