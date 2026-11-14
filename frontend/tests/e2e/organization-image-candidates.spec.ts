import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { loginAsEditor, setupMockEditorApi } from "./mockEditorApi";

test("legacy candidates are listed without network preview until explicit selection", async ({ page }) => {
  const state = await setupMockEditorApi(page);
  state.organizations[0].image_asset_feature_enabled = true;
  let previewRequests = 0;
  await page.route("**/api/tenants/1/organizations/10/images/state/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ brave_search_enabled: true, expected_revision: 0, active_selection: null }),
    });
  });
  await page.route("**/api/tenants/1/organizations/10/images/legacy-candidates/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        candidates: [{
          candidate_ref: "signed-legacy-ref",
          source_type: "open_graph",
          source_label: "Tidligere Open Graph-bilde",
          source_domain: "legacy.example",
          source_title: null,
          source_publisher: null,
          source_key: "og_image_url",
          provider: "legacy_database",
          width: null,
          height: null,
          technical_status: "ready_for_preview",
        }],
      }),
    });
  });
  await page.route("**/api/tenants/1/organizations/10/images/candidate-preview/", async (route) => {
    previewRequests += 1;
    expect(route.request().postDataJSON()).toEqual({
      candidate_ref: "signed-legacy-ref",
      original: true,
    });
    await route.fulfill({ status: 200, contentType: "image/webp", body: "legacy-preview" });
  });

  await page.goto("/organizations");
  await loginAsEditor(page);
  await page.locator(".editor-card-grid").getByRole("button", { name: "Kreativ Demo AS" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Rediger" }).click();
  await page.locator("summary").filter({hasText:"Endre bilde"}).click();
  await expect(page.getByText("Tidligere lagrede bilder")).toBeVisible();
  await expect(page.getByText("Åpne for å se bildet")).toBeVisible();
  expect(previewRequests).toBe(0);
  await page.getByRole("button", { name: /Tidligere Open Graph-bilde/ }).click();
  await expect.poll(() => previewRequests).toBe(1);
});

