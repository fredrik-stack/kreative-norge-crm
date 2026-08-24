import { expect, test } from "@playwright/test";

const publicOrigin = "http://127.0.0.1:8000";
const fallbackRoot = `${publicOrigin}/static/crm/public-image-fallback/v1`;

test("PUBLIC cutover exposes fallback projection, metadata, and target API", async ({
  page,
  request,
}) => {
  await page.goto(`${publicOrigin}/public/actors/?q=Playwright`);

  const card = page.locator(".card", { hasText: "Playwright fallback actor" });
  await expect(card).toBeVisible();
  const image = card.locator("img");
  await expect(image).toHaveAttribute("src", `${fallbackRoot}/fallback-square.png`);
  await expect(image).toHaveAttribute("alt", "");
  await expect(image).not.toHaveAttribute("onerror", /.+/);
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    "href",
    `${publicOrigin}/public/actors/`,
  );
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute(
    "content",
    `${fallbackRoot}/fallback-share.png`,
  );
  await expect(image).toHaveJSProperty("complete", true);
  expect(await image.evaluate((element: HTMLImageElement) => element.naturalWidth)).toBe(512);

  const detailHref = await card.getAttribute("href");
  expect(detailHref).toMatch(/^\/public\/actors\/id\/\d+\/$/);
  await page.goto(`${publicOrigin}${detailHref}`);
  await expect(page.locator(".hero-card img")).toHaveAttribute(
    "src",
    `${fallbackRoot}/fallback-square.png`,
  );
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute(
    "content",
    `${fallbackRoot}/fallback-share.png`,
  );
  await expect(page.locator('meta[property="og:image:width"]')).toHaveAttribute(
    "content",
    "1200",
  );
  await expect(page.locator('meta[property="og:image:height"]')).toHaveAttribute(
    "content",
    "630",
  );
  await expect(page.locator('meta[property="og:image:alt"]')).toHaveCount(0);

  const api = await request.get(`${publicOrigin}/api/public/actors/999999999/`);
  expect(api.ok()).toBeTruthy();
  const payload = await api.json();
  expect(payload.image.kind).toBe("system_fallback");
  expect(payload.image.alt_text).toBe("");
  expect(payload.thumbnail_image_url).toBe(payload.image.square.url);
  expect(payload.preview_image_url).toBe(payload.image.square.url);
  expect(JSON.stringify(payload)).not.toContain("legacy.invalid");
});

test("PUBLIC detail keeps the square image readable on desktop and mobile", async ({ page }) => {
  await page.goto(`${publicOrigin}/public/actors/?q=Playwright`);
  const detailHref = await page
    .locator(".card", { hasText: "Playwright fallback actor" })
    .getAttribute("href");
  await page.goto(`${publicOrigin}${detailHref}`);

  const desktopImage = page.locator(".hero-card img");
  await expect(desktopImage).toHaveCSS("width", "160px");
  await expect(desktopImage).toHaveCSS("height", "160px");

  await page.setViewportSize({ width: 390, height: 844 });
  const mobileBox = await desktopImage.boundingBox();
  expect(mobileBox).not.toBeNull();
  expect(mobileBox!.width).toBeGreaterThan(300);
  expect(mobileBox!.height).toBe(210);
});
