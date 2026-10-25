import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../test/server";
import { useEditorData } from "./useEditorData";

async function setup() {
  server.use(http.get('/api/tenants/', () => HttpResponse.json([{id:1,name:'Test',slug:'test',default_phone_region:'NO',current_user_role:'gruppeadmin'}])));
  const hook = renderHook(() => useEditorData());
  await waitFor(() => expect(hook.result.current.tenantDataLoaded).toBe(true));
  act(() => hook.result.current.setSelectedPersonId("new"));
  await waitFor(() => expect(hook.result.current.personDraft.full_name).toBe(""));
  act(() => hook.result.current.setPersonDraft(draft => ({ ...draft, full_name: "Kontakt Test" })));
  return hook;
}
const event = { preventDefault() {} } as React.FormEvent;
const contact = (id: number, type: "EMAIL" | "PHONE", value: string, is_primary = false) => ({
  id, type, value, is_primary, is_public: false, phone_region_used: null, phone_dial_uri: null, phone_country_calling_code_hint: null, created_at: "2026-10-25T12:00:00Z",
});

it("keeps unchanged region baselines clean and blocks region-only saves for primary and extra phones before writes", async()=>{
  server.use(http.get('/api/tenants/',()=>HttpResponse.json([{id:1,name:'Test',slug:'test',default_phone_region:'NO',current_user_role:'gruppeadmin'}])));
  const person={id:20,tenant:1,full_name:'Region Test',title:'',email:null,phone:'070 123 45 67',phone_region_used:'SE',municipality:'',tags:[],categories:[],subcategories:[],contacts:[{...contact(31,'PHONE','070 123 45 67',true),phone_region_used:'SE'},{...contact(32,'PHONE','070 123 45 68'),phone_region_used:'SE'}]};
  server.use(http.get('/api/tenants/1/persons/',()=>HttpResponse.json([person])));
  const {result}=renderHook(()=>useEditorData());
  await waitFor(()=>expect(result.current.personDraft.full_name).toBe('Region Test'));
  expect(result.current.peopleHasUnsavedChanges).toBe(false);
  let writes=0;
  server.use(http.patch('/api/tenants/1/persons/20/',()=>{writes++;return HttpResponse.json(person);}));
  for(const id of [31,32]){
    act(()=>result.current.updatePersonContact(`contact-${id}`,{phone_region:'NO'}));
    expect(result.current.peopleHasUnsavedChanges).toBe(true);
    let ok=true;await act(async()=>{ok=await result.current.saveAllPendingChanges();});
    expect(ok).toBe(false); expect(writes).toBe(0);
    expect(result.current.personFieldErrors[`contact-${id}`]).toMatch(/nummeret endres/);
    act(()=>result.current.onResetPersonDraft());
    expect(result.current.peopleHasUnsavedChanges).toBe(false);
  }
});

it("keeps all contact edits local, includes them in dirty state, and discards locally", async () => {
  const { result } = await setup();
  let writes = 0;
  server.use(http.all('/api/tenants/1/person-contacts/*', () => { writes++; return HttpResponse.json({}); }));
  act(() => result.current.addPersonContact("EMAIL"));
  const key = result.current.personContactRows.slice(-1)[0]!.key;
  act(() => result.current.updatePersonContact(key, { value: "extra@example.invalid", is_public: true }));
  expect(result.current.peopleHasUnsavedChanges).toBe(true);
  expect(writes).toBe(0);
  act(() => result.current.onResetPersonDraft());
  expect(result.current.personContactRows.some(row => row.value === "extra@example.invalid")).toBe(false);
  expect(result.current.peopleHasUnsavedChanges).toBe(false);
  expect(writes).toBe(0);
});

