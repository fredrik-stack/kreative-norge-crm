import {test,expect} from '@playwright/test';
import {setupMockEditorApi,loginAsEditor} from './mockEditorApi';

test('outer actor footer submits the main form, validates hidden fields, and follows every separate section',async({page})=>{
 const state=await setupMockEditorApi(page);state.tenants[0].current_user_role='gruppeadmin';await page.goto('/organizations');await loginAsEditor(page);
 await page.getByRole('button',{name:'Ny aktør',exact:true}).click();
 const footer=page.locator('.actor-profile-footer'); const submit=footer.getByRole('button',{name:'Opprett aktør',exact:true});
 expect(await submit.evaluate((button:HTMLButtonElement)=>button.form?.id)).toBe('organization-profile-form');
 await submit.click();await expect(page.getByLabel('Navn',{exact:false}).first()).toBeFocused();
 await page.getByLabel('Navn',{exact:false}).first().fill('Footeraktør');
 const links=page.locator('summary').filter({hasText:/^Lenker og sosiale medier/});
 await links.click();await page.getByLabel('Website URL',{exact:true}).fill('broken');await links.click();
 await submit.click();await expect(page.getByLabel('Website URL',{exact:true})).toBeFocused();
 await page.getByLabel('Website URL',{exact:true}).fill('https://example.invalid');await links.click();
 const request=page.waitForRequest(r=>r.method()==='POST'&&r.url().endsWith('/organizations/'));
 await submit.click();expect((await request).postDataJSON().name).toBe('Footeraktør');
 await expect(footer.getByRole('button',{name:'Lagre aktør',exact:true})).toBeDisabled();
 expect(await footer.evaluate(e=>Boolean(e.previousElementSibling?.textContent?.includes('Forhåndsvisning')))).toBe(true);
 await expect(footer.getByRole('button',{name:'Slett aktør',exact:true})).toBeEnabled();
});

test('actor deletion confirms, preserves a protected profile, then uses the same existing DELETE endpoint',async({page})=>{
 const state=await setupMockEditorApi(page);state.tenants[0].current_user_role='gruppeadmin';await page.goto('/organizations');await loginAsEditor(page);
 await page.getByRole('button',{name:'Kreativ Demo AS',exact:true}).click();await page.getByRole('dialog').getByRole('button',{name:'Rediger',exact:true}).click();
 let deletes=0,protectedProfile=true;
 await page.route('**/api/tenants/1/organizations/10/',async route=>{
  if(route.request().method()!=='DELETE')return route.fallback();deletes++;
  if(protectedProfile)return route.fulfill({status:409,json:{code:'profile_delete_protected',detail:'Profilen har beskyttet tilhørighet eller historikk og kan ikke slettes.'}});
  return route.fulfill({status:204,body:''});
 });
 page.once('dialog',d=>d.dismiss());await page.getByRole('button',{name:'Slett aktør',exact:true}).click();expect(deletes).toBe(0);
 page.once('dialog',d=>d.accept());await page.getByRole('button',{name:'Slett aktør',exact:true}).click();
 await expect(page.getByText('Profilen har beskyttet tilhørighet eller historikk og kan ikke slettes.',{exact:true})).toBeVisible();
 await expect(page.getByLabel('Navn',{exact:false}).first()).toHaveValue('Kreativ Demo AS');
 protectedProfile=false;page.once('dialog',d=>d.accept());await page.getByRole('button',{name:'Slett aktør',exact:true}).click();
 await expect(page).toHaveURL(/\/organizations$/);expect(deletes).toBe(2);
 await expect(page.locator('.editor-card-grid').getByRole('button',{name:'Kreativ Demo AS',exact:true})).toHaveCount(0);
});
