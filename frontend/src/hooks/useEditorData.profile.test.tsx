import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { vi } from "vitest";
import { server } from "../test/server";
import { profileStatus } from "../editor-utils";
import { useEditorData } from "./useEditorData";

async function editor(role = "redigerer") {
  server.use(http.get('/api/tenants/', () => HttpResponse.json([
    { id: 1, name: 'Test', slug: 'test', default_phone_region: 'NO', current_user_role: role },
  ])));
  const hook = renderHook(() => useEditorData());
  await waitFor(() => expect(hook.result.current.tenantDataLoaded).toBe(true));
  await waitFor(() => expect(hook.result.current.selectedOrganization).not.toBeNull());
  return hook;
}
const event = { preventDefault() {} } as React.FormEvent;

it('keeps actor saving state and immediate lock through the final metadata read',async()=>{
  const {result}=await editor();let stored=result.current.selectedOrganization!;
  let release!:()=>void; const gate=new Promise<void>(resolve=>{release=resolve;});
  let metadataRead=false, writes=0;
  server.use(
    http.patch('/api/tenants/1/organizations/10/',async({request})=>{writes++;stored={...stored,...await request.json() as object};return HttpResponse.json(stored);}),
    http.get('/api/tenants/1/organizations/',()=>HttpResponse.json([stored])),
    http.get('/api/tenants/1/tags/',async()=>{metadataRead=true;await gate;return HttpResponse.json([]);}),
  );
  act(()=>result.current.setDraft(draft=>({...draft,name:'Saved while reading metadata'})));
  let save!:Promise<void>;act(()=>{save=result.current.onSubmit(event);});
  await waitFor(()=>expect(metadataRead).toBe(true));
  expect(result.current.saveState).toBe('saving');
  await act(async()=>{await result.current.onSubmit(event);});
  expect(writes).toBe(1);
  await act(async()=>{release();await save;});
  expect(result.current.saveState).toBe('saved');
});

