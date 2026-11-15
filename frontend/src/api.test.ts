import { http, HttpResponse } from "msw";
import { vi } from "vitest";
import { server } from "./test/server";
import { AUTH_ERROR_EVENT, ApiError, patchPerson, getInternalTags, getTags } from "./api";

it("returns a rejected write to the mounted form without triggering automatic logout", async () => {
  const expired=vi.fn(); window.addEventListener(AUTH_ERROR_EVENT,expired);
  server.use(http.patch('/api/tenants/1/persons/20/',()=>HttpResponse.json({detail:'Denied'},{status:403})));
  await expect(patchPerson(1,20,{title:'Keep draft'})).rejects.toBeInstanceOf(ApiError);
  expect(expired).not.toHaveBeenCalled(); window.removeEventListener(AUTH_ERROR_EVENT,expired);
});

for (const status of [403, 401]) {
  it(`private dictionary ${status} preserves permission denial and only expires real authentication`, async () => {
    const expired = vi.fn(); window.addEventListener(AUTH_ERROR_EVENT, expired);
    try {
      server.use(http.get('/api/tenants/1/internal-tags/', () => HttpResponse.json({detail: 'Synthetic denied'}, {status})));
      await expect(getInternalTags(1)).rejects.toMatchObject({status});
      expect(expired).toHaveBeenCalledTimes(status === 401 ? 1 : 0);
    } finally { window.removeEventListener(AUTH_ERROR_EVENT, expired); }
  });
}
it('ordinary read 403 keeps the existing session error contract', async () => {
  const expired = vi.fn(); window.addEventListener(AUTH_ERROR_EVENT, expired);
  try {
    server.use(http.get('/api/tenants/1/tags/', () => HttpResponse.json({detail: 'Synthetic denied'}, {status: 403})));
    await expect(getTags(1)).rejects.toMatchObject({status: 403});
    expect(expired).toHaveBeenCalledTimes(1);
  } finally { window.removeEventListener(AUTH_ERROR_EVENT, expired); }
});
