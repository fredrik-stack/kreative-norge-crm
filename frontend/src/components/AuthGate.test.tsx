import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AUTH_ERROR_EVENT } from "../api";
import { AuthGate } from "./AuthGate";

describe("AuthGate", () => {
  it("shows login form, logs in via API, and renders children", async () => {
    render(
      <AuthGate>
        {({ username }) => <div>Innlogget bruker: {username}</div>}
      </AuthGate>,
    );

    expect(await screen.findByRole("heading", { name: "Logg inn" })).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Brukernavn"), "editor");
    await userEvent.type(screen.getByLabelText("Passord"), "secret123");
    await userEvent.click(screen.getByRole("button", { name: "Logg inn" }));

    expect(await screen.findByText("Innlogget bruker: editor")).toBeInTheDocument();
  });

  it("shows backend login error from API", async () => {
    render(
      <AuthGate>
        {({ username }) => <div>Innlogget bruker: {username}</div>}
      </AuthGate>,
    );

    await screen.findByRole("heading", { name: "Logg inn" });
    await userEvent.type(screen.getByLabelText("Brukernavn"), "editor");
    await userEvent.type(screen.getByLabelText("Passord"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Logg inn" }));

    await waitFor(() => {
      expect(screen.getByText("Ugyldig brukernavn eller passord.")).toBeInTheDocument();
    });
  });

  it("returns to login when auth error event is emitted", async () => {
    render(
      <AuthGate>
        {({ username }) => <div>Innlogget bruker: {username}</div>}
      </AuthGate>,
    );

    await screen.findByRole("heading", { name: "Logg inn" });
    await userEvent.type(screen.getByLabelText("Brukernavn"), "editor");
    await userEvent.type(screen.getByLabelText("Passord"), "secret123");
    await userEvent.click(screen.getByRole("button", { name: "Logg inn" }));
    await screen.findByText("Innlogget bruker: editor");

    act(() => {
      window.dispatchEvent(
        new CustomEvent(AUTH_ERROR_EVENT, { detail: { status: 403, path: "/api/tenants/" } }),
      );
    });

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Logg inn" })).toBeInTheDocument();
      expect(screen.getByText("Innloggingen er utløpt. Logg inn på nytt.")).toBeInTheDocument();
    });
  });
});
