import { test, expect } from '@playwright/test';
import { setupMockEditorApi, loginAsEditor } from './mockEditorApi';

for (const width of [1920, 390, 320]) test(`Editor identity, fitted tags and linked person card at ${width}px`, async ({page}, info) => {
  await page.setViewportSize({width,height:width===1920?1080:844});
  const state=await setupMockEditorApi(page);
  const actor=state.organizations[0],person=state.persons[0];
  actor.name='Lofoten Internasjonale Kammermusikkfestival';actor.municipalities='Vestvågøy';
  actor.categories=[state.categories[0]];actor.subcategories=[state.subcategories[0]];
  actor.tags=['jazz','live','blues','konsertproduksjon','internasjonalt samarbeid'].map((name,i)=>({id:100+i,tenant:1,name,slug:name.replaceAll(' ','-'),created_at:'2026-01-01T00:00:00Z'}));
  actor.active_people=[{id:40,person:{id:person.id,full_name:person.full_name,title:person.title,municipality:person.municipality},status:'ACTIVE',publish_person:false}];
  state.organizationPeople.push({id:40,tenant:1,organization:actor.id,person:person.id,status:'ACTIVE',publish_person:false,created_at:'2026-01-01T00:00:00Z'});
  state.organizations.push(...Array.from({length:40},(_,i)=>({...actor,id:50+i,name:i===0?'Kort navn':`Syntetisk aktør ${i+1}`,active_people:[]})));
  await page.goto('/organizations');await loginAsEditor(page);
  await expect(page).toHaveTitle('Editor CRM');await expect(page.locator('.editor-brand')).toHaveText('Editor CRM');await expect(page.locator('.editor-sidebar')).not.toContainText('Kreative Norge');
  await expect(page.getByRole('button',{name:'Kart',exact:true})).toBeDisabled();
  await expect(page.getByRole('navigation',{name:'Hovednavigasjon'}).locator('svg')).toHaveCount(5);
  const card=page.locator('.editor-card-grid article').filter({has:page.getByRole('button',{name:actor.name,exact:true})});
  await expect(card.locator('.card-name')).toHaveCSS('font-weight','600');
  if(width<600) {await expect(card.locator('.card-name')).toHaveCSS('font-size','17px');await expect(card.locator('.editor-card-head .meta')).toHaveCSS('font-size','13px');}
  const short=page.locator('.editor-card-grid article').filter({has:page.getByRole('button',{name:'Kort navn',exact:true})});
  await expect.poll(()=>short.locator('.card-tags > .mini-pill').count()).toBeGreaterThan(1);
  for(const item of [card,short]) {
    const visible=await item.locator('.card-tags > .mini-pill').count();
    if(visible<actor.tags.length) await expect(item.locator('.tag-count')).toHaveText(`+${actor.tags.length-visible}`);
    else await expect(item.locator('.tag-count')).toHaveCount(0);
    expect(await item.locator('.card-tags').evaluate(e=>Array.from(e.children).filter(x=>!x.classList.contains('card-tags-probe')).every(x=>{const a=e.getBoundingClientRect(),b=x.getBoundingClientRect();return b.top>=a.top-.5&&b.bottom<=a.bottom+.5&&b.right<=a.right+.5;}))).toBe(true);
  }
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:info.outputPath(`overview-${width}.png`)});
  await card.locator('.tag-count').click();const dialog=page.getByRole('dialog');
  await expect(dialog.locator('.mini-pill.tag')).toHaveCount(5);await expect(dialog.getByText('Primærlenke',{exact:true})).toHaveCount(0);await expect(dialog.getByRole('link',{name:'Nettside',exact:true})).toBeVisible();
  await dialog.getByRole('button',{name:person.full_name,exact:true}).click();
  await expect(page.getByRole('dialog')).toHaveCount(1);await expect(page.getByRole('dialog').getByRole('heading',{name:person.full_name,exact:true})).toBeVisible();await page.screenshot({path:info.outputPath(`linked-person-${width}.png`)});
  await page.goBack();await expect(page.getByRole('dialog')).toHaveCount(0);
  await card.locator('.tag-count').click();await page.getByRole('dialog').getByRole('button',{name:person.full_name,exact:true}).click();
  await page.keyboard.press('Escape');await expect(page.getByRole('dialog').getByRole('heading',{name:actor.name,exact:true})).toBeVisible();await page.keyboard.press('Escape');
  await page.evaluate(()=>scrollTo(0,document.body.scrollHeight));await short.getByRole('button',{name:'Kort navn',exact:true}).click();
  const edit=page.getByRole('dialog').getByRole('button',{name:'Rediger',exact:true});await edit.scrollIntoViewIfNeeded();await edit.click();await expect(page).toHaveURL(/\/organizations\/50$/);await expect.poll(()=>page.evaluate(()=>scrollY)).toBe(0);
  if(width<600) await expect(page.locator('.profile-scope')).toHaveCSS('font-size','14px');
  await page.screenshot({path:info.outputPath(`actor-form-${width}.png`)});
  await page.locator('summary').filter({hasText:/^Opprett kontaktperson/}).click();await expect(page.getByText('Klar',{exact:true})).toHaveCount(0);
  await page.getByRole('link',{name:'Personer',exact:true}).click();await page.getByRole('searchbox',{name:'Søk personer'}).fill(person.full_name);await page.locator('.person-results').getByRole('button',{name:person.full_name,exact:true}).click();await page.getByRole('dialog').getByRole('button',{name:'Rediger',exact:true}).click();
  await expect(page.getByLabel('E-post',{exact:true})).toBeVisible();await expect(page.getByLabel('Telefon',{exact:true})).toBeVisible();await expect(page.locator('.person-contact-group > h3')).toHaveText(['E-post','Telefon']);
  await expect(page.locator('.person-contact-group > .person-contact-row .field-label:not(.sr-only)')).toHaveCount(0);await page.screenshot({path:info.outputPath(`person-form-${width}.png`)});
});