for(const uncertain of [false,true]) it(`does not undo ${uncertain?'unknown':'confirmed'} DELETE after a later failure or local discard`,async()=>{
  const {result}=await setup(); const base=result.current.persons[0];
  let saved={...base,id:77,full_name:'Kontakt Test',email:'one@example.invalid',phone:null,contacts:[contact(91,'EMAIL','one@example.invalid',true)]};
  let failed=false, deletes=0, posts=0;
  server.use(
    http.post('/api/tenants/1/persons/',()=>HttpResponse.json(saved,{status:201})),
    http.delete('/api/tenants/1/person-contacts/91/',()=>{deletes++;saved.contacts=[];return uncertain?HttpResponse.error():new HttpResponse(null,{status:204});}),
    http.patch('/api/tenants/1/persons/77/',async({request})=>{if(!failed){failed=true;return HttpResponse.json({title:['Avvist']},{status:400});}saved={...saved,...await request.json() as object};return HttpResponse.json(saved);}),
    http.post('/api/tenants/1/person-contacts/',()=>{posts++;return HttpResponse.json({});}),
  );
  const key=result.current.personContactRows.find(row=>row.type==='EMAIL')!.key;
  act(()=>result.current.updatePersonContact(key,{value:'one@example.invalid'}));
  await act(async()=>{await result.current.onSubmitPerson(event);});
  act(()=>result.current.updatePersonContact(key,{removed:true}));
  await act(async()=>{await result.current.onSubmitPerson(event);});
  expect(result.current.personSaveState).toBe('error'); expect(deletes).toBe(1);
  act(()=>result.current.updatePersonContact(key,{removed:false}));
  expect(result.current.personContactRows.find(row=>row.key===key)?.removed).toBe(true);
  act(()=>result.current.onResetPersonDraft());
  expect(result.current.personContactRows.some(row=>row.id===91||row.value==='one@example.invalid')).toBe(false);
  expect(result.current.personSaveBlocked).toBe(true);
  act(()=>result.current.setSelectedPersonId('new'));
  act(()=>result.current.setSelectedPersonId(77));
  await waitFor(()=>expect(result.current.persistedPersonId).toBe(77));
  expect(result.current.personSaveBlocked).toBe(true);
  await act(async()=>{await result.current.onSubmitPerson(event);});
  expect(posts).toBe(0); expect(result.current.personSaveState).toBe('error');
});

it('undoing a staged primary removal preserves an existing legacy mismatch without repairing it',async()=>{
  server.use(http.get('/api/tenants/',()=>HttpResponse.json([{id:1,name:'Test',slug:'test',default_phone_region:'NO',current_user_role:'gruppeadmin'}])));
  server.use(http.get('/api/tenants/1/persons/',()=>HttpResponse.json([{id:20,tenant:1,full_name:'Legacy Test',title:'',email:'legacy@example.invalid',phone:null,municipality:'',tags:[],categories:[],subcategories:[],contacts:[contact(31,'EMAIL','contact@example.invalid',true)]}])));
  const {result}=renderHook(()=>useEditorData());
  await waitFor(()=>expect(result.current.personDraft.email).toBe('legacy@example.invalid'));
  act(()=>result.current.updatePersonContact('contact-31',{removed:true}));
  act(()=>result.current.updatePersonContact('contact-31',{removed:false}));
  expect(result.current.personDraft.email).toBe('legacy@example.invalid');
  expect(result.current.peopleHasUnsavedChanges).toBe(false);
});

