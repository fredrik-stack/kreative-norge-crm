import { http, HttpResponse } from "msw";
import { vi } from "vitest";
import { server } from "./test/server";
import { AUTH_ERROR_EVENT, ApiError, patchPerson } from "./api";

it("returns a rejected write to the mounted form without triggering automatic logout", async () => {
  const expired=vi.fn(); window.addEventListener(AUTH_ERROR_EVENT,expired);
  server.use(http.patch('/api/tenants/1/persons/20/',()=>HttpResponse.json({detail:'Denied'},{status:403})));
  await expect(patchPerson(1,20,{title:'Keep draft'})).rejects.toBeInstanceOf(ApiError);
  expect(expired).not.toHaveBeenCalled(); window.removeEventListener(AUTH_ERROR_EVENT,expired);
});
