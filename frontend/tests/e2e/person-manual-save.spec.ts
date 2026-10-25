import { expect, test } from "@playwright/test";
import { loginAsEditor, setupMockEditorApi } from "./mockEditorApi";

test("manual contacts retain confirmed IDs after failure and retry without duplicate creates", async ({page}) => {
  const state=await setupMockEditorApi(page);
  const errors:string[]=[]; page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/people'); await loginAsEditor(page);
  await page.getByRole('button',{name:'Ny person',exact:true}).click();
  await page.getByLabel('Fullt navn',{exact:false}).fill('Ny Kontakt');
  await page.getByLabel('E-post',{exact:true}).fill('main@example.invalid');
  await page.getByLabel('Telefon',{exact:true}).fill('+4790012345');
  await page.getByRole('button',{name:'+ Legg til ekstra e-post',exact:true}).click();
  await page.getByLabel('E-post 2',{exact:true}).fill('extra@example.invalid');
  await page.getByRole('button',{name:'+ Legg til ekstra telefon',exact:true}).click();
  await page.getByLabel('Telefon 2',{exact:true}).fill('+4791234567');
  await page.getByLabel('E-post 2',{exact:true}).blur();
  expect(state.persons).toHaveLength(1); expect(state.personContacts).toHaveLength(0);
  let fail=true; let personPosts=0, emailPosts=0;
  page.on('request',request=>{
    if(request.method()!=='POST')return;
    if(request.url().endsWith('/persons/'))personPosts++;
    if(request.url().endsWith('/person-contacts/')&&request.postDataJSON().type==='EMAIL')emailPosts++;
  });
  await page.route('**/api/tenants/1/person-contacts/',async route=>{
    if(route.request().method()==='POST'&&route.request().postDataJSON().type==='PHONE'&&fail)
      await route.fulfill({status:400,json:{value:['Prøv igjen']}});
    else await route.fallback();
  });
  await page.getByRole('button',{name:'Opprett person',exact:true}).last().click();
  await expect(page.locator('.profile-form').getByRole('status').first()).toHaveText('Lagring ikke bekreftet');
  const id=state.persons[1].id;
  const confirmed=state.personContacts.filter(contact=>contact.person===id).map(contact=>contact.id);
  expect(confirmed).toHaveLength(3);
  await expect(page.getByLabel('Telefon 2',{exact:true})).toHaveValue('+4791234567');
  fail=false;
  await page.getByRole('button',{name:'Lagre person',exact:true}).first().click();
  await expect(page).toHaveURL(new RegExp(`/people/${id}$`));
  await expect(page.getByRole('dialog')).toHaveCount(0);
  expect(personPosts).toBe(1); expect(emailPosts).toBe(1);
  const contacts=state.personContacts.filter(contact=>contact.person===id);
  expect(contacts).toHaveLength(4); expect(contacts.filter(contact=>contact.is_primary)).toHaveLength(2);
  expect(confirmed.every(id=>contacts.some(contact=>contact.id===id))).toBe(true);
  await page.getByLabel('E-post 2',{exact:true}).fill('changed@example.invalid');
  await page.getByRole('button',{name:'Logg ut',exact:true}).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button',{name:'Bli her',exact:true}).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('link',{name:'Aktører',exact:true}).click();
  await page.getByRole('button',{name:'Forlat uten å lagre',exact:true}).click();
  await expect(page).toHaveURL(/\/organizations$/);
  expect(errors).toEqual([]);
});
