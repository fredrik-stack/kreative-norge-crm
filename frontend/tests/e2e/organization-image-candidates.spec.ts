import { expect, test } from "@playwright/test";
import { loginAsEditor, setupMockEditorApi } from "./mockEditorApi";

test("legacy candidates are listed without network preview until explicit selection", async ({ page }) => {
  const state = await setupMockEditorApi(page);
  state.organizations[0].image_asset_feature_enabled = true;
  let previewRequests = 0;
  await page.route("**/api/tenants/1/organizations/10/images/state/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ expected_revision: 0, active_selection: null }),
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
  await page.getByRole("button", { name: "Rediger" }).click();
  await expect(page.getByText("Tidligere lagrede bilder")).toBeVisible();
  await expect(page.getByText("Ingen automatisk forhåndshenting")).toBeVisible();
  expect(previewRequests).toBe(0);
  await page.getByRole("button", { name: /Tidligere Open Graph-bilde/ }).click();
  await expect.poll(() => previewRequests).toBe(1);
});

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
    expect(payload).toMatchObject({
      candidate_ref: "signed-candidate-ref",
      image_kind: "photo",
      focus_x: 0.5,
      focus_y: 0.5,
      zoom: 1,
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
  await expect(page.getByLabel("Serverens bildeformater").getByRole("img")).toHaveCount(3);
  await page.getByLabel(/Alt-tekst/).fill("Offisielt bilde av Kreativ Demo AS");
  await page.getByLabel("Offentlig kreditering (valgfritt)").fill("Fotograf");
  await page.getByRole("button", { name: "Godkjenn og lås bilde" }).click();
  await expect(page.getByText("Aktivt bilde")).toBeVisible();
  await expect(page.getByText("Revisjon 1")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Public Preview (legacy)" })).toBeVisible();
});

test("direct URL can be previewed, cropped live, processed, and approved with blank alt text", async ({ page }) => {
  const state = await setupMockEditorApi(page);
  state.organizations[0].image_asset_feature_enabled = true;
  let activeRevision = 0;
  const imageBody = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAQAAABp8Z5+AAAADklEQVR42mNk+M8AAQADAgEAff9qAAAAAElFTkSuQmCC",
    "base64",
  );

  await page.route("**/api/tenants/1/organizations/10/images/state/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
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
  await page.getByRole("button", { name: "Rediger" }).click();
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
  await page.getByRole("button", { name: "Godkjenn og lås bilde" }).click();
  await expect(page.getByText("Aktivt bilde")).toBeVisible();
  await expect(page.getByText("Ingen alt-tekst")).toBeVisible();
});

test("local upload can be processed as a complete uncropped logo without changing PUBLIC fields", async ({ page }) => {
  const state = await setupMockEditorApi(page);
  state.organizations[0].image_asset_feature_enabled = true;
  let activeRevision = 0;
  const imageBody = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAQAAABp8Z5+AAAADklEQVR42mNk+M8AAQADAgEAff9qAAAAAElFTkSuQmCC",
    "base64",
  );

  await page.route("**/api/tenants/1/organizations/10/images/state/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
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
      approval_ref: "signed-upload-approval-ref",
      expected_revision: 0,
      alt_text: "",
      public_credit: "",
    });
    activeRevision = 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ selection_id: 3, revision: 1, status: "active", event_id: 3 }),
    });
  });

  await page.goto("/organizations");
  await loginAsEditor(page);
  await page.getByRole("button", { name: "Rediger" }).click();
  await page.getByRole("button", { name: "Finn bilder" }).click();
  await page.getByRole("button", { name: "Last opp bilde" }).click();
  await page.getByLabel("Velg JPEG-, PNG- eller WebP-bilde").setInputFiles({
    name: "upload.png",
    mimeType: "image/png",
    buffer: imageBody,
  });

  const uploadCandidate = page.getByRole("button", { name: /Lastet opp.*upload\.png/ });
  await expect(uploadCandidate).toBeVisible();
  await expect(page.getByRole("button", { name: "Prosesser valgt bilde" })).toHaveCount(0);
  await uploadCandidate.click();
  await expect(page.getByLabel("Live crop-preview").getByRole("img")).toHaveCount(3);
  await page.getByLabel("Bildetype").selectOption("logo");
  await expect(page.getByText("Logo viser hele motivet uten beskjæring.")).toBeVisible();
  await expect(page.getByRole("img", { name: "Forhåndsvisning av hele logoen" })).toBeVisible();
  await expect(page.getByText("Finjuster utsnitt")).toHaveCount(0);
  await expect(page.getByLabel("Zoom")).toHaveCount(0);
  await page.getByRole("button", { name: "Prosesser valgt bilde" }).click();
  await expect(page.getByRole("textbox", { name: /Alt-tekst \(valgfritt\)/ })).toHaveValue("");
  await page.getByRole("button", { name: "Godkjenn og lås bilde" }).click();

  await expect(page.getByText("Aktivt bilde")).toBeVisible();
  await expect(page.getByText("Ingen alt-tekst")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Public Preview (legacy)" })).toBeVisible();
  expect(state.organizations[0].is_published).toBe(true);
  expect(state.organizations[0].og_image_url).toBeNull();
});

test("Brave search is mocked with exact manual query, privacy copy, private preview, and processing", async ({ page }) => {
  const state = await setupMockEditorApi(page);
  state.organizations[0].image_asset_feature_enabled = true;
  const imageBody = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAQAAABp8Z5+AAAADklEQVR42mNk+M8AAQADAgEAff9qAAAAAElFTkSuQmCC",
    "base64",
  );

  await page.route("**/api/tenants/1/organizations/10/images/state/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ expected_revision: 0, active_selection: null }),
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
  await page.getByRole("button", { name: "Rediger" }).click();
  await page.getByRole("button", { name: "Finn bilder" }).click();
  await page.getByRole("button", { name: "Søk etter flere bilder" }).click();
  await expect(page.getByText(/Bildesøket utføres via Brave Search/)).toBeVisible();
  const query = page.getByLabel("Forslått søk");
  await expect(query).toHaveValue("Kreativ Demo AS Oslo");
  await query.fill("Festspillene Helgeland logo");
  await page.getByRole("button", { name: "Søk", exact: true }).click();
  await expect(page.getByText("Eksempelavisen · publisher.example")).toBeVisible();
  await expect(page.getByText("Bildesøk viser forslag fra nettet. Kontroller at bildet kan brukes før du godkjenner det.")).toBeVisible();
  await page.getByRole("button", { name: /Festspillene Helgeland/ }).click();
  await page.getByRole("button", { name: "Prosesser valgt bilde" }).click();
  await expect(page.getByLabel("Serverens bildeformater").getByRole("img")).toHaveCount(3);
  await expect(page.getByRole("heading", { name: "Public Preview (legacy)" })).toBeVisible();
});
