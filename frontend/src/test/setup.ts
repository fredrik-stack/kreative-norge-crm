import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll, beforeEach } from "vitest";
import { resetMockEditorData, resetMockSession } from "./handlers";
import { server } from "./server";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
beforeEach(() => {
  resetMockSession();
  resetMockEditorData();
  document.cookie = "csrftoken=test-csrf-token; path=/";
});
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
