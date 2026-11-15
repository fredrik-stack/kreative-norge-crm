import { expect, test } from "@playwright/test";
import { loginAsEditor, setupMockEditorApi } from "./mockEditorApi";

for (const kind of ["organizations", "persons"] as const) {
  test(`${kind}: regular and internal tags search separately even with equal IDs/names/slugs`, async ({ page }) => {
    const state = await setupMockEditorApi(page);
    const regular = state.tags[0];
    const internal = { id: regular.id, name: regular.name, slug: regular.slug };
    const unique = { id: regular.id + 1, name: "Oppfølging", slug: "oppfolging" };
    const source = kind === "organizations" ? state.organizations[0] : state.persons[0];
    source.tags = [regular];
    const privateProfile = { ...source, id: source.id + 1, tags: [], internal_tags: [internal, unique] };
    if (kind === "organizations") state.organizations = [state.organizations[0], { ...state.organizations[0], ...privateProfile, name: "Privat treff" }];
    else state.persons = [state.persons[0], { ...state.persons[0], ...privateProfile, full_name: "Privat treff" }];
    await page.route("**/api/tenants/1/internal-tags/", route => route.fulfill({ json: [internal, unique, { id: 999, name: "Ubrukt intern", slug: "ubrukt" }] }));
    const writes: string[] = [];
    page.on("request", request => { if (["POST", "PATCH", "PUT", "DELETE"].includes(request.method()) && request.url().includes("/api/tenants/")) writes.push(request.url()); });
    await page.goto(kind === "organizations" ? "/organizations" : "/people");
    await loginAsEditor(page);
    const input = page.getByRole("textbox", { name: "Søk tag", exact: true });
    await input.fill(regular.name);
    const choices = page.getByRole("listbox", { name: "Tag-forslag" });
    const privateChoice = choices.getByRole("button", { name: `${regular.name} Intern tag`, exact: true });
    await expect(privateChoice.locator(".internal-tag")).toHaveCSS("background-color", "rgb(200, 250, 0)");
    await expect(privateChoice.locator(".internal-tag")).toHaveCSS("color", "rgb(0, 0, 0)");
    await input.press("Tab");
    await expect(privateChoice).toBeFocused();
    await page.keyboard.press("Enter");
    const results = page.locator(kind === "organizations" ? ".editor-card-grid article" : ".person-results tbody tr");
    await expect(results).toHaveCount(1);
    await expect(results).toContainText("Privat treff");
    await expect(page.locator(".filter-summary").first()).toContainText(`intern tag «${regular.name}»`);
    // Editing an existing choice must preserve typing and resolve unique exact names.
    await input.fill("Oppfølging");
    await expect(input).toHaveValue("Oppfølging");
    await expect(results).toHaveCount(1);
    await expect(results).toContainText("Privat treff");
    await input.fill(regular.name);
    await choices.getByRole("button", { name: `${regular.name} Tag`, exact: true }).click();
    await expect(results).toHaveCount(1);
    await expect(results).not.toContainText("Privat treff");
    await input.fill("Ubrukt intern");
    await expect(results).toHaveCount(0);
    await page.getByRole("button", { name: "Nullstill filtre", exact: true }).click();
    await expect(input).toHaveValue("");
    await expect(results).toHaveCount(kind === "organizations" ? 2 : 0);
    expect(writes).toEqual([]);
  });
}