for (const published of [true, false]) {
test(`official candidate confirms once for ${published ? "published" : "unpublished"} actor`, async ({ page }) => {
  const state = await setupMockEditorApi(page);
  state.organizations[0].image_asset_feature_enabled = true;
  state.organizations[0].is_published = published;
  let activeRevision = 0;
  let released = false;
  const imageBody = readFileSync(new URL("../fixtures/editor-image-synthetic.png", import.meta.url));
  const imageUrl = published ? "/synthetic-public-image.png" : "/api/tenants/1/organizations/10/images/active-preview/1/square/";
  await page.route(`**${imageUrl}`, route => route.fulfill({status: 200, contentType: "image/png", body: imageBody}));
  await page.route("**/api/tenants/1/organizations/10/images/complete/", async route => {
    expect(route.request().postDataJSON()).toEqual({expected_revision: 1, confirmed: true});
    released = true;
    state.organizations[0].preview_image_url = imageUrl;
    await route.fulfill({status: 200, contentType: "application/json", body: JSON.stringify({release_id:"synthetic-release",revision:1})});
  });

  await page.route("**/api/tenants/1/organizations/10/images/state/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        brave_search_enabled: true,
        image_use: {pending: activeRevision > 0 && !released, ready: released},
        editor_preview_image_url: released ? imageUrl : null,
        expected_revision: activeRevision,
        public_image: {enabled:true, kind: released && published ? "asset" : "system_fallback", reason: !published ? "organization_unpublished" : released ? "asset" : "release_missing",
          image: released && published ? {kind:"asset",alt_text:"Syntetisk bilde",credit:"Fotograf",square:{url:imageUrl,width:512,height:512},landscape:{url:imageUrl,width:800,height:450},share:{url:imageUrl,width:1200,height:630}} : null},
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
    await route.fulfill({ status: 200, contentType: "image/png", body: imageBody });
  });
  await page.route("**/api/tenants/1/organizations/10/images/process/", async (route) => {
    const payload = route.request().postDataJSON();
    expect(payload).toMatchObject({
      candidate_ref: "signed-candidate-ref",
      image_kind: "photo",
      focus_x: 0.5,
      focus_y: 0.5,
      zoom: 0.5,
    });
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
    await route.fulfill({ status: 200, contentType: "image/png", body: imageBody });
  });
  await page.route("**/api/tenants/1/organizations/10/images/approve/", async (route) => {
    const payload = route.request().postDataJSON();
    expect(payload).toEqual({
      rights_confirmed: true,
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
  await page.locator(".editor-card-grid").getByRole("button", { name: "Kreativ Demo AS" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Rediger" }).click();
  await page.locator("summary").filter({hasText:"Endre bilde"}).click();
  await expect(page.getByRole("heading", { name: "Aktørbilde" })).toBeVisible();
  await page.getByRole("button", { name: "Finn bilder" }).click();
  await expect(page.getByText("official.example")).toBeVisible();
  await page.getByRole("button", { name: /Open Graph/ }).click();
  await page.getByText("Finjuster utsnitt").click();
  await page.getByRole("slider",{name:"Zoom",exact:true}).fill("0.5");
  await expect(page.getByText("Zoom: 50 %")).toBeVisible();
  await expect(page.locator('.image-live-crop-frame.square')).toHaveCSS('background-color','rgb(255, 255, 255)');
  await page.getByLabel('Live crop-preview').screenshot({path:test.info().outputPath('00-zoom-out-white.png')});
  await page.getByRole("button", { name: "Prosesser valgt bilde" }).click();
  await expect(page.getByLabel("Serverens bildeformater").getByRole("img")).toHaveCount(3);
  await page.getByLabel(/Alt-tekst/).fill("Offisielt bilde av Kreativ Demo AS");
  await page.getByLabel("Offentlig kreditering (valgfritt)").fill("Fotograf");
  await page.getByRole("checkbox", {name: /Jeg bekrefter/}).check();
  await page.getByRole("button", { name: "Bekreft og bruk bildet" }).click();
  await expect(page.getByText("Godkjent aktørbilde")).toBeVisible();
  await expect(page.getByText("Revisjon 1")).toBeVisible();
  await expect(page.getByText(published ? "Bildet er bekreftet og brukes for aktøren i Editor CRM og PUBLIC." : "Bildet er bekreftet. Det blir offentlig når du publiserer aktøren.")).toBeVisible();
  await expect(page.getByRole("button", {name:"Ta bildet i bruk på PUBLIC"})).toHaveCount(0);
  await expect(page.getByRole("button", {name:"Bruk standardbilde i stedet"})).toHaveCount(0);
  await expect(page.locator('.profile-image-entry img').first()).toHaveAttribute('src', imageUrl);
  await page.locator('.organization-image-panel').screenshot({path:test.info().outputPath("01-one-confirmation.png")});
  await page.locator("summary").filter({hasText:/^Forhåndsvisning/}).click();
  await expect(page.getByRole("heading", { name: "Public Preview (legacy)" })).toBeVisible();
  await page.getByRole("link", {name:"Aktører",exact:true}).click();
  await expect(page.locator(`.editor-card-grid img[src="${imageUrl}"]`)).toBeVisible();
  await page.locator(".editor-card-grid").getByRole("button", {name:"Kreativ Demo AS"}).click();
  await expect(page.getByRole("dialog").locator(`img[src="${imageUrl}"]`)).toBeVisible();
  await page.getByRole("dialog").screenshot({path: test.info().outputPath("03-editor-card-detail.png")});
});
}

test("direct URL can be previewed, cropped live, processed, and approved with blank alt text", async ({ page }) => {
  const state = await setupMockEditorApi(page);
  state.organizations[0].image_asset_feature_enabled = true;
  let activeRevision = 0;
  const imageBody = readFileSync("tests/fixtures/editor-image-synthetic.png");

  await page.route("**/api/tenants/1/organizations/10/images/state/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        brave_search_enabled: true,
        expected_revision: activeRevision,
        active_selection: activeRevision
          ? {
              id: 2,
              revision: activeRevision,
              status: "active",
              kind: "asset",
              alt_text: "",
              public_credit: "",
              rendition_preview_ref: "active-url-preview-ref",
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
      body: JSON.stringify({ candidates: [] }),
    });
  });
  await page.route("**/api/tenants/1/organizations/10/images/url-candidate/", async (route) => {
    expect(route.request().postDataJSON()).toEqual({ image_url: "https://images.example/scene.png" });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        candidate: {
          candidate_ref: "signed-url-candidate-ref",
          source_type: "pasted_url",
          source_label: "Direkte bilde-URL",
          source_domain: "images.example",
          source_title: null,
          source_publisher: null,
          provider: "pasted_url",
          width: 1600,
          height: 1000,
          technical_status: "ready_for_preview",
        },
      }),
    });
  });
  await page.route("**/api/tenants/1/organizations/10/images/candidate-preview/", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      candidate_ref: "signed-url-candidate-ref",
      original: true,
    });
    await route.fulfill({ status: 200, contentType: "image/png", body: imageBody });
  });
  await page.route("**/api/tenants/1/organizations/10/images/process/", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      candidate_ref: "signed-url-candidate-ref",
      image_kind: "photo",
      focus_x: 0.37,
      focus_y: 0.68,
      zoom: 1.75,
    });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        approval_ref: "signed-url-approval-ref",
        rendition_preview_ref: "signed-url-preview-ref",
        asset_id: 2,
        rendition_set_id: 3,
        variants: ["square", "landscape", "share"],
        warnings: [],
        status: "created",
      }),
    });
  });
  await page.route("**/api/tenants/1/organizations/10/images/rendition-preview/", async (route) => {
    await route.fulfill({ status: 200, contentType: "image/png", body: imageBody });
  });
  await page.route("**/api/tenants/1/organizations/10/images/approve/", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      rights_confirmed: true,
      approval_ref: "signed-url-approval-ref",
      expected_revision: 0,
      alt_text: "",
      public_credit: "",
    });
    activeRevision = 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ selection_id: 2, revision: 1, status: "active", event_id: 2 }),
    });
  });

  await page.goto("/organizations");
  await loginAsEditor(page);
  await page.locator(".editor-card-grid").getByRole("button", { name: "Kreativ Demo AS" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Rediger" }).click();
  await page.locator("summary").filter({hasText:"Endre bilde"}).click();
  await page.getByRole("button", { name: "Finn bilder" }).click();
  await page.getByRole("button", { name: "Lim inn bilde-URL" }).click();
  await page.getByRole("textbox", { name: "Direkte bilde-URL" }).fill("https://images.example/scene.png");
  await page.getByRole("button", { name: "Hent bilde" }).click();

  const candidate = page.getByRole("button", { name: /Direkte bilde-URL.*images\.example/ });
  await expect(candidate).toBeVisible();
  await expect(page.getByRole("button", { name: "Prosesser valgt bilde" })).toHaveCount(0);
  await candidate.click();
  await expect(page.getByLabel("Live crop-preview").getByRole("img")).toHaveCount(3);
  await page.getByRole("group", { name: "Horisontalt" }).getByRole("button", { name: "Høyre" }).click();
  await page.getByRole("group", { name: "Vertikalt" }).getByRole("button", { name: "Bunn" }).click();
  await page.getByText("Finjuster utsnitt").click();
  await page.getByLabel("Horisontal plassering").fill("0.37");
  await page.getByLabel("Vertikal plassering").fill("0.68");
  await page.getByLabel("Zoom").fill("1.75");
  await expect(page.getByText("Zoom: 175 %")).toBeVisible();
  await page.getByLabel("Zoom").fill("1");
  await expect(page.getByText("Zoom: 100 %")).toBeVisible();
  await page.getByLabel("Zoom").fill("1.75");

  await page.getByRole("button", { name: "Prosesser valgt bilde" }).click();
  await expect(page.getByRole("textbox", { name: /Alt-tekst \(valgfritt\)/ })).toHaveValue("");
  await page.getByRole("checkbox", {name: /Jeg bekrefter/}).check();
  await page.getByRole("button", { name: "Bekreft og bruk bildet" }).click();
  await expect(page.getByText("Godkjent aktørbilde")).toBeVisible();
  await page.locator(".image-current-picture").evaluate(node => { (node as HTMLDetailsElement).open = true; });
  await expect(page.getByText("Ingen alt-tekst")).toBeVisible();
});

