import { renderHook, act } from "@testing-library/react";
import { vi } from "vitest";

const blockerState = {
  state: "unblocked" as "unblocked" | "blocked",
  location: null as { pathname: string } | null,
  proceed: vi.fn(),
  reset: vi.fn(),
};

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useBlocker: () => blockerState,
  };
});

import { useUnsavedChangesGuard } from "./useUnsavedChangesGuard";

describe("useUnsavedChangesGuard", () => {
  beforeEach(() => {
    blockerState.state = "unblocked";
    blockerState.location = null;
    blockerState.proceed.mockClear();
    blockerState.reset.mockClear();
  });

  it("opens tenant confirmation modal when changing tenant with unsaved changes", () => {
    const applyTenantSelection = vi.fn();
    const saveAllPendingChanges = vi.fn().mockResolvedValue(true);
    const discardAllPendingChanges = vi.fn();

    const { result } = renderHook(() =>
      useUnsavedChangesGuard({
        hasUnsavedChanges: true,
        tenants: [{ id: 2, name: "Tenant B", slug: "tenant-b", created_at: "2026-01-01T00:00:00Z" }],
        dirtySummary: ["Personskjema"],
        applyTenantSelection,
        saveAllPendingChanges,
        discardAllPendingChanges,
      }),
    );

    act(() => {
      result.current.requestTenantSelection(2);
    });

    expect(result.current.modal.open).toBe(true);
    expect(result.current.modal.targetKind).toBe("tenant");
    expect(result.current.modal.targetLabel).toContain("Tenant B");
    expect(result.current.modal.dirtySummary).toEqual(["Personskjema"]);
    expect(applyTenantSelection).not.toHaveBeenCalled();
  });

  it("can discard and continue tenant switch", () => {
    const applyTenantSelection = vi.fn();
    const discardAllPendingChanges = vi.fn();

    const { result } = renderHook(() =>
      useUnsavedChangesGuard({
        hasUnsavedChanges: true,
        tenants: [{ id: 3, name: "Tenant C", slug: "tenant-c", created_at: "2026-01-01T00:00:00Z" }],
        dirtySummary: [],
        applyTenantSelection,
        saveAllPendingChanges: vi.fn().mockResolvedValue(true),
        discardAllPendingChanges,
      }),
    );

    act(() => {
      result.current.requestTenantSelection(3);
    });
    act(() => {
      result.current.modal.onDiscardAndContinue();
    });

    expect(applyTenantSelection).toHaveBeenCalledWith(3);
    expect(discardAllPendingChanges).toHaveBeenCalled();
  });
});