it("retains Person and contact IDs after a later failure; retry creates neither again", async () => {
  const { result } = await setup();
  const base = result.current.persons[0];
  let personPosts = 0, contactPosts = 0, fail = true;
  let saved = { ...base, id: 77, full_name: "Kontakt Test", email: null, phone: null, contacts: [] as ReturnType<typeof contact>[] };
  const patches: object[] = [];
  server.use(
    http.post('/api/tenants/1/persons/', async ({request}) => { personPosts++; saved = {...saved, ...await request.json() as object}; return HttpResponse.json(saved, {status:201}); }),
    http.patch('/api/tenants/1/persons/77/', async ({request}) => { const payload=await request.json() as object; patches.push(payload); saved={...saved,...payload}; return HttpResponse.json(saved); }),
    http.post('/api/tenants/1/person-contacts/', async ({request}) => {
      contactPosts++; const payload=await request.json() as {type:"EMAIL"|"PHONE"; value:string};
      if (payload.type === "PHONE" && fail) return HttpResponse.json({value:["Avvist i testen"]},{status:400});
      const created=contact(80+contactPosts,payload.type,payload.value); saved.contacts.push(created); return HttpResponse.json(created,{status:201});
    }),
  );
  act(() => { result.current.addPersonContact("EMAIL"); result.current.addPersonContact("PHONE"); });
  const rows=result.current.personContactRows.slice(-2);
  act(() => { result.current.updatePersonContact(rows[0].key,{value:"extra@example.invalid"}); result.current.updatePersonContact(rows[1].key,{value:"+4790012345"}); });
  await act(async () => { await result.current.onSubmitPerson(event); });
  expect(result.current.persistedPersonId).toBe(77);
  expect(result.current.personSaveState).toBe("error");
  expect(result.current.personSaveMessage).toMatch(/Kontakt #81 er lagret/);
  expect(result.current.personContactRows.find(row=>row.key===rows[0].key)?.id).toBe(81);
  fail=false;
  await act(async () => { await result.current.onSubmitPerson(event); });
  expect(personPosts).toBe(1); expect(contactPosts).toBe(3);
  expect(saved.contacts).toHaveLength(2);
  expect(patches[0]).not.toHaveProperty("email"); expect(patches[0]).not.toHaveProperty("phone");
  expect(result.current.personSaveState).toBe("saved"); expect(result.current.peopleHasUnsavedChanges).toBe(false);
});

it("does not retry a POST with unknown outcome, including concurrent submit", async () => {
  const { result } = await setup(); let posts=0; let release!:()=>void;
  const pending=new Promise<void>(resolve=>{release=resolve;});
  server.use(http.post('/api/tenants/1/persons/',async()=>{posts++;await pending;return HttpResponse.error();}));
  let first!:Promise<void>;
  act(()=>{first=result.current.onSubmitPerson(event);});
  await waitFor(()=>expect(posts).toBe(1));
  await act(async()=>{await result.current.onSubmitPerson(event);release();await first;});
  await act(async()=>{await result.current.onSubmitPerson(event);});
  expect(posts).toBe(1); expect(result.current.personSaveBlocked).toBe(true);
  expect(result.current.personSaveMessage).toMatch(/Ukjent opprettingsresultat/);
});

it("reuses server-created main contacts, keeps technical primary flags and stages removal by ID", async () => {
  const {result}=await setup(); const base=result.current.persons[0];
  let saved={...base,id:77,full_name:"Kontakt Test",email:"main@example.invalid",phone:null,contacts:[contact(91,"EMAIL","main@example.invalid",true)]};
  let contactPosts=0; const deleted:number[]=[]; const patches:object[]=[];
  server.use(
    http.post('/api/tenants/1/persons/',()=>HttpResponse.json(saved,{status:201})),
    http.patch('/api/tenants/1/persons/77/',async({request})=>{const payload=await request.json() as object;patches.push(payload);saved={...saved,...payload};return HttpResponse.json(saved);}),
    http.patch('/api/tenants/1/person-contacts/91/',async({request})=>{const payload=await request.json() as object;expect(payload).not.toHaveProperty('is_primary');saved.contacts[0]={...saved.contacts[0],...payload};return HttpResponse.json(saved.contacts[0]);}),
    http.post('/api/tenants/1/person-contacts/',()=>{contactPosts++;return HttpResponse.json({});}),
    http.delete('/api/tenants/1/person-contacts/91/',()=>{deleted.push(91);saved.contacts=[];return new HttpResponse(null,{status:204});}),
  );
  const row=result.current.personContactRows.find(row=>row.type==='EMAIL')!;
  act(()=>result.current.updatePersonContact(row.key,{value:'main@example.invalid',is_public:true}));
  await act(async()=>{await result.current.onSubmitPerson(event);});
  expect(contactPosts).toBe(0); expect(saved.contacts[0].is_primary).toBe(true);expect(saved.contacts[0].is_public).toBe(true);
  act(()=>result.current.updatePersonContact(row.key,{removed:true}));
  expect(deleted).toEqual([]);
  await act(async()=>{await result.current.onSubmitPerson(event);});
  expect(deleted).toEqual([91]); expect(patches.slice(-1)[0]).toHaveProperty('email',null);
});