test("local upload can be processed as a complete uncropped logo without changing PUBLIC fields", async ({ page }) => {
  const state = await setupMockEditorApi(page);
  state.organizations[0].image_asset_feature_enabled = true;
  let activeRevision = 8;
  const imageBody = readFileSync("tests/fixtures/editor-image-synthetic.png");

  await page.route("**/api/tenants/1/organizations/10/images/state/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        brave_search_enabled: true,
        expected_revision: activeRevision,
        active_selection: activeRevision
          ? {
              id: 3,
              revision: activeRevision,
              status: "active",
              kind: "asset",
              alt_text: "",
              public_credit: "",
              rendition_preview_ref: "active-upload-preview-ref",
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
      body: JSON.stringify({ candidates: [] }),
    });
  });
  await page.route("**/api/tenants/1/organizations/10/images/upload-process/", async (route) => {
    const contentType = route.request().headers()["content-type"];
    expect(contentType).toContain("multipart/form-data; boundary=");
    const requestBody = route.request().postDataBuffer();
    expect(requestBody).not.toBeNull();
    const multipart = requestBody!.toString("latin1");
    expect(multipart).toContain('name="file"; filename="upload.png"');
    expect(multipart).toContain("Content-Type: image/png");
    expect(multipart).toMatch(/name="image_kind"\r\n\r\nlogo/);
    expect(multipart).not.toContain('name="focus_x"');
    expect(multipart).not.toContain('name="focus_y"');
    expect(multipart).not.toContain('name="zoom"');
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        approval_ref: "signed-upload-approval-ref",
        rendition_preview_ref: "signed-upload-preview-ref",
        asset_id: 3,
        rendition_set_id: 4,
        variants: ["square", "landscape", "share"],
        warnings: [],
        status: "created",
      }),
    });
  });
  await page.route("**/api/tenants/1/organizations/10/images/rendition-preview/", async (route) => {
    await route.fulfill({ status: 200, contentType: "image/png", body: imageBody });
  });
  await page.route("**/api/tenants/1/organizations/10/images/approve/", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      rights_confirmed: true,
      approval_ref: "signed-upload-approval-ref",
      expected_revision: 8,
      alt_text: "",
      public_credit: "",
    });
    activeRevision = 9;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ selection_id: 3, revision: 9, status: "active", event_id: 3 }),
    });
  });

  await page.goto("/organizations");
  await loginAsEditor(page);
  await page.locator(".editor-card-grid").getByRole("button", { name: "Kreativ Demo AS" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Rediger" }).click();
  await page.locator("summary").filter({hasText:"Endre bilde"}).click();
  await expect(page.getByText("Revisjon 8", {exact: true})).toBeVisible();
  for (const name of ["Finn bilder", "Søk etter flere bilder", "Lim inn bilde-URL", "Last opp bilde"]) {
    await expect(page.getByRole("button", {name, exact: true})).toBeEnabled();
  }
  await page.getByRole("button", { name: "Last opp bilde" }).click();
  if (process.env.IMAGE_UX_EVIDENCE_DIR) {
    await page.getByLabel("Opplastingsområde").scrollIntoViewIfNeeded();
    await page.screenshot({path: `${process.env.IMAGE_UX_EVIDENCE_DIR}/replace-drop.png`});
  }
  const drop = await page.evaluateHandle((bytes) => {
    const transfer = new DataTransfer();
    transfer.items.add(new File([new Uint8Array(bytes)], "upload.png", {type: "image/png"}));
    return transfer;
  }, [...imageBody]);
  await page.getByLabel("Opplastingsområde").dispatchEvent("drop", {dataTransfer: drop});

  const uploadCandidate = page.getByRole("button", { name: /Lastet opp.*upload\.png/ });
  await expect(uploadCandidate).toBeVisible();
  await expect(page.getByRole("button", { name: "Prosesser valgt bilde" })).toBeEnabled();
  await uploadCandidate.click();
  await expect(page.getByLabel("Live crop-preview").getByRole("img")).toHaveCount(3);
  await page.getByLabel("Bildetype").selectOption("logo");
  await expect(page.getByText("Logo vises uten beskjæring.")).toBeVisible();
  await expect(page.getByRole("img", { name: "Forhåndsvisning av hele logoen" })).toBeVisible();
  await expect(page.getByText("Finjuster utsnitt")).toHaveCount(0);
  await expect(page.getByLabel("Zoom")).toHaveCount(0);
  await page.getByRole("button", { name: "Prosesser valgt bilde" }).click();
  await expect(page.getByRole("textbox", { name: /Alt-tekst \(valgfritt\)/ })).toHaveValue("");
  await page.getByRole("checkbox", {name: /Jeg bekrefter/}).check();
  await page.getByRole("button", { name: "Bekreft og erstatt bildet" }).click();

  await expect(page.getByText("Godkjent aktørbilde")).toBeVisible();
  await expect(page.getByText("Revisjon 9", {exact: true})).toBeVisible();
  await page.locator(".image-current-picture summary").click();
  await page.locator(".image-current-picture").evaluate(node => { (node as HTMLDetailsElement).open = true; });
  await expect(page.getByText("Ingen alt-tekst")).toBeVisible();
  await page.locator("summary").filter({hasText:/^Forhåndsvisning/}).click();
  await expect(page.getByRole("heading", { name: "Public Preview (legacy)" })).toBeVisible();
  expect(state.organizations[0].is_published).toBe(true);
  expect(state.organizations[0].og_image_url).toBeNull();
});

