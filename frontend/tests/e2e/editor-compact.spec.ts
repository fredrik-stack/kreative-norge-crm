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
  await page.locator('.editor-card-grid').getByRole('button',{name:'Kreativ Demo AS'}).click();await page.getByRole('dialog').getByRole('button',{name:'Rediger'}).click();
  const links=page.locator('summary').filter({hasText:/^Lenker og sosiale medier/});
  await links.click();await page.getByLabel('Website URL',{exact:true}).fill('broken');await links.click();
  await page.evaluate(() => {
    document.addEventListener('invalid', event => {
      queueMicrotask(() => { document.body.dataset.nativeErrorCancelled = String(event.defaultPrevented); });
    }, true);
  });
  await page.getByLabel('Navn',{exact:false}).first().fill('Kreativ Demo endret');
  await page.getByRole('button',{name:'Lagre aktør'}).first().click();
  await expect(page.getByLabel('Website URL',{exact:true})).toBeFocused();
  await expect(page.getByLabel('Website URL',{exact:true})).toHaveValue('broken');
  await expect(page.locator('body')).toHaveAttribute('data-native-error-cancelled','false');
  await page.getByLabel('Website URL',{exact:true}).fill('https://example.invalid');
  await page.getByLabel('Facebook URL',{exact:true}).fill('https://example.invalid/facebook');await links.click();
  await page.route('**/api/tenants/1/organizations/10/',route=>route.request().method()==='PATCH'
    ? route.fulfill({status:400,json:{website_url:['Ugyldig URL.'],facebook_url:['Ugyldig URL.']}}) : route.continue());
  await page.getByRole('button',{name:'Lagre aktør'}).first().click();
  await expect(page.getByRole('status').first()).toHaveText('Lagring ikke bekreftet');
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

test("a linked actor opens even when the retained person search excludes actor cards", async ({page}) => {
  const state=await setupMockEditorApi(page);
  state.organizationPeople.push({id:40,tenant:1,organization:10,person:20,status:'ACTIVE',publish_person:false,created_at:'2026-01-01T00:00:00Z'});
  await page.goto('/people');await loginAsEditor(page);
  await page.getByRole('searchbox',{name:'Søk personer'}).fill('Manager');
  await page.locator('.person-results').getByRole('button',{name:'Kreativ Demo AS',exact:true}).click();
  await expect(page.getByRole('dialog').getByRole('heading',{name:'Kreativ Demo AS',exact:true})).toBeVisible();
  await expect(page.locator('.editor-card-grid article')).toHaveCount(0);
  await page.keyboard.press('Escape');
  await page.getByRole('link',{name:/^Personer/}).click();
  await expect(page.getByRole('searchbox',{name:'Søk personer'})).toHaveValue('Manager');
  await expect(page.locator('.selected-result')).toContainText('Ada Editor');
});