test('reader can open a linked person card without edit access',async({page})=>{
  const state=await setupMockEditorApi(page);state.tenants[0].current_user_role='leser';
  const actor=state.organizations[0],person=state.persons[0];actor.active_people=[{id:40,person:{id:person.id,full_name:person.full_name},status:'ACTIVE',publish_person:false}];
  await page.goto('/organizations');await loginAsEditor(page);await page.getByRole('button',{name:actor.name,exact:true}).click();await page.getByRole('dialog').getByRole('button',{name:person.full_name,exact:true}).click();
  await expect(page.getByRole('dialog').getByRole('heading',{name:person.full_name,exact:true})).toBeVisible();await expect(page.getByRole('dialog').getByRole('button',{name:'Rediger',exact:true})).toHaveCount(0);
});


test('tags refit after viewport resize and show no counter when all fit',async({page})=>{
 const state=await setupMockEditorApi(page);const actor=state.organizations[0];actor.name='Kort navn';actor.categories=[state.categories[0]];
 actor.tags=['jazzmusikk','bluesmusikk','scenekunst','kulturfestival','internasjonalt'].map((name,i)=>({id:100+i,tenant:1,name,slug:name,created_at:''}));
 await page.setViewportSize({width:1200,height:900});await page.goto('/organizations');await loginAsEditor(page);
 const tags=page.locator('.card-tags');await expect.poll(()=>tags.locator('> .mini-pill').count()).toBe(5);await expect(tags.locator('.tag-count')).toHaveCount(0);
 await page.setViewportSize({width:320,height:844});await expect.poll(()=>tags.locator('> .mini-pill').count()).toBeLessThan(5);
 const visible=await tags.locator('> .mini-pill').count();await expect(tags.locator('.tag-count')).toHaveText(`+${5-visible}`);
 await page.setViewportSize({width:1200,height:900});await expect.poll(()=>tags.locator('> .mini-pill').count()).toBe(5);await expect(tags.locator('.tag-count')).toHaveCount(0);
});

test('authorized Admin remains below the shared five-item mobile menu',async({page},info)=>{
 await setupMockEditorApi(page);
 await page.route('**/api/auth/session/',route=>route.fulfill({json:{authenticated:true,user:{id:1,username:'synthetic-admin',display_name:'Ada Eksempel',is_superuser:true,can_access_admin:true,memberships:[{id:1,tenant:1,user:1,role:'superadmin'}]}}}));
 await page.setViewportSize({width:390,height:844});await page.goto('/organizations');
 const nav=page.getByRole('navigation',{name:'Hovednavigasjon'});await expect(nav.getByRole('link')).toHaveText(['Aktører','Personer','Import','Eksport','Admin']);await expect(nav.locator('svg')).toHaveCount(6);
 const admin=await nav.getByRole('link',{name:'Admin',exact:true}).boundingBox(),map=await nav.getByRole('button',{name:'Kart',exact:true}).boundingBox();expect(admin!.y).toBeGreaterThan(map!.y);
 await page.screenshot({path:info.outputPath('admin-hero-390.png')});
});

test('very long tags retain a readable first tag and an exact overflow count',async({page})=>{
 const state=await setupMockEditorApi(page),actor=state.organizations[0];actor.name='Langt internasjonalt aktørnavn med mange ord';actor.categories=[state.categories[0]];actor.subcategories=[state.subcategories[0]];
 actor.tags=Array.from({length:5},(_,i)=>({id:100+i,tenant:1,name:`Langt emne ${i+1} for internasjonalt kultursamarbeid`,slug:`tag-${i}`,created_at:''}));
 await page.setViewportSize({width:320,height:844});await page.goto('/organizations');await loginAsEditor(page);
 const tags=page.locator('.card-tags');await expect(tags.locator('> .mini-pill')).toHaveCount(1);await expect(tags.locator('.tag-count')).toHaveText('+4');
 expect(await tags.evaluate(e=>e.scrollWidth<=e.clientWidth)).toBe(true);await tags.locator('.tag-count').click();await expect(page.getByRole('dialog').locator('.mini-pill.tag')).toHaveCount(5);
 expect(await page.getByRole('dialog').evaluate(e=>e.scrollWidth<=e.clientWidth)).toBe(true);
});