test("Brave search is mocked with exact manual query, first result focus, private preview, and processing", async ({ page }) => {
  await page.setViewportSize({width: 1440, height: 900});
  const state = await setupMockEditorApi(page);
  state.organizations[0].image_asset_feature_enabled = true;
  const imageBody = readFileSync("tests/fixtures/editor-image-synthetic.png");

  await page.route("**/api/tenants/1/organizations/10/images/state/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ brave_search_enabled: true, expected_revision: 0, active_selection: null }),
    });
  });
  await page.route("**/api/tenants/1/organizations/10/images/discover/", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ candidates: [] }) });
  });
  await page.route("**/api/tenants/1/organizations/10/images/search-context/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        suggested_query: "Kreativ Demo AS Oslo",
        query_sources: ["organization_name", "municipality"],
        municipalities: ["Oslo"],
        categories: [{ id: 1, name: "Musikk" }],
        people: [{ id: 2, name: "Ada Editor" }],
      }),
    });
  });
  await page.route("**/api/tenants/1/organizations/10/images/brave-search/", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      query: "Festspillene Helgeland logo",
      municipality: null,
      category_id: null,
      person_id: null,
      query_edited: true,
    });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        search_query: "Festspillene Helgeland logo",
        query_sources: ["manual_edit"],
        candidates: [{
          candidate_ref: "signed-brave-ref",
          source_type: "brave_image_search",
          source_label: "Bildesøk",
          source_domain: "publisher.example",
          source_title: "Festspillene Helgeland",
          source_publisher: "Eksempelavisen",
          provider: "brave_image_search",
          width: 1800,
          height: 1200,
          technical_status: "ready_for_preview",
        }],
      }),
    });
  });
  await page.route("**/api/tenants/1/organizations/10/images/candidate-preview/", async (route) => {
    const payload = route.request().postDataJSON();
    expect(payload.candidate_ref).toBe("signed-brave-ref");
    await route.fulfill({ status: 200, contentType: "image/png", body: imageBody });
  });
  await page.route("**/api/tenants/1/organizations/10/images/process/", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      candidate_ref: "signed-brave-ref",
      image_kind: "photo",
      focus_x: 0.5,
      focus_y: 0.5,
      zoom: 1,
    });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        approval_ref: "signed-brave-approval-ref",
        rendition_preview_ref: "signed-brave-preview-ref",
        asset_id: 4,
        rendition_set_id: 5,
        variants: ["square", "landscape", "share"],
        warnings: [],
        status: "created",
      }),
    });
  });
  await page.route("**/api/tenants/1/organizations/10/images/rendition-preview/", async (route) => {
    await route.fulfill({ status: 200, contentType: "image/png", body: imageBody });
  });

  await page.goto("/organizations");
  await loginAsEditor(page);
  await page.locator(".editor-card-grid").getByRole("button", { name: "Kreativ Demo AS" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Rediger" }).click();
  await page.locator("summary").filter({hasText:"Endre bilde"}).click();
  await page.getByRole("button", { name: "Finn bilder" }).click();
  await page.getByRole("button", { name: "Søk etter flere bilder" }).click();
  await expect(page.getByText(/Søket sendes til Brave/)).toHaveCount(0);
  const query = page.getByLabel("Forslått søk");
  await expect(query).toHaveValue("Kreativ Demo AS Oslo");
  if (process.env.IMAGE_UX_EVIDENCE_DIR) {
    await page.getByLabel("Bildesøk").scrollIntoViewIfNeeded();
    await page.screenshot({path: `${process.env.IMAGE_UX_EVIDENCE_DIR}/search-form.png`});
  }
  await query.fill("Festspillene Helgeland logo");
  await page.getByRole("button", { name: "Nytt søk", exact: true }).click();
  const firstResult = page.locator('[data-brave-result-index="0"]');
  await expect(firstResult).toBeFocused();
  await expect(firstResult).toBeInViewport({ratio: 0.9});
  await expect(page.getByText("Eksempelavisen · publisher.example")).toBeVisible();
  await expect(firstResult.locator("img")).toHaveJSProperty("complete", true);
  await expect(firstResult.locator("img")).toHaveJSProperty("naturalWidth", 1600);
  if (process.env.IMAGE_UX_EVIDENCE_DIR) await page.screenshot({path: `${process.env.IMAGE_UX_EVIDENCE_DIR}/brave-results.png`});
  await expect(page.getByText("Kontroller at du har lov til å bruke bildet før du godkjenner.")).toHaveCount(1);
  await page.getByRole("button", { name: /Festspillene Helgeland/ }).click();
  await page.getByRole("button", { name: "Prosesser valgt bilde" }).click();
  await expect(page.getByLabel("Serverens bildeformater").getByRole("img")).toHaveCount(3);
  await page.locator("summary").filter({hasText:/^Forhåndsvisning/}).click();
  await expect(page.getByRole("heading", { name: "Public Preview (legacy)" })).toBeVisible();
});