for (const model of ['organization'] as const) {
  const org = model === 'organization';
  it(`${model}: new/reset share tenant region, clear tags/errors/state, preserve separate drafts and issue no writes`, async () => {
    const { result } = await editor();
    act(() => org ? result.current.setSelectedOrgId('new') : result.current.setSelectedPersonId('new'));
    await waitFor(() => expect(org ? result.current.draft.phone_region : result.current.personDraft.phone_region).toBe('NO'));
    expect(org ? result.current.organizationHasUnsavedChanges : result.current.personDraftHasUnsavedChanges).toBe(false);
    act(() => {

      if (org) {
        result.current.setDraft(s => ({ ...s, email: 'invalid', phone_region: 'SE' }));
        result.current.setOrganizationTagInput('new tag');
      } else {
        result.current.setPersonDraft(s => ({ ...s, email: 'invalid', phone_region: 'SE' }));
        result.current.setPersonTagInput('new tag');
      }
    });
    await act(async () => { await (org ? result.current.onSubmit(event) : result.current.onSubmitPerson(event)); });
    expect(org ? result.current.saveState : result.current.personSaveState).toBe('error');
    expect(Object.keys(org ? result.current.organizationFieldErrors : result.current.personFieldErrors).length).toBeGreaterThan(0);
    const globalError = result.current.error;
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    fetchSpy.mockClear();
    act(() => org ? result.current.onResetOrganizationDraft() : result.current.onResetPersonDraft());
    expect(org ? result.current.draft.phone_region : result.current.personDraft.phone_region).toBe('NO');
    expect(org ? result.current.draft.name : result.current.personDraft.full_name).toBe('');
    expect(org ? result.current.organizationTagInput : result.current.personTagInput).toBe('');
    expect(org ? result.current.saveState : result.current.personSaveState).toBe('idle');
    expect(org ? result.current.organizationFieldErrors : result.current.personFieldErrors).toEqual({});
    expect(org ? result.current.organizationHasUnsavedChanges : result.current.personDraftHasUnsavedChanges).toBe(false);

    expect(result.current.error).toBe(globalError);
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it(`${model}: existing reset restores loaded fields/tags and keeps contact guard`, async () => {
    const { result } = await editor();
    await waitFor(() => expect(result.current.personDraft.full_name).not.toBe(''));
    const original = org ? result.current.draft : result.current.personDraft;
    const tags = org ? result.current.organizationTagInput : result.current.personTagInput;
    act(() => {
      if (org) {
        result.current.setDraft(s => ({ ...s, name: 'changed' }));
        result.current.setOrganizationTagInput('changed');
      } else {
        result.current.setPersonDraft(s => ({ ...s, full_name: 'changed' }));
        result.current.setPersonTagInput('changed');
      }

    });
    act(() => org ? result.current.onResetOrganizationDraft() : result.current.onResetPersonDraft());
    expect(org ? result.current.draft : result.current.personDraft).toEqual(original);
    expect(org ? result.current.organizationTagInput : result.current.personTagInput).toBe(tags);
    expect(result.current.personDraftHasUnsavedChanges).toBe(false);
    expect(result.current.contactDraftHasUnsavedChanges).toBe(false);
    expect(result.current.peopleHasUnsavedChanges).toBe(false);
    expect(profileStatus(result.current.personSaveState, result.current.personDraftHasUnsavedChanges, false, 'person').label).toBe('Ingen ulagrede profilfelt');
  });

  it(`${model}: saving blocks reset; error outranks dirty and local reset preserves global error`, async () => {
    const { result } = await editor();
    act(() => org ? result.current.setSelectedOrgId('new') : result.current.setSelectedPersonId('new'));
    let release!: () => void;
    const pending = new Promise<void>(r => { release = r; });
    server.use(http.post(`/api/tenants/1/${org ? 'organizations' : 'persons'}/`, async () => {
      await pending;
      return HttpResponse.json({ detail: 'Unknown outcome' }, { status: 503 });
    }));
    act(() => org
      ? result.current.setDraft(s => ({ ...s, name: 'Pending' }))
      : result.current.setPersonDraft(s => ({ ...s, full_name: 'Pending' })));
    let submit!: Promise<void>;
    act(() => { submit = org ? result.current.onSubmit(event) : result.current.onSubmitPerson(event); });
    await waitFor(() => expect(org ? result.current.saveState : result.current.personSaveState).toBe('saving'));
    act(() => org ? result.current.onResetOrganizationDraft() : result.current.onResetPersonDraft());
    expect(org ? result.current.draft.name : result.current.personDraft.full_name).toBe('Pending');
    await act(async () => { release(); await submit; });
    expect(profileStatus(org ? result.current.saveState : result.current.personSaveState, true, true, org ? 'aktør' : 'person').label).toBe('Lagring ikke bekreftet');
    const error = result.current.error;
    act(() => org ? result.current.onResetOrganizationDraft() : result.current.onResetPersonDraft());
    expect(result.current.error).toBe(error);
  });
}

it('successful save, new edits and profile switch never reuse an old confirmation', async () => {
  const { result } = await editor();
  let stored = result.current.selectedOrganization!;
  server.use(
    http.patch('/api/tenants/1/organizations/10/', async ({ request }) => {
      stored = { ...stored, ...await request.json() as object };
      return HttpResponse.json(stored);
    }),
    http.get('/api/tenants/1/organizations/', () => HttpResponse.json([stored])),
  );
  act(() => result.current.setDraft(s => ({ ...s, name: 'Saved profile' })));
  await act(async () => { await result.current.onSubmit(event); });
  expect(result.current.organizationHasUnsavedChanges).toBe(false);
  act(() => result.current.setDraft(s => ({ ...s, name: 'New edit' })));
  expect(profileStatus('saved', result.current.organizationHasUnsavedChanges, false, 'aktør').label).toBe('Ulagrede profilfelt');
  act(() => result.current.setSelectedOrgId('new'));
  await waitFor(() => expect(result.current.saveState).toBe('idle'));
  expect(profileStatus(result.current.saveState, result.current.organizationHasUnsavedChanges, true, 'aktør').label).toBe('Nytt profilutkast');
});

it('actor deletion requires the existing delete role and never clears a rejected profile', async () => {
  let deletes=0;
  server.use(http.delete('/api/tenants/1/organizations/10/', () => { deletes++; return HttpResponse.json({detail:'Profilen har beskyttet tilhørighet eller historikk og kan ikke slettes.'}, {status:409}); }));
  const denied=await editor();
  await act(async()=>{expect(await denied.result.current.onDeleteOrganization()).toBe(false);});
  expect(deletes).toBe(0); denied.unmount();
  const {result}=await editor('gruppeadmin');
  act(()=>result.current.setDraft(draft=>({...draft,name:'Ulagret navn'})));
  await act(async()=>{expect(await result.current.onDeleteOrganization()).toBe(false);});
  expect(deletes).toBe(1); expect(result.current.draft.name).toBe('Ulagret navn');
  expect(result.current.selectedOrgId).toBe(10);
  expect(result.current.error).toContain('beskyttet tilhørighet');
  expect(result.current.organizationDeleting).toBe(false);
});
it('confirmed actor deletion clears only its cache/links, retains people and excludes competing writes', async () => {
  const {result}=await editor('gruppeadmin');
  const people=result.current.persons;
  let release!:()=>void; const gate=new Promise<void>(resolve=>{release=resolve;}); let deletes=0,patches=0;
  server.use(http.delete('/api/tenants/1/organizations/10/', async()=>{deletes++;await gate;return new HttpResponse(null,{status:204});}),
    http.patch('/api/tenants/1/organizations/10/',()=>{patches++;return HttpResponse.json({});}));
  act(()=>result.current.setDraft(draft=>({...draft,name:'Lokalt utkast'})));
  let deletion!:Promise<boolean>;act(()=>{deletion=result.current.onDeleteOrganization();});
  await waitFor(()=>expect(deletes).toBe(1));
  expect(result.current.organizationDeleting).toBe(true);
  await act(async()=>{await result.current.onSubmit(event);expect(await result.current.onDeleteOrganization()).toBe(false);});
  expect(deletes).toBe(1);expect(patches).toBe(0);
  await act(async()=>{release();expect(await deletion).toBe(true);});
  expect(result.current.organizations.some(org=>org.id===10)).toBe(false);
  expect(result.current.organizationPeople.some(link=>link.organization===10)).toBe(false);
  expect(result.current.persons).toEqual(people);
  expect(result.current.organizationHasUnsavedChanges).toBe(false);
});
