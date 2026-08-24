import { expect, test } from "@playwright/test";
import { Buffer } from "node:buffer";

const publicOrigin = "http://127.0.0.1:8000";
const fallbackRoot = `${publicOrigin}/static/crm/public-image-fallback/v1`;
const tinyPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

function boxesOverlap(
  first: { x: number; y: number; width: number; height: number },
  second: { x: number; y: number; width: number; height: number },
) {
  return !(
    first.x + first.width <= second.x ||
    second.x + second.width <= first.x ||
    first.y + first.height <= second.y ||
    second.y + second.height <= first.y
  );
}

test("PUBLIC cutover exposes fallback projection, metadata, and target API", async ({
  page,
  request,
}) => {
  await page.goto(`${publicOrigin}/public/actors/?q=Playwright%20fallback`);

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
  await page.goto(`${publicOrigin}/public/actors/?q=Playwright%20fallback`);
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

test("PUBLIC asset keeps approved alt, credit, metadata, and long layout", async ({
  page,
  request,
}) => {
  await page.route("**/media/releases/**", (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: tinyPng }),
  );
  await page.goto(`${publicOrigin}/public/actors/?q=Playwright%20asset`);

  const card = page.locator(".card", { hasText: "Playwright asset actor" });
  await expect(card).toBeVisible();
  const cardImage = card.locator("img");
  await expect(cardImage).toHaveAttribute("src", /\/media\/releases\/.+\/square\.webp$/);
  await expect(cardImage).toHaveAttribute("alt", "Scene med godkjent alttekst");
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
    await page.evaluate(() => document.documentElement.clientWidth),
  );

  const detailHref = await card.getAttribute("href");
  await page.goto(`${publicOrigin}${detailHref}`);
  const detailImage = page.locator(".hero-card img");
  await expect(detailImage).toHaveAttribute("alt", "Scene med godkjent alttekst");
  await expect(page.locator(".image-credit")).toHaveText("Foto: Playwright");
  await expect(detailImage).toHaveCSS("width", "160px");
  await expect(detailImage).toHaveCSS("height", "160px");
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute(
    "content",
    /\/media\/releases\/.+\/share\.webp$/,
  );
  await expect(page.locator('meta[property="og:image:alt"]')).toHaveAttribute(
    "content",
    "Scene med godkjent alttekst",
  );

  await page.setViewportSize({ width: 390, height: 844 });
  const creditBox = await page.locator(".image-credit").boundingBox();
  const heroBodyBox = await page.locator(".hero-body").boundingBox();
  expect(creditBox).not.toBeNull();
  expect(heroBodyBox).not.toBeNull();
  expect(boxesOverlap(creditBox!, heroBodyBox!)).toBeFalsy();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
    await page.evaluate(() => document.documentElement.clientWidth),
  );

  const api = await request.get(`${publicOrigin}/api/public/actors/888888888/`);
  const payload = await api.json();
  expect(payload.image.kind).toBe("asset");
  expect(payload.image.alt_text).toBe("Scene med godkjent alttekst");
  expect(payload.image.credit).toBe("Foto: Playwright");
  expect(payload.thumbnail_image_url).toBe(payload.image.square.url);
  expect(payload.preview_image_url).toBe(payload.image.square.url);
});

test("PUBLIC asset byte error switches once to blank-alt static fallback", async ({ page }) => {
  await page.route("**/media/releases/**", (route) => route.abort("failed"));
  await page.goto(`${publicOrigin}/public/actors/?q=Playwright%20asset`);

  const image = page.locator(".card", { hasText: "Playwright asset actor" }).locator("img");
  await expect(image).toHaveAttribute("src", `${fallbackRoot}/fallback-square.png`);
  await expect(image).toHaveAttribute("alt", "");
  expect(await image.evaluate((element: HTMLImageElement) => element.onerror)).toBeNull();
  expect(await image.evaluate((element: HTMLImageElement) => element.naturalWidth)).toBe(512);
  await expect(image).not.toHaveAttribute("src", /legacy\.invalid/);
});
