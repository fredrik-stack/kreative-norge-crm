import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { vi } from "vitest";
import { server } from "../test/server";
import { profileStatus } from "../editor-utils";
import { useEditorData } from "./useEditorData";

async function editor() {
  server.use(http.get('/api/tenants/', () => HttpResponse.json([
    { id: 1, name: 'Test', slug: 'test', default_phone_region: 'NO', current_user_role: 'redigerer' },
  ])));
  const hook = renderHook(() => useEditorData());
  await waitFor(() => expect(hook.result.current.tenantDataLoaded).toBe(true));
  await waitFor(() => expect(hook.result.current.selectedOrganization).not.toBeNull());
  return hook;
}
const event = { preventDefault() {} } as React.FormEvent;

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
