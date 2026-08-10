import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  approveOfficialImage: vi.fn(),
  discoverOfficialImages: vi.fn(),
  getCandidatePreview: vi.fn(),
  getOrganizationImageState: vi.fn(),
  getRenditionPreview: vi.fn(),
  processOfficialImage: vi.fn(),
}));

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return { ...actual, ...api };
});

import { OrganizationImagePanel } from "./OrganizationsPage";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}

describe("OrganizationImagePanel", () => {
  beforeEach(() => {
    Object.values(api).forEach((mock) => mock.mockReset());
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn() });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
    vi.spyOn(URL, "createObjectURL").mockReturnValueOnce("blob:active-square");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    api.getOrganizationImageState.mockResolvedValue({
      expected_revision: 0,
      active_selection: null,
    });
    api.discoverOfficialImages.mockResolvedValue([
      {
        candidate_ref: "candidate-ref",
        source_type: "open_graph",
        source_label: "Open Graph",
        source_domain: "official.example",
        provider: "official_website",
        width: 1400,
        height: 1000,
        technical_status: "ready_for_preview",
      },
    ]);
    api.getCandidatePreview.mockResolvedValue(new Blob(["candidate"], { type: "image/webp" }));
    api.getRenditionPreview.mockResolvedValue(new Blob(["rendition"], { type: "image/webp" }));
    api.processOfficialImage.mockResolvedValue({
      approval_ref: "approval-ref",
      rendition_preview_ref: "preview-ref",
      asset_id: 1,
      rendition_set_id: 2,
      variants: ["square", "landscape", "share"],
      warnings: ["untagged_assumed_srgb"],
      status: "created",
    });
    api.approveOfficialImage.mockResolvedValue({ selection_id: 3, revision: 1, status: "active", event_id: 4 });
  });

  it("runs discovery, selected processing, three previews, and explicit approval", async () => {
    vi.spyOn(URL, "createObjectURL")
      .mockReturnValueOnce("blob:candidate")
      .mockReturnValueOnce("blob:square")
      .mockReturnValueOnce("blob:landscape")
      .mockReturnValueOnce("blob:share")
      .mockReturnValueOnce("blob:active-square")
      .mockReturnValueOnce("blob:active-landscape")
      .mockReturnValueOnce("blob:active-share");
    api.getOrganizationImageState
      .mockResolvedValueOnce({ expected_revision: 0, active_selection: null })
      .mockResolvedValueOnce({
        expected_revision: 1,
        active_selection: {
          id: 3,
          revision: 1,
          status: "active",
          kind: "asset",
          alt_text: "Offisielt foto",
          public_credit: "Fotograf",
          rendition_preview_ref: "active-preview-ref",
          variants: ["square", "landscape", "share"],
        },
      });

    render(<OrganizationImagePanel tenantId={1} organizationId={10} organizationName="Kreativ Demo AS" />);
    expect(await screen.findByText("Ingen aktiv bildeselection.")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Finn bilder" }));
    expect(await screen.findByText("official.example")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Open Graph/ }));
    await userEvent.click(screen.getByRole("button", { name: "Prosesser valgt bilde" }));

    expect(await screen.findByLabelText("Intern processing-preview")).toBeInTheDocument();
    expect(api.getRenditionPreview).toHaveBeenCalledTimes(3);
    expect(screen.getByText(/untagged_assumed_srgb/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/Alt-tekst/), "Offisielt foto");
    await userEvent.type(screen.getByLabelText("Offentlig kreditering (valgfritt)"), "Fotograf");
    await userEvent.click(screen.getByRole("button", { name: "Godkjenn og lås bilde" }));

    await waitFor(() => expect(api.approveOfficialImage).toHaveBeenCalledWith(1, 10, {
      approval_ref: "approval-ref",
      expected_revision: 0,
      alt_text: "Offisielt foto",
      public_credit: "Fotograf",
    }));
    expect(await screen.findByText("Aktivt låst bilde · revisjon 1")).toBeInTheDocument();
  });

  it("shows controlled discovery errors", async () => {
    api.discoverOfficialImages.mockRejectedValue(new Error("network"));
    render(<OrganizationImagePanel tenantId={1} organizationId={10} organizationName="Kreativ Demo AS" />);
    await screen.findByText("Ingen aktiv bildeselection.");
    await userEvent.click(screen.getByRole("button", { name: "Finn bilder" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Bildehandlingen kunne ikke fullføres");
  });

  it("does not send focus when Logo is selected", async () => {
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:test");
    render(<OrganizationImagePanel tenantId={1} organizationId={10} organizationName="Kreativ Demo AS" />);
    await screen.findByText("Ingen aktiv bildeselection.");
    await userEvent.click(screen.getByRole("button", { name: "Finn bilder" }));
    await userEvent.click(await screen.findByRole("button", { name: /Open Graph/ }));
    await userEvent.selectOptions(screen.getByLabelText("Bildetype"), "logo");
    expect(screen.queryByLabelText(/Fokus X/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Prosesser valgt bilde" }));
    await waitFor(() => expect(api.processOfficialImage).toHaveBeenCalledWith(1, 10, {
      candidate_ref: "candidate-ref",
      image_kind: "logo",
    }));
  });

  it("keeps late preview responses scoped to the organization that started them", async () => {
    const latePreview = deferred<Blob>();
    vi.mocked(URL.createObjectURL).mockReturnValue("blob:late-a");
    api.getOrganizationImageState.mockImplementation(async (_tenantId: number, organizationId: number) => (
      organizationId === 10
        ? {
            expected_revision: 1,
            active_selection: {
              id: 1,
              revision: 1,
              status: "active",
              kind: "asset",
              alt_text: "Bilde fra organisasjon A",
              public_credit: "",
              rendition_preview_ref: "preview-a",
              variants: ["square", "landscape", "share"],
            },
          }
        : { expected_revision: 0, active_selection: null }
    ));
    api.getRenditionPreview.mockReturnValue(latePreview.promise);

    const { rerender } = render(
      <OrganizationImagePanel
        key="1:10"
        tenantId={1}
        organizationId={10}
        organizationName="Organisasjon A"
      />,
    );
    await waitFor(() => expect(api.getRenditionPreview).toHaveBeenCalledTimes(3));

    rerender(
      <OrganizationImagePanel
        key="1:11"
        tenantId={1}
        organizationId={11}
        organizationName="Organisasjon B"
      />,
    );
    expect(await screen.findByText("Ingen aktiv bildeselection.")).toBeInTheDocument();

    latePreview.resolve(new Blob(["late-a"], { type: "image/webp" }));
    await waitFor(() => expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:late-a"));
    expect(screen.queryByText("Bilde fra organisasjon A")).not.toBeInTheDocument();
    expect(screen.getByText("Ingen aktiv bildeselection.")).toBeInTheDocument();
  });

  it("requires new processing after focus or image kind changes", async () => {
    vi.mocked(URL.createObjectURL).mockReturnValue("blob:test");
    render(<OrganizationImagePanel tenantId={1} organizationId={10} organizationName="Kreativ Demo AS" />);
    await screen.findByText("Ingen aktiv bildeselection.");
    await userEvent.click(screen.getByRole("button", { name: "Finn bilder" }));
    await userEvent.click(await screen.findByRole("button", { name: /Open Graph/ }));
    await userEvent.click(screen.getByRole("button", { name: "Prosesser valgt bilde" }));
    expect(await screen.findByRole("button", { name: "Godkjenn og lås bilde" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Fokus X/), { target: { value: "0.6" } });
    expect(screen.queryByRole("button", { name: "Godkjenn og lås bilde" })).not.toBeInTheDocument();
    expect(api.approveOfficialImage).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "Prosesser valgt bilde" }));
    expect(await screen.findByRole("button", { name: "Godkjenn og lås bilde" })).toBeInTheDocument();
    expect(api.processOfficialImage).toHaveBeenCalledTimes(2);

    await userEvent.selectOptions(screen.getByLabelText("Bildetype"), "logo");
    expect(screen.queryByRole("button", { name: "Godkjenn og lås bilde" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Prosesser valgt bilde" }));
    expect(await screen.findByRole("button", { name: "Godkjenn og lås bilde" })).toBeInTheDocument();
    expect(api.processOfficialImage).toHaveBeenCalledTimes(3);
  });
});
