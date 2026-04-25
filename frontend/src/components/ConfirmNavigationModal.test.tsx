import { createRef, type ComponentProps } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ConfirmNavigationModal } from "./ConfirmNavigationModal";

function modalProps(overrides: Partial<ComponentProps<typeof ConfirmNavigationModal>> = {}) {
  return {
    open: true,
    busy: false,
    canSaveAndContinue: true,
    targetLabel: "/people/12",
    targetKind: "route" as const,
    dirtySummary: ["Aktørskjema", "Ny kontakt (ikke lagret)"],
    onStay: vi.fn(),
    onSaveAndContinue: vi.fn(),
    onDiscardAndContinue: vi.fn(),
    stayButtonRef: createRef<HTMLButtonElement>(),
    saveButtonRef: createRef<HTMLButtonElement>(),
    leaveButtonRef: createRef<HTMLButtonElement>(),
    ...overrides,
  };
}

describe("ConfirmNavigationModal", () => {
  it("renders dirty summary and target label", () => {
    render(<ConfirmNavigationModal {...modalProps()} />);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Aktørskjema")).toBeInTheDocument();
    expect(screen.getByText("Ny kontakt (ikke lagret)")).toBeInTheDocument();
    expect(screen.getByText(/Neste side/)).toBeInTheDocument();
    expect(screen.getByText("/people/12")).toBeInTheDocument();
  });

  it("wires button callbacks", async () => {
    const props = modalProps();
    render(<ConfirmNavigationModal {...props} />);

    await userEvent.click(screen.getByRole("button", { name: "Bli her" }));
    await userEvent.click(screen.getByRole("button", { name: "Lagre og fortsett" }));
    await userEvent.click(screen.getByRole("button", { name: "Forlat uten å lagre" }));

    expect(props.onStay).toHaveBeenCalledTimes(1);
    expect(props.onSaveAndContinue).toHaveBeenCalledTimes(1);
    expect(props.onDiscardAndContinue).toHaveBeenCalledTimes(1);
  });
});
