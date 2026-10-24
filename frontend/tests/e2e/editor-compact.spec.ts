import { expect, test } from "@playwright/test";
import { loginAsEditor, setupMockEditorApi } from "./mockEditorApi";

test("people starts with search, preserves query/selection on profile return and separates no results", async ({page}) => {
  await setupMockEditorApi(page);
  await page.goto('/people'); await loginAsEditor(page);
  await expect(page.getByRole('heading',{name:'Finn en person'})).toBeVisible();
  await expect(page.locator('.person-results tr')).toHaveCount(0);
  const search=page.getByRole('searchbox',{name:'Søk personer'});
  await search.fill('Ada');
  await expect(page.locator('.person-results th')).toHaveCount(4);
  const name=page.getByRole('button',{name:'Ada Editor',exact:true});
  await name.click();
  await expect(page.getByRole('dialog')).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(page.getByRole('dialog').getByRole('button',{name:'Rediger'})).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('dialog').getByRole('button',{name:'Lukk'}).first()).toBeFocused();
  await page.keyboard.press('Escape'); await expect(name).toBeFocused();
  await name.click(); await page.getByRole('dialog').getByRole('button',{name:'Rediger'}).click();
  await page.getByRole('button',{name:'← Til personoversikt'}).click();
  await expect(search).toHaveValue('Ada');
  await expect(page.locator('.selected-result')).toContainText('Ada Editor');
  await search.fill('ingen-syntetiske-treff'); await expect(page.getByText('Ingen personer matcher søket eller filtrene.')).toBeVisible();
  await page.getByRole('button',{name:'Nullstill filtre'}).click();
  await expect(page.getByRole('heading',{name:'Finn en person'})).toBeVisible();
  await expect(page).toHaveURL(/\/people$/);
  await expect(page.locator('.person-results tr')).toHaveCount(0);
  await page.getByLabel('Hovedkategori',{exact:true}).selectOption('musikk');
  await expect(page.getByRole('heading',{name:'Finn en person'})).toHaveCount(0);
  await expect(page.getByText('Ingen personer matcher søket eller filtrene.')).toBeVisible();
});

test("closed profile sections retain drafts, reveal native errors and link duplicate server errors to the right field", async ({page}) => {
  await setupMockEditorApi(page);await page.goto('/organizations');await loginAsEditor(page);
  await page.getByRole('button',{name:'Rediger',exact:true}).first().click();
  const links=page.locator('summary').filter({hasText:/^Lenker og sosiale medier/});
  await links.click();await page.getByLabel('Website URL',{exact:true}).fill('broken');await links.click();
  await page.getByLabel('Navn',{exact:false}).first().fill('Kreativ Demo endret');
  await page.getByRole('button',{name:'Lagre aktør'}).click();
  await expect(page.getByLabel('Website URL',{exact:true})).toBeFocused();
  await expect(page.getByLabel('Website URL',{exact:true})).toHaveValue('broken');
  await page.getByLabel('Website URL',{exact:true}).fill('https://example.invalid');
  await page.getByLabel('Facebook URL',{exact:true}).fill('https://example.invalid/facebook');await links.click();
  await page.route('**/api/tenants/1/organizations/10/',route=>route.request().method()==='PATCH'
    ? route.fulfill({status:400,json:{website_url:['Ugyldig URL.'],facebook_url:['Ugyldig URL.']}}) : route.continue());
  await page.getByRole('button',{name:'Lagre aktør'}).click();
  await expect(page.getByRole('status')).toHaveText('Lagring ikke bekreftet');
  await expect(page.getByLabel('Website URL',{exact:true})).toBeVisible();
  await links.click();
  await page.locator('.profile-validation').getByRole('button',{name:/Facebook/}).click();
  await expect(page.getByLabel('Facebook URL',{exact:true})).toBeFocused();
});

test("person loading failure is distinct from search entry and no results", async ({page}) => {
  await setupMockEditorApi(page);
  await page.route('**/api/tenants/1/persons/',route=>route.fulfill({status:503,json:{detail:'Synthetic read failure'}}));
  await page.goto('/people');await loginAsEditor(page);
  await expect(page.getByText('Personoversikten kunne ikke lastes. Prøv å laste siden på nytt.')).toBeVisible();
  await expect(page.getByRole('heading',{name:'Finn en person'})).toHaveCount(0);
  await expect(page.locator('.person-results')).toHaveCount(0);
});
