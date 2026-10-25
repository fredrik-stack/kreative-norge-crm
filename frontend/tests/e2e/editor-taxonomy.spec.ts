import { test, expect, type Locator } from '@playwright/test';
import { setupMockEditorApi, loginAsEditor } from './mockEditorApi';

const colors = {category:'rgb(107, 73, 61)',subcategory:'rgb(56, 168, 236)',tag:'rgb(74, 135, 85)'};
async function expectTaxonomyColors(scope: Locator) {
  for (const [kind,color] of Object.entries(colors)) {
    const pills=scope.locator(`.mini-pill.${kind}`);
    expect(await pills.count()).toBeGreaterThan(0);
    for (const pill of await pills.all()) await expect(pill).toHaveCSS('background-color',color);
  }
}

for (const width of [1920,390,320]) test(`square thumbnails, fixed cards and semantic taxonomy colors at ${width}px`,async({page},info)=>{
  await page.setViewportSize({width,height:width===1920?1080:844});
  const state=await setupMockEditorApi(page);
  const category=state.categories[0],subcategory=state.subcategories[0],tag=state.tags[0];
  const source=state.organizations[0];
  const names=['Fjordfestivalen','Lofoten Internasjonale Kammermusikkfestival','Nordlys kulturverksted og internasjonale produksjonssamarbeid','Kulturfabrikken Meløy','Kultursamarbeidet i Vesterålen','Made Management AS','Meieriet Kultursenter','Kysten Jazzklubb','Kunnskapsparken Helgeland AS','Lydteamet'];
  state.organizations=names.map((name,i)=>({...source,id:10+i,name,municipalities:i===2?'Kautokeino / Guovdageaidnu og Porsanger':'Vestvågøy',categories:[category],subcategories:[subcategory],tags:[tag],preview_image_url:i===0?'/synthetic-square-thumbnail.svg':null}));
  state.persons[0]={...state.persons[0],full_name:'Alexandra Kristine Eksempel Langt-Etternavn',title:'Programansvarlig for internasjonale samarbeidsproduksjoner',email:'alexandra@example.invalid',municipality:'Kautokeino / Guovdageaidnu',categories:[category],subcategories:[subcategory],tags:[tag]};
  await page.route('**/synthetic-square-thumbnail.svg',route=>route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160"><rect width="160" height="160" fill="#145e4c"/><circle cx="130" cy="30" r="60" fill="#327c65"/><path d="M25 140V80l55-35 40 35v60z" fill="#e7b569"/><text x="12" y="22" fill="white" font-size="9">SYNTETISK BILDE</text></svg>'}));
  await page.goto('/organizations');await loginAsEditor(page);
  const grid=page.locator('.editor-card-grid');await expect(grid.locator('article')).toHaveCount(10);
  await expect.poll(()=>grid.locator('img').evaluate((e:HTMLImageElement)=>e.complete&&e.naturalWidth>0)).toBe(true);
  const cards=await grid.locator('article').evaluateAll(es=>es.map(e=>{const r=e.getBoundingClientRect();return{width:Math.round(r.width),height:r.height};}));
  expect(new Set(cards.map(e=>e.width)).size).toBe(1);expect(cards.every(e=>e.height===148)).toBe(true);
  for(const thumb of await grid.locator('.editor-card-thumb').all()) {
    const r=await thumb.boundingBox();expect(r?.width).toBe(76);expect(r?.height).toBe(76);
  }
  await expectTaxonomyColors(grid);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:info.outputPath(`actors-${width}.png`)});
  await grid.getByRole('button',{name:names[0],exact:true}).click();await expectTaxonomyColors(page.getByRole('dialog'));await page.keyboard.press('Escape');
  await page.getByRole('link',{name:'Personer',exact:true}).click();await page.getByRole('searchbox',{name:'Søk personer'}).fill('Alexandra');
  const results=page.locator('.person-results');await expect(results.locator('tbody tr')).toHaveCount(1);await expectTaxonomyColors(results);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:info.outputPath(`people-${width}.png`),fullPage:width!==1920});
  await results.getByRole('button',{name:state.persons[0].full_name,exact:true}).click();await expectTaxonomyColors(page.getByRole('dialog'));
  await page.screenshot({path:info.outputPath(`person-modal-${width}.png`)});
});

test('existing import metadata and suggestions retain distinct taxonomy colors',async({page})=>{
  await setupMockEditorApi(page);
  const job={id:1,tenant:1,source_type:'CSV',import_mode:'ORGANIZATIONS_ONLY',status:'PREVIEWED',filename:'synthetic.csv',config_json:{},summary_json:{rows_total:1},rows_count:1};
  const row={id:1,import_job:1,row_number:1,row_status:'REVIEW_REQUIRED',raw_payload_json:{organization_name:'Syntetisk importaktør',organization_categories:'Musikk',organization_subcategories:'Konsertarrangører',organization_tags:'Etablert'},normalized_payload_json:{},detected_entities_json:{has_organization:true},match_result_json:{},ai_suggestions_json:{suggested_fields:{suggested_categories:{value:['Film']},suggested_subcategories:{value:['Filmlyd']},suggested_tags:{value:['Nettverk']}}},validation_errors_json:[],warnings_json:[],errors_json:[],decisions:[],decision:null};
  await page.route('**/api/tenants/1/export-jobs/',route=>route.fulfill({json:[]}));
  await page.route('**/api/tenants/1/import-jobs/',route=>route.fulfill({json:[job]}));
  await page.route('**/api/tenants/1/import-jobs/1/',route=>route.fulfill({json:job}));
  await page.route('**/api/tenants/1/import-jobs/1/rows/**',route=>route.fulfill({json:{count:1,next:null,previous:null,results:[row]}}));
  await page.goto('/import');await loginAsEditor(page);
  await expect(page.getByText('Syntetisk importaktør',{exact:true})).toBeVisible();
  await expectTaxonomyColors(page.locator('.import-review-table'));
  await expect(page.locator('.import-review-table .mini-pill.suggested')).toHaveCount(3);
  for(const pill of await page.locator('.import-review-table .mini-pill.suggested').all()) await expect(pill).toHaveCSS('border-top-style','dashed');
  await page.getByRole('button',{name:'Review',exact:true}).click();
  const editor=page.locator('.inline-review-editor');
  for(const [kind,color] of Object.entries(colors)) {
    const button=editor.locator(`.suggestion-pill.${kind}`);
    await expect(button).toHaveCSS('background-color',color);
    await expect(button).toHaveCSS('border-top-style','dashed');
  }
  await expect(editor.locator('.tag-chip-edit')).toHaveCSS('background-color',colors.tag);
});
