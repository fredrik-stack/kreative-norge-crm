import { vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import type { ImportJob } from "./types";

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

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    uploadImportJobFile: vi.fn(async (tenantId: number, importJobId: number): Promise<ImportJob> => ({
      id: importJobId,
      tenant: tenantId,
      created_by: 1,
      source_type: "CSV",
      import_mode: "COMBINED",
      status: "UPLOADED",
      filename: "import.csv",
      file: "/media/import.csv",
      summary_json: {},
      config_json: {},
      preview_report_file: null,
      error_report_file: null,
      committed_at: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      rows_count: 0,
    })),
  };
});

describe("App integration", () => {
  it("logs in, loads organization data, and reflects dirty state in the UI", async () => {
    window.history.pushState({}, "", "/organizations");

    render(<App />);

    await screen.findByRole("heading", { name: "Logg inn" });

    await userEvent.type(screen.getByLabelText("Brukernavn"), "editor");
    await userEvent.type(screen.getByLabelText("Passord"), "secret123");
    await userEvent.click(screen.getByRole("button", { name: "Logg inn" }));

    await userEvent.click(await screen.findByRole("button", { name: "Rediger" }));
    expect(await screen.findByDisplayValue("Kreativ Demo AS")).toBeInTheDocument();

    const nameInput = screen.getByDisplayValue("Kreativ Demo AS");
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, "Kreativ Demo AS (endret)");

    await waitFor(() => {
      expect(screen.getByText("Du har ulagrede endringer i aktørskjemaet.")).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: /^Aktører/ })).toBeInTheDocument();
  });

  it("supports the import and export page flow", async () => {
    window.history.pushState({}, "", "/import-export");

    render(<App />);

    await screen.findByRole("heading", { name: "Logg inn" });

    await userEvent.type(screen.getByLabelText("Brukernavn"), "editor");
    await userEvent.type(screen.getByLabelText("Passord"), "secret123");
    await userEvent.click(screen.getByRole("button", { name: "Logg inn" }));

    await userEvent.click(await screen.findByRole("link", { name: "Import / eksport" }));
    expect(await screen.findByRole("heading", { name: "Importjobber" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Opprett importjobb" }));
    expect(await screen.findByText("#1")).toBeInTheDocument();

    const fileInput = screen.getByLabelText("Last opp CSV/XLSX");
    const csvFile = new File(["organization_name,person_full_name\nKreativ Demo AS,Ada Editor\n"], "import.csv", {
      type: "text/csv",
    });
    await userEvent.upload(fileInput, csvFile);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Last opp" })).toBeEnabled();
    });
    await userEvent.click(screen.getByRole("button", { name: "Last opp" }));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Kjør preview" })).toBeEnabled();
    });
    await userEvent.click(screen.getByRole("button", { name: "Kjør preview" }));

    expect(await screen.findByText("Rader totalt")).toBeInTheDocument();
    expect(await screen.findByText("Aktører opprett")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Åpne" })).toBeInTheDocument();
    });
    await userEvent.click(screen.getByRole("button", { name: "Åpne" }));
    expect(await screen.findByRole("heading", { name: /Kreativ Demo AS/i })).toBeInTheDocument();
    expect(screen.getByText("AI-forslag")).toBeInTheDocument();
    expect(screen.getByText("organization_website_url")).toBeInTheDocument();
    await userEvent.click(screen.getAllByRole("button", { name: "Godta" })[0]);
    await userEvent.click(screen.getAllByRole("button", { name: "Ignorer" })[1]);
    await userEvent.click(screen.getByRole("button", { name: "Lagre vurderinger" }));
    await waitFor(() => {
      expect(screen.queryByText("AI-forslag")).not.toBeInTheDocument();
    });
    await userEvent.click(screen.getByRole("button", { name: "Åpne" }));
    expect(await screen.findByText("Akseptert")).toBeInTheDocument();
    expect(screen.getByText("Ignorert")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Lukk" }));

    await userEvent.click(screen.getByRole("button", { name: "Opprett eksportjobb" }));
    expect(await screen.findByText(/SEARCH_RESULTS/)).toBeInTheDocument();
  });
});
