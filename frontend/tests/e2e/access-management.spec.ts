import { test, expect, type Page } from "@playwright/test";
import { loginAsEditor, setupMockEditorApi } from "./mockEditorApi";

async function start(page: Page, type: "member" | "manager" | "publisher", stale = false) {
  await setupMockEditorApi(page);
  const context = {enabled:true,published_agreements:[] as unknown[],grants:[] as unknown[],acceptances:[] as unknown[],memberships:[] as unknown[]};
  if (type === "member") context.memberships=[{tenant_id:1,tenant_name:"Syntetisk kontor",domain_id:10,role:"leser",
    agreement:{id:20,version:1,text:"Syntetisk avtale.\nBare testdata.",effective_at:"2026-01-01T00:00:00Z"}}];
  if (type === "manager") context.grants=[{action:"manage_tenant_memberships",domain_id:10,tenant_id:1,tenant_name:"Syntetisk kontor",domain_name:"Syntetisk"}];
  if (type === "publisher") context.grants=[{action:"publish_sharing_agreement",domain_id:10,tenant_id:null,tenant_name:null,domain_name:"Syntetisk"}];
  let members: unknown[]=[];
  await page.route("**/api/auth/access-management/**",async route => {
    const path=new URL(route.request().url()).pathname;
    const data=route.request().method()==="POST" ? route.request().postDataJSON() : null;
    const json=(body: unknown,status=200)=>route.fulfill({status,json:body});
    if(path==="/api/auth/access-management/") return json(context);
    if(path.endsWith("/memberships/")) {
      if(data){members=[{...data,expected_updated_at:"2026-11-08T14:00:00+00:00"}];return json(members[0]);}
      return json(members);
    }
    if(path.endsWith("/agreements/")) {
      context.published_agreements=[{id:20,domain_id:10,...data}];return json({agreement_id:20,version:data.version},201);
    }
    if(path.endsWith("/acceptances/")) {
      if(stale)return json({code:"STALE_AGREEMENT"},409);
      context.acceptances=[{id:30,agreement_id:20,domain_id:10,version:1,revoked:false}];return json({acceptance_id:30},201);
    }
    if(path.endsWith("/revoke/")){context.acceptances=[];return json({revoked:true});}
    return json({code:"ACCESS_DENIED"},403);
  });
  await page.goto("/organizations");await loginAsEditor(page);
  await page.getByRole("link",{name:"Tilgang og avtale"}).click();
}

test("explicit own acceptance and withdrawal, desktop and mobile",async ({page},testInfo)=>{
  await start(page,"member");
  const accept=page.getByRole("button",{name:"Aksepter delingsavtalen"});await expect(accept).toBeDisabled();
  await expect(page.getByText(/Bare testdata/)).toBeVisible();
  await page.screenshot({path:testInfo.outputPath("member.png"),fullPage:true});
  await page.getByRole("checkbox").check();await accept.click();
  await expect(page.getByText("Du har akseptert denne versjonen.",{exact:false})).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  await page.getByRole("button",{name:"Tilbakekall min aksept"}).click();
  await expect(page.getByRole("button",{name:"Aksepter delingsavtalen"})).toBeVisible();
  await page.screenshot({path:testInfo.outputPath("mobile.png"),fullPage:true});
});
test("stale agreement is visible and never silently retried",async ({page},testInfo)=>{
  await start(page,"member",true);await page.getByRole("checkbox").check();
  await page.getByRole("button",{name:"Aksepter delingsavtalen"}).click();
  await expect(page.getByRole("alert")).toContainText("STALE_AGREEMENT");
  await expect(page.getByRole("button",{name:"Aksepter delingsavtalen"})).toBeEnabled();
});
test("manager can add existing synthetic account without publication authority",async ({page},testInfo)=>{
  await start(page,"manager");await page.getByLabel("Eksisterende brukernavn").fill("synthetic-member");
  await page.getByRole("button",{name:"Lagre medlemskap"}).click();
  await expect(page.getByRole("list").getByText(/synthetic-member/)).toBeVisible();
  await expect(page.getByRole("button",{name:"Publiser godkjent versjon"})).toHaveCount(0);
  await page.screenshot({path:testInfo.outputPath("manager.png"),fullPage:true});
});
test("publisher must affirm legal approval and can read back exact publication",async ({page},testInfo)=>{
  await start(page,"publisher");
  await expect(page.getByRole("button",{name:"Publiser godkjent versjon"})).toBeDisabled();
  await page.getByLabel("Godkjent avtaletekst").fill("Syntetisk juridisk tekst – ingen reell avtale.");
  await page.getByLabel("Gjelder fra (lokal tid)").fill("2026-11-08T15:00");
  await page.getByLabel("Referanse til juridisk godkjenning").fill("SYNTHETIC-ONLY");
  await page.getByRole("checkbox").check();await page.getByRole("button",{name:"Publiser godkjent versjon"}).click();
  await page.getByText(/Publisert i domene 10/).click();
  await expect(page.getByText("Juridisk referanse: SYNTHETIC-ONLY")).toBeVisible();
  await expect(page.getByRole("button",{name:"Lagre medlemskap"})).toHaveCount(0);
  await page.screenshot({path:testInfo.outputPath("publisher.png"),fullPage:true});
});