for (const status of [200, 403]) test(`late private catalog ${status} cannot block loading, cross tenant or expire the session`, async ({ page }) => {
  const state = await setupMockEditorApi(page);
  state.tenants.push({ ...state.tenants[0], id: 2, name: "Andre kontor", slug: "andre" });
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  let started = false;
  await page.route("**/api/tenants/1/internal-tags/", async route => {
    started = true; await gate;
    await route.fulfill({ status, json: status === 200 ? [{ id: 999, name: "Forsinket privat", slug: "forsinket" }] : { detail: "Synthetic forbidden" } });
  });
  for (const [path, data] of Object.entries({ organizations: [{ ...state.organizations[0], id: 90, tenant: 2, name: "Andre aktør" }], persons: [], tags: [], "organization-people": [], "internal-tags": [] })) {
    await page.route(`**/api/tenants/2/${path}/`, route => route.fulfill({ json: data }));
  }
  await page.goto("/organizations"); await loginAsEditor(page);
  await expect(page.getByRole("button", { name: state.organizations[0].name, exact: true })).toBeVisible();
  await expect.poll(() => started).toBe(true);
  await page.getByLabel("Aktivt Musikkontor").selectOption("2");
  await expect(page.getByRole("button", { name: "Andre aktør", exact: true })).toBeVisible();
  const oldResponse = page.waitForResponse(response => response.url().endsWith("/api/tenants/1/internal-tags/"));
  release();
  await (await oldResponse).finished();
  const input = page.getByRole("textbox", { name: "Søk tag", exact: true });
  await expect(input).toHaveValue("");
  await input.fill("Forsinket privat");
  await expect(page.getByRole("listbox", { name: "Tag-forslag" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Andre aktør", exact: true })).toBeVisible();
});

test("failed private catalog retains authorized profile suggestions and regular search", async ({ page }) => {
  const state = await setupMockEditorApi(page);
  state.organizations[0].internal_tags = [{ id: 999, name: "Fra profil", slug: "fra-profil" }];
  state.organizations[0].tags = [state.tags[0]];
  await page.route("**/api/tenants/1/internal-tags/", route => route.fulfill({ status: 503, json: { detail: "Synthetic unavailable" } }));
  await page.goto("/organizations"); await loginAsEditor(page);
  const input = page.getByRole("textbox", { name: "Søk tag", exact: true });
  await input.fill("Fra profil");
  await expect(page.locator(".editor-card-grid article")).toHaveCount(1);
  await expect(page.locator(".filter-summary").first()).toContainText("intern tag «Fra profil»");
  await input.fill(state.tags[0].name);
  await expect(page.locator(".filter-summary").first()).toContainText(`tag «${state.tags[0].name}»`);
});

for (const explicit of [false, true]) {
  test(`late same-name catalog rechecks automatic choice but preserves explicit=${explicit}`, async ({ page }) => {
    const state = await setupMockEditorApi(page);
    state.organizations[0].tags = [state.tags[0]];
    state.organizations.push({ ...state.organizations[0], id: 11, name: "Uten tagg", tags: [] });
    let release!: () => void;
    const gate = new Promise<void>(resolve => { release = resolve; });
    await page.route("**/api/tenants/1/internal-tags/", async route => {
      await gate;
      await route.fulfill({ json: [{ id: state.tags[0].id, name: state.tags[0].name, slug: state.tags[0].slug }] });
    });
    await page.goto("/organizations"); await loginAsEditor(page);
    const input = page.getByRole("textbox", { name: "Søk tag", exact: true });
    await input.fill(state.tags[0].name);
    const rows = page.locator(".editor-card-grid article");
    await expect(rows).toHaveCount(1);
    if (explicit) await page.getByRole("listbox", { name: "Tag-forslag" })
      .getByRole("button", { name: `${state.tags[0].name} Tag`, exact: true }).click();
    const response = page.waitForResponse(value => value.url().endsWith("/api/tenants/1/internal-tags/"));
    release(); await (await response).finished();
    await input.blur();
    await input.focus();
    await expect(page.getByRole("listbox", { name: "Tag-forslag" }).getByRole("button")).toHaveCount(2);
    await expect(rows).toHaveCount(explicit ? 1 : 2);
    if (!explicit) await expect(page.locator(".filter-summary")).toHaveCount(0);
  });
}

test("optional catalog permission denial preserves the mounted unsaved actor draft", async ({ page }) => {
  const state = await setupMockEditorApi(page);
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/api/tenants/1/internal-tags/", async route => {
    await gate; await route.fulfill({ status: 403, json: { detail: "Synthetic private permission denied" } });
  });
  await page.goto(`/organizations/${state.organizations[0].id}`); await loginAsEditor(page);
  const name = page.getByRole("textbox", { name: "Navn *", exact: true });
  await name.fill("Ulagret syntetisk utkast");
  const response = page.waitForResponse(value => value.url().endsWith("/api/tenants/1/internal-tags/"));
  release(); await (await response).finished();
  await expect(name).toHaveValue("Ulagret syntetisk utkast");
  await expect(page.getByRole("heading", { name: "Logg inn", exact: true })).toHaveCount(0);
  await expect(page.getByRole("status").first()).toContainText("Ulagrede profilfelt");
});
