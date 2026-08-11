import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  approveOrganizationImage: vi.fn(),
  createDirectUrlCandidate: vi.fn(),
  discoverOfficialImages: vi.fn(),
  getCandidatePreview: vi.fn(),
  getImageSearchContext: vi.fn(),
  getOrganizationImageState: vi.fn(),
  getRenditionPreview: vi.fn(),
  processOrganizationImage: vi.fn(),
  processUploadedOrganizationImage: vi.fn(),
  searchBraveImages: vi.fn(),
}));

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return { ...actual, ...api };
});

import { calculateCoverCrop, OrganizationImagePanel } from "./OrganizationsPage";
import { ApiError } from "../api";

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
    api.processOrganizationImage.mockResolvedValue({
      approval_ref: "approval-ref",
      rendition_preview_ref: "preview-ref",
      asset_id: 1,
      rendition_set_id: 2,
      variants: ["square", "landscape", "share"],
      warnings: ["untagged_assumed_srgb"],
      status: "created",
    });
    api.processUploadedOrganizationImage.mockResolvedValue({
      approval_ref: "upload-approval-ref",
      rendition_preview_ref: "upload-preview-ref",
      asset_id: 5,
      rendition_set_id: 6,
      variants: ["square", "landscape", "share"],
      warnings: [],
      status: "created",
    });
    api.approveOrganizationImage.mockResolvedValue({ selection_id: 3, revision: 1, status: "active", event_id: 4 });
    api.getImageSearchContext.mockResolvedValue({
      suggested_query: "Kreativ Demo AS Oslo",
      query_sources: ["organization_name", "municipality"],
      municipalities: ["Oslo"],
      categories: [{ id: 100, name: "Musikk" }],
      people: [{ id: 20, name: "Ada Editor" }],
    });
    api.searchBraveImages.mockResolvedValue({
      search_query: "Kreativ Demo AS Oslo",
      query_sources: ["organization_name", "municipality"],
      candidates: [],
    });
    api.createDirectUrlCandidate.mockResolvedValue({
      candidate_ref: "url-candidate-ref",
      source_type: "pasted_url",
      source_label: "Direkte bilde-URL",
      source_domain: "images.example",
      source_title: null,
      source_publisher: null,
      provider: "pasted_url",
      width: 1600,
      height: 1000,
      technical_status: "ready_for_preview",
    });
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
    expect(await screen.findByText("Ingen aktivt valgt bilde ennå.")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Finn bilder" }));
    expect(await screen.findByText("official.example")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Open Graph/ }));
    await userEvent.click(screen.getByRole("button", { name: "Prosesser valgt bilde" }));

    expect(await screen.findByLabelText("Serverens bildeformater")).toBeInTheDocument();
    expect(api.getRenditionPreview).toHaveBeenCalledTimes(3);
    expect(screen.getByText(/untagged_assumed_srgb/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/Alt-tekst/), "Offisielt foto");
    await userEvent.type(screen.getByLabelText("Offentlig kreditering (valgfritt)"), "Fotograf");
    await userEvent.click(screen.getByRole("button", { name: "Godkjenn og lås bilde" }));

    await waitFor(() => expect(api.approveOrganizationImage).toHaveBeenCalledWith(1, 10, {
      approval_ref: "approval-ref",
      expected_revision: 0,
      alt_text: "Offisielt foto",
      public_credit: "Fotograf",
    }));
    expect(await screen.findByText("Aktivt bilde")).toBeInTheDocument();
    expect(screen.getByText("Revisjon 1")).toBeInTheDocument();
  });

  it("shows controlled discovery errors", async () => {
    api.discoverOfficialImages.mockRejectedValue(new Error("network"));
    render(<OrganizationImagePanel tenantId={1} organizationId={10} organizationName="Kreativ Demo AS" />);
    await screen.findByText("Ingen aktivt valgt bilde ennå.");
    await userEvent.click(screen.getByRole("button", { name: "Finn bilder" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Bildehandlingen kunne ikke fullføres");
  });

  it("does not send focus when Logo is selected", async () => {
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:test");
    render(<OrganizationImagePanel tenantId={1} organizationId={10} organizationName="Kreativ Demo AS" />);
    await screen.findByText("Ingen aktivt valgt bilde ennå.");
    await userEvent.click(screen.getByRole("button", { name: "Finn bilder" }));
    await userEvent.click(await screen.findByRole("button", { name: /Open Graph/ }));
    await userEvent.selectOptions(screen.getByLabelText("Bildetype"), "logo");
    expect(screen.getByText("Logo viser hele motivet uten beskjæring.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Zoom")).not.toBeInTheDocument();
    expect(screen.queryByText("Finjuster utsnitt")).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Forhåndsvisning av hele logoen" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Prosesser valgt bilde" }));
    await waitFor(() => expect(api.processOrganizationImage).toHaveBeenCalledWith(1, 10, {
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
    expect(await screen.findByText("Ingen aktivt valgt bilde ennå.")).toBeInTheDocument();

    latePreview.resolve(new Blob(["late-a"], { type: "image/webp" }));
    await waitFor(() => expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:late-a"));
    expect(screen.queryByText("Bilde fra organisasjon A")).not.toBeInTheDocument();
    expect(screen.getByText("Ingen aktivt valgt bilde ennå.")).toBeInTheDocument();
  });

  it("requires new processing after focus or image kind changes", async () => {
    vi.mocked(URL.createObjectURL).mockReturnValue("blob:test");
    render(<OrganizationImagePanel tenantId={1} organizationId={10} organizationName="Kreativ Demo AS" />);
    await screen.findByText("Ingen aktivt valgt bilde ennå.");
    await userEvent.click(screen.getByRole("button", { name: "Finn bilder" }));
    await userEvent.click(await screen.findByRole("button", { name: /Open Graph/ }));
    await userEvent.click(screen.getByRole("button", { name: "Prosesser valgt bilde" }));
    expect(await screen.findByRole("button", { name: "Godkjenn og lås bilde" })).toBeInTheDocument();

    await userEvent.click(within(screen.getByRole("group", { name: "Horisontalt" })).getByRole("button", { name: "Høyre" }));
    expect(screen.queryByRole("button", { name: "Godkjenn og lås bilde" })).not.toBeInTheDocument();
    expect(api.approveOrganizationImage).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "Prosesser valgt bilde" }));
    expect(await screen.findByRole("button", { name: "Godkjenn og lås bilde" })).toBeInTheDocument();
    expect(api.processOrganizationImage).toHaveBeenCalledTimes(2);

    await userEvent.selectOptions(screen.getByLabelText("Bildetype"), "logo");
    expect(screen.queryByRole("button", { name: "Godkjenn og lås bilde" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Prosesser valgt bilde" }));
    expect(await screen.findByRole("button", { name: "Godkjenn og lås bilde" })).toBeInTheDocument();
    expect(api.processOrganizationImage).toHaveBeenCalledTimes(3);
  });

  it("uses presets and precise focus and zoom in the same live crop recipe", async () => {
    vi.mocked(URL.createObjectURL).mockReturnValue("blob:test");
    render(<OrganizationImagePanel tenantId={1} organizationId={10} organizationName="Kreativ Demo AS" />);
    await screen.findByText("Ingen aktivt valgt bilde ennå.");
    await userEvent.click(screen.getByRole("button", { name: "Finn bilder" }));
    await userEvent.click(await screen.findByRole("button", { name: /Open Graph/ }));

    const previews = screen.getAllByRole("img", { name: /Live crop-preview/ });
    previews.forEach((preview) => {
      Object.defineProperty(preview, "naturalWidth", { configurable: true, value: 1600 });
      Object.defineProperty(preview, "naturalHeight", { configurable: true, value: 900 });
      fireEvent.load(preview);
    });
    const initialStyles = previews.map((preview) => preview.getAttribute("style"));

    await userEvent.click(screen.getByText("Finjuster utsnitt"));
    fireEvent.change(screen.getByLabelText("Horisontal plassering"), { target: { value: "0.37" } });
    fireEvent.change(screen.getByLabelText("Vertikal plassering"), { target: { value: "0.68" } });
    fireEvent.change(screen.getByLabelText("Zoom"), { target: { value: "1.75" } });

    expect(screen.getByText("Horisontal plassering: 37 %")).toBeInTheDocument();
    expect(screen.getByText("Vertikal plassering: 68 %")).toBeInTheDocument();
    expect(screen.getByText("Zoom: 175 %")).toBeInTheDocument();
    previews.forEach((preview, index) => expect(preview.getAttribute("style")).not.toBe(initialStyles[index]));

    await userEvent.click(screen.getByRole("button", { name: "Prosesser valgt bilde" }));
    await waitFor(() => expect(api.processOrganizationImage).toHaveBeenCalledWith(1, 10, {
      candidate_ref: "candidate-ref",
      image_kind: "photo",
      focus_x: 0.37,
      focus_y: 0.68,
      zoom: 1.75,
    }));

    await userEvent.click(screen.getByRole("button", { name: "Tilbakestill utsnitt" }));
    expect(screen.getByLabelText("Horisontal plassering")).toHaveValue("0.5");
    expect(screen.getByLabelText("Vertikal plassering")).toHaveValue("0.5");
    expect(screen.getByLabelText("Zoom")).toHaveValue("1");
    expect(within(screen.getByRole("group", { name: "Horisontalt" })).getByRole("button", { name: "Midt" })).toHaveAttribute("aria-pressed", "true");
    expect(within(screen.getByRole("group", { name: "Vertikalt" })).getByRole("button", { name: "Midt" })).toHaveAttribute("aria-pressed", "true");
  });

  it("runs direct URL through private preview, live crop, processing, and blank-alt approval", async () => {
    vi.mocked(URL.createObjectURL).mockReturnValue("blob:test");
    render(<OrganizationImagePanel tenantId={1} organizationId={10} organizationName="Kreativ Demo AS" />);
    await screen.findByText("Ingen aktivt valgt bilde ennå.");

    expect(screen.queryByRole("button", { name: "Lim inn bilde-URL" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Finn bilder" }));
    await userEvent.click(screen.getByRole("button", { name: "Lim inn bilde-URL" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Direkte bilde-URL" }), "https://images.example/photo.jpg");
    await userEvent.click(screen.getByRole("button", { name: "Hent bilde" }));

    expect(api.createDirectUrlCandidate).toHaveBeenCalledWith(1, 10, "https://images.example/photo.jpg");
    expect(api.getCandidatePreview).toHaveBeenCalledWith(1, 10, "url-candidate-ref", { original: true });
    const urlCandidate = await screen.findByRole("button", { name: /Direkte bilde-URL/ });
    expect(screen.queryByRole("button", { name: "Prosesser valgt bilde" })).not.toBeInTheDocument();
    await userEvent.click(urlCandidate);
    expect(api.getCandidatePreview.mock.calls.filter((call) => call[2] === "url-candidate-ref")).toHaveLength(1);

    const horizontal = screen.getByRole("group", { name: "Horisontalt" });
    const vertical = screen.getByRole("group", { name: "Vertikalt" });
    await userEvent.click(within(horizontal).getByRole("button", { name: "Høyre" }));
    await userEvent.click(within(vertical).getByRole("button", { name: "Bunn" }));
    expect(screen.getByText("Foto fyller hele bildeflaten og kan derfor beskjæres. Bruk fokus og zoom for å styre utsnittet.")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Prosesser valgt bilde" }));
    await waitFor(() => expect(api.processOrganizationImage).toHaveBeenCalledWith(1, 10, {
      candidate_ref: "url-candidate-ref",
      image_kind: "photo",
      focus_x: 1,
      focus_y: 1,
      zoom: 1,
    }));
    expect(await screen.findByRole("textbox", { name: /Alt-tekst \(valgfritt\)/ })).toHaveValue("");
    await userEvent.click(screen.getByRole("button", { name: "Godkjenn og lås bilde" }));
    await waitFor(() => expect(api.approveOrganizationImage).toHaveBeenCalledWith(1, 10, {
      approval_ref: "approval-ref",
      expected_revision: 0,
      alt_text: "",
      public_credit: "",
    }));
  });

  it("shows backend search context, explicit refinements, exact manual query, and reset", async () => {
    vi.mocked(URL.createObjectURL).mockReturnValue("blob:test");
    api.getImageSearchContext.mockResolvedValue({
      suggested_query: "Kreativ Demo AS",
      query_sources: ["organization_name"],
      municipalities: ["Oslo", "Bodø"],
      categories: [{ id: 100, name: "Musikk" }],
      people: [{ id: 20, name: "Ada Editor" }],
    });
    api.searchBraveImages.mockResolvedValue({
      search_query: "Kreativ Demo AS Bodø konsert",
      query_sources: ["manual_edit"],
      candidates: [{
        candidate_ref: "brave-ref",
        source_type: "brave_image_search",
        source_label: "Bildesøk",
        source_domain: "publisher.example",
        source_title: "Kreativ Demo på scenen",
        source_publisher: null,
        provider: "brave_image_search",
        width: 1800,
        height: 1200,
        technical_status: "ready_for_preview",
      }],
    });

    render(<OrganizationImagePanel tenantId={1} organizationId={10} organizationName="Kreativ Demo AS" />);
    await screen.findByText("Ingen aktivt valgt bilde ennå.");
    await userEvent.click(screen.getByRole("button", { name: "Finn bilder" }));
    await userEvent.click(screen.getByRole("button", { name: "Søk etter flere bilder" }));

    expect(await screen.findByText(
      "Bildesøket utføres via Brave Search. Søketeksten sendes til Brave og kan lagres der i opptil 90 dager. Ikke skriv sensitiv eller intern informasjon i søket.",
    )).toBeInTheDocument();

    const query = await screen.findByLabelText("Forslått søk");
    expect(query).toHaveValue("Kreativ Demo AS");
    expect((query as HTMLInputElement).value).not.toContain("tags");
    await userEvent.click(within(screen.getByRole("group", { name: "Refiner med sted" })).getByRole("button", { name: "Bodø" }));
    await userEvent.click(within(screen.getByRole("group", { name: "Legg til kategori" })).getByRole("button", { name: "Musikk" }));
    await userEvent.click(within(screen.getByRole("group", { name: "Søk med tilknyttet person" })).getByRole("button", { name: "Ada Editor" }));
    expect(query).toHaveValue("Kreativ Demo AS Bodø Musikk Ada Editor");

    await userEvent.clear(query);
    await userEvent.type(query, "Kreativ Demo AS Bodø konsert");
    expect(within(screen.getByLabelText("Bildesøk")).getByText(/Basert på:/).parentElement).toHaveTextContent(
      "redigert av redaktør",
    );
    await userEvent.click(screen.getByRole("button", { name: "Søk" }));
    await waitFor(() => expect(api.searchBraveImages).toHaveBeenCalledWith(1, 10, {
      query: "Kreativ Demo AS Bodø konsert",
      municipality: null,
      category_id: null,
      person_id: null,
      query_edited: true,
    }));
    expect(await screen.findByText("Kreativ Demo på scenen")).toBeInTheDocument();
    expect(screen.getByText("Bildesøk viser forslag fra nettet. Kontroller at bildet kan brukes før du godkjenner det.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Prosesser valgt bilde" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Tilbakestill til forslag" }));
    expect(screen.getByLabelText("Forslått søk")).toHaveValue("Kreativ Demo AS");
  });

  it("uses the original Brave image for live crop and gates processing while it loads", async () => {
    const originalPreview = deferred<Blob>();
    vi.mocked(URL.createObjectURL)
      .mockReset()
      .mockReturnValueOnce("blob:brave-grid-thumbnail")
      .mockReturnValueOnce("blob:brave-original");
    api.discoverOfficialImages.mockResolvedValue([]);
    api.searchBraveImages.mockResolvedValue({
      search_query: "Kreativ Demo AS Oslo",
      query_sources: ["organization_name", "municipality"],
      candidates: [{
        candidate_ref: "brave-ref",
        source_type: "brave_image_search",
        source_label: "Bildesøk",
        source_domain: "publisher.example",
        source_title: "Kreativ Demo på scenen",
        source_publisher: "Eksempelavisen",
        provider: "brave_image_search",
        width: 1800,
        height: 1200,
        technical_status: "ready_for_preview",
      }],
    });
    api.getCandidatePreview.mockImplementation(
      async (
        _tenantId: number,
        _organizationId: number,
        _candidateRef: string,
        options?: { original?: boolean },
      ) => options?.original
        ? originalPreview.promise
        : new Blob(["thumbnail"], { type: "image/webp" }),
    );

    render(<OrganizationImagePanel tenantId={1} organizationId={10} organizationName="Kreativ Demo AS" />);
    await screen.findByText("Ingen aktivt valgt bilde ennå.");
    await userEvent.click(screen.getByRole("button", { name: "Finn bilder" }));
    await userEvent.click(screen.getByRole("button", { name: "Søk etter flere bilder" }));
    await screen.findByLabelText("Forslått søk");
    await userEvent.click(screen.getByRole("button", { name: "Søk" }));

    const candidate = await screen.findByRole("button", { name: /Kreativ Demo på scenen/ });
    expect(screen.getByText("Eksempelavisen · publisher.example")).toBeInTheDocument();
    await waitFor(() => expect(api.getCandidatePreview).toHaveBeenCalledWith(1, 10, "brave-ref"));
    await userEvent.click(candidate);
    expect(api.getCandidatePreview).toHaveBeenCalledWith(1, 10, "brave-ref", { original: true });
    expect(await screen.findByRole("status")).toHaveTextContent("Henter originalbilde for live crop");
    expect(screen.queryByRole("button", { name: "Prosesser valgt bilde" })).not.toBeInTheDocument();

    await act(async () => {
      originalPreview.resolve(new Blob(["original"], { type: "image/webp" }));
    });
    expect(await screen.findByRole("button", { name: "Prosesser valgt bilde" })).toBeInTheDocument();
    screen.getAllByRole("img", { name: /Live crop-preview/ }).forEach((preview) => {
      expect(preview).toHaveAttribute("src", "blob:brave-original");
    });
  });

  it("creates a browser-local upload candidate and sends the selected file only at processing", async () => {
    vi.mocked(URL.createObjectURL).mockReturnValue("blob:upload");
    render(<OrganizationImagePanel tenantId={1} organizationId={10} organizationName="Kreativ Demo AS" />);
    await screen.findByText("Ingen aktivt valgt bilde ennå.");
    await userEvent.click(screen.getByRole("button", { name: "Finn bilder" }));
    await userEvent.click(screen.getByRole("button", { name: "Last opp bilde" }));

    const file = new File(["image-bytes"], "scene.webp", { type: "image/webp" });
    await userEvent.upload(screen.getByLabelText("Velg JPEG-, PNG- eller WebP-bilde"), file);
    const uploadCandidate = await screen.findByRole("button", { name: /Lastet opp/ });
    expect(screen.queryByRole("button", { name: "Prosesser valgt bilde" })).not.toBeInTheDocument();
    expect(api.processUploadedOrganizationImage).not.toHaveBeenCalled();

    await userEvent.click(uploadCandidate);
    expect(screen.getAllByRole("img", { name: /Live crop-preview/ })).toHaveLength(3);
    await userEvent.click(screen.getByRole("button", { name: "Prosesser valgt bilde" }));
    await waitFor(() => expect(api.processUploadedOrganizationImage).toHaveBeenCalledWith(1, 10, {
      file,
      image_kind: "photo",
      focus_x: 0.5,
      focus_y: 0.5,
      zoom: 1,
    }));
  });

  it("maps an ingress 413 upload response to the Norwegian size limit", async () => {
    vi.mocked(URL.createObjectURL).mockReturnValue("blob:upload");
    api.processUploadedOrganizationImage.mockRejectedValue(
      new ApiError(413, "API 413", "Request Entity Too Large"),
    );
    render(<OrganizationImagePanel tenantId={1} organizationId={10} organizationName="Kreativ Demo AS" />);
    await screen.findByText("Ingen aktivt valgt bilde ennå.");
    await userEvent.click(screen.getByRole("button", { name: "Finn bilder" }));
    await userEvent.click(screen.getByRole("button", { name: "Last opp bilde" }));

    const file = new File(["image-bytes"], "scene.webp", { type: "image/webp" });
    await userEvent.upload(screen.getByLabelText("Velg JPEG-, PNG- eller WebP-bilde"), file);
    await userEvent.click(await screen.findByRole("button", { name: /Lastet opp/ }));
    await userEvent.click(screen.getByRole("button", { name: "Prosesser valgt bilde" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Bildet er for stort. Velg en fil på maks 15 MB.",
    );
  });

  it("maps direct HTML responses to Norwegian without exposing raw backend detail", async () => {
    vi.mocked(URL.createObjectURL).mockReturnValue("blob:test");
    api.getCandidatePreview.mockImplementation(
      async (_tenantId: number, _organizationId: number, candidateRef: string) => {
        if (candidateRef === "url-candidate-ref") {
          throw new ApiError(400, "API 400", { code: "content_type", detail: "Remote response has an unsupported content type." });
        }
        return new Blob(["candidate"], { type: "image/webp" });
      },
    );
    render(<OrganizationImagePanel tenantId={1} organizationId={10} organizationName="Kreativ Demo AS" />);
    await screen.findByText("Ingen aktivt valgt bilde ennå.");
    await userEvent.click(screen.getByRole("button", { name: "Finn bilder" }));
    await userEvent.click(screen.getByRole("button", { name: "Lim inn bilde-URL" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Direkte bilde-URL" }), "https://example.com/page");
    await userEvent.click(screen.getByRole("button", { name: "Hent bilde" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Lenken peker ikke direkte til et støttet bilde.");
    expect(screen.queryByText(/unsupported content type/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Direkte bilde-URL.*Velg bilde/ })).not.toBeInTheDocument();
  });

  it("limits candidate preview fetching to four concurrent requests", async () => {
    vi.mocked(URL.createObjectURL).mockReturnValue("blob:test");
    const previews = Array.from({ length: 6 }, () => deferred<Blob>());
    api.discoverOfficialImages.mockResolvedValue(
      previews.map((_, index) => ({
        candidate_ref: `candidate-${index}`,
        source_type: "open_graph",
        source_label: `Open Graph ${index}`,
        source_domain: "official.example",
        source_title: null,
        source_publisher: null,
        provider: "official_website",
        width: 1400,
        height: 1000,
        technical_status: "ready_for_preview",
      })),
    );
    api.getCandidatePreview.mockImplementation((_tenantId: number, _organizationId: number, candidateRef: string) => {
      const index = Number(candidateRef.split("-")[1]);
      return previews[index].promise;
    });

    render(<OrganizationImagePanel tenantId={1} organizationId={10} organizationName="Kreativ Demo AS" />);
    await screen.findByText("Ingen aktivt valgt bilde ennå.");
    await userEvent.click(screen.getByRole("button", { name: "Finn bilder" }));
    await waitFor(() => expect(api.getCandidatePreview).toHaveBeenCalledTimes(4));
    await act(async () => {
      previews[0].resolve(new Blob(["preview"], { type: "image/webp" }));
    });
    await waitFor(() => expect(api.getCandidatePreview).toHaveBeenCalledTimes(5));
    await act(async () => {
      previews.slice(1).forEach((preview) => preview.resolve(new Blob(["preview"], { type: "image/webp" })));
    });
  });
});

describe("calculateCoverCrop", () => {
  it.each([
    [[1600, 900], [512, 512], 0.5, 0.5, 1, { left: 350, top: 0, width: 900, height: 900 }],
    [[1600, 900], [512, 512], 0, 0, 2, { left: 0, top: 0, width: 450, height: 450 }],
    [[1600, 900], [512, 512], 1, 1, 2, { left: 1150, top: 450, width: 450, height: 450 }],
    [[1000, 1600], [512, 512], 0.5, 0.5, 1, { left: 0, top: 300, width: 1000, height: 1000 }],
    [[1600, 900], [800, 450], 0.5, 0.5, 2, { left: 400, top: 225, width: 800, height: 450 }],
  ] as const)("matches the server crop contract for %#", (source, target, focusX, focusY, zoom, expected) => {
    expect(calculateCoverCrop(source, target, focusX, focusY, zoom)).toEqual(expected);
  });
});
