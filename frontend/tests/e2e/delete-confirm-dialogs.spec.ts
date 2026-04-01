import { expect, test } from "@playwright/test";
import { loginAsEditor, setupMockEditorApi } from "./mockEditorApi";

async function latestConfirmMessage(page: import("@playwright/test").Page): Promise<string> {
  const messages = await page.evaluate(
    () => (window as Window & { __confirmMessages?: string[] }).__confirmMessages ?? [],
  );
  return messages.at(-1) ?? "";
}

async function confirmMessageCount(page: import("@playwright/test").Page): Promise<number> {
  return await page.evaluate(
    () => ((window as Window & { __confirmMessages?: string[] }).__confirmMessages ?? []).length,
  );
}

async function clickUntilConfirmIncrements(
  page: import("@playwright/test").Page,
  click: () => Promise<void>,
  previousCount: number,
): Promise<number> {
  for (let attempt = 0; attempt < 6; attempt += 1) {
    await click();
    try {
      await page.waitForFunction(
        (prev) => ((window as Window & { __confirmMessages?: string[] }).__confirmMessages ?? []).length > prev,
        previousCount,
        { timeout: 2000 },
      );
      return await confirmMessageCount(page);
    } catch {
      await page.waitForTimeout(150);
    }
  }

  throw new Error("Confirm dialog was not triggered after retries");
}

test("shows confirm dialogs for deleting link and person", async ({ page }) => {
  await page.addInitScript(() => {
    (window as Window & { __confirmMessages?: string[] }).__confirmMessages = [];
    window.confirm = (message?: string) => {
      (window as Window & { __confirmMessages?: string[] }).__confirmMessages?.push(String(message ?? ""));
      return false;
    };
  });

  await setupMockEditorApi(page, {
    organizationPeople: [
      {
        id: 30,
        tenant: 1,
        organization: 10,
        person: 20,
        status: "ACTIVE",
        publish_person: true,
        created_at: "2026-01-01T00:00:00Z",
      },
    ],
    personContacts: [
      {
        id: 40,
        tenant: 1,
        person: 20,
        type: "EMAIL",
        value: "ada@example.com",
        is_primary: true,
        is_public: true,
        created_at: "2026-01-01T00:00:00Z",
      },
    ],
    persons: [
      {
        id: 20,
        tenant: 1,
        full_name: "Ada Editor",
        email: "ada@example.com",
        phone: "+4799999999",
        municipality: "Oslo",
        note: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        contacts: [
          {
            id: 40,
            tenant: 1,
            person: 20,
            type: "EMAIL",
            value: "ada@example.com",
            is_primary: true,
            is_public: true,
            created_at: "2026-01-01T00:00:00Z",
          },
        ],
      },
    ],
  });

  await page.goto("/organizations/10");
  await loginAsEditor(page);

  const linkRow = page.locator(".link-row").filter({ hasText: "Ada Editor" }).first();
  let count = await confirmMessageCount(page);
  count = await clickUntilConfirmIncrements(page, async () => {
    await linkRow.getByRole("button", { name: "Fjern" }).dispatchEvent("click");
  }, count);
  expect(await latestConfirmMessage(page)).toContain("Fjerne koblingen");

  await expect(page.getByText("Ada Editor")).toBeVisible();

  await page.getByRole("link", { name: /Personer/ }).click();
  await page.getByRole("button", { name: "Ada Editor" }).click();
  count = await clickUntilConfirmIncrements(page, async () => {
    await page.evaluate(() => {
      const button = Array.from(document.querySelectorAll("button")).find(
        (candidate) => candidate.textContent?.trim() === "Slett person",
      );
      button?.click();
    });
  }, count);
  expect(await latestConfirmMessage(page)).toContain("Slette valgt person");

  await expect(page.getByRole("button", { name: /Ada Editor/ })).toBeVisible();
});
