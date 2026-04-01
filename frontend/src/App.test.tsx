import { vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useBlocker: () => ({
      state: "unblocked" as const,
      location: null,
      proceed: vi.fn(),
      reset: vi.fn(),
    }),
  };
});

describe("App integration", () => {
  it("logs in, loads organization data, and reflects dirty state in the UI", async () => {
    window.history.pushState({}, "", "/organizations/10");

    render(<App />);

    await screen.findByRole("heading", { name: "Logg inn" });

    await userEvent.type(screen.getByLabelText("Brukernavn"), "editor");
    await userEvent.type(screen.getByLabelText("Passord"), "secret123");
    await userEvent.click(screen.getByRole("button", { name: "Logg inn" }));

    expect(await screen.findByRole("button", { name: /Kreativ Demo AS/ })).toBeInTheDocument();
    expect(await screen.findByText("Aktør #10")).toBeInTheDocument();

    const nameInput = screen.getByDisplayValue("Kreativ Demo AS");
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, "Kreativ Demo AS (endret)");

    await waitFor(() => {
      expect(screen.getByText("Du har ulagrede endringer i aktørskjemaet.")).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: /^Aktører/ })).toBeInTheDocument();
  });
});
