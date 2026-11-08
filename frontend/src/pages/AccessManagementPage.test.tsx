import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { AccessManagementPage } from "./AccessManagementPage";
import * as api from "../api";
vi.mock("../api", async () => ({...await vi.importActual("../api"),
  getManagementContext: vi.fn(), acceptSharingAgreement: vi.fn(), revokeSharingAcceptance: vi.fn(),
  getManagedMemberships: vi.fn(), saveManagedMembership: vi.fn(), publishSharingAgreement: vi.fn(),
}));
const context: api.ManagementContext = {enabled:true,published_agreements:[],grants:[],acceptances:[],memberships:[{
  tenant_id:10,tenant_name:"Syntetisk kontor",domain_id:20,role:"leser",
  agreement:{id:30,version:1,text:"Syntetisk avtale\nÆ  ",effective_at:"2026-01-01T00:00:00Z"},
}]};
beforeEach(() => {vi.clearAllMocks();vi.mocked(api.getManagementContext).mockResolvedValue(structuredClone(context));});

it("requires explicit checkbox and binds acceptance to displayed exact version",async () => {
  render(<AccessManagementPage username="synthetic" />);
  const button=await screen.findByRole("button",{name:"Aksepter delingsavtalen"});
  expect(button).toBeDisabled();expect(screen.getByText(/Syntetisk avtale/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("checkbox"));await userEvent.click(button);
  await waitFor(()=>expect(api.acceptSharingAgreement).toHaveBeenCalledWith(20,10,30));
  expect(api.publishSharingAgreement).not.toHaveBeenCalled();
});
it("shows own revocation after membership loss and no management controls",async () => {
  vi.mocked(api.getManagementContext).mockResolvedValue({...context,memberships:[],acceptances:[{id:9,agreement_id:30,domain_id:20,version:1,revoked:false}]});
  render(<AccessManagementPage username="synthetic" />);
  await userEvent.click(await screen.findByRole("button",{name:"Tilbakekall min aksept"}));
  await waitFor(()=>expect(api.revokeSharingAcceptance).toHaveBeenCalledWith(9));
  expect(screen.queryByRole("button",{name:"Lagre medlemskap"})).not.toBeInTheDocument();
});
it("keeps stale acceptance failure visible without automatic retry",async () => {
  vi.mocked(api.acceptSharingAgreement).mockRejectedValue(new api.ApiError(409,"conflict",{code:"STALE_AGREEMENT"}));
  render(<AccessManagementPage username="synthetic" />);
  await screen.findByRole("button",{name:"Aksepter delingsavtalen"});
  await userEvent.click(screen.getByRole("checkbox"));await userEvent.click(screen.getByRole("button",{name:"Aksepter delingsavtalen"}));
  expect(await screen.findByRole("alert")).toHaveTextContent("STALE_AGREEMENT");
  expect(api.acceptSharingAgreement).toHaveBeenCalledTimes(1);
});
it("fails closed when disabled",async () => {
  vi.mocked(api.getManagementContext).mockResolvedValue({enabled:false,published_agreements:[],memberships:[],grants:[],acceptances:[]});
  render(<AccessManagementPage username="synthetic" />);
  expect(await screen.findByText("Tilgangsforvaltning er ikke aktivert.")).toBeInTheDocument();
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
});
