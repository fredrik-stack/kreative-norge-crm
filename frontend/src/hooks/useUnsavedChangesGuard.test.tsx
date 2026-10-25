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
  it("cannot discard or switch tenant while a profile write is still running", async () => {
    const apply=vi.fn(), discard=vi.fn(), save=vi.fn();
    const {result}=renderHook(()=>useUnsavedChangesGuard({hasUnsavedChanges:true,isSaving:true,tenants:[],dirtySummary:[],applyTenantSelection:apply,discardAllPendingChanges:discard,saveAllPendingChanges:save}));
    act(()=>result.current.requestTenantSelection(2));
    expect(result.current.modal.busy).toBe(true);
    act(()=>result.current.modal.onDiscardAndContinue());
    await act(async()=>{await result.current.modal.onSaveAndContinue();});
    expect(apply).not.toHaveBeenCalled(); expect(discard).not.toHaveBeenCalled(); expect(save).not.toHaveBeenCalled();
  });
  it("guards logout, waits for save, stays on failure and runs once on success", async () => {
    let release!: (ok: boolean) => void;
    const save = vi.fn(() => new Promise<boolean>(resolve => { release = resolve; }));
    const logout = vi.fn();
    const { result } = renderHook(() => useUnsavedChangesGuard({hasUnsavedChanges:true,tenants:[],dirtySummary:["Personskjema"],applyTenantSelection:vi.fn(),saveAllPendingChanges:save,discardAllPendingChanges:vi.fn()}));
    act(() => result.current.requestAction("Logg ut", logout));
    let pending!: Promise<void>;
    act(() => { pending=result.current.modal.onSaveAndContinue(); });
    await act(async () => { await result.current.modal.onSaveAndContinue(); });
    expect(save).toHaveBeenCalledTimes(1); expect(logout).not.toHaveBeenCalled();
    await act(async () => { release(false); await pending; });
    expect(result.current.modal.open).toBe(true); expect(logout).not.toHaveBeenCalled();
    act(() => { pending=result.current.modal.onSaveAndContinue(); });
    await act(async () => { release(true); await pending; });
    expect(logout).toHaveBeenCalledTimes(1); expect(result.current.modal.open).toBe(false);
  });

  it("continues a discarded route only once when local baselines become clean", () => {
    blockerState.state="blocked"; blockerState.location={pathname:"/people"};
    const discard=vi.fn();
    const {result,rerender}=renderHook(({dirty})=>useUnsavedChangesGuard({hasUnsavedChanges:dirty,tenants:[],dirtySummary:[],applyTenantSelection:vi.fn(),saveAllPendingChanges:vi.fn(),discardAllPendingChanges:discard}),{initialProps:{dirty:true}});
    act(()=>result.current.modal.onDiscardAndContinue());
    rerender({dirty:false});
    expect(discard).toHaveBeenCalledTimes(1); expect(blockerState.proceed).toHaveBeenCalledTimes(1);
  });
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
        tenants: [{ id: 2, name: "Tenant B", slug: "tenant-b", default_phone_region: null, created_at: "2026-01-01T00:00:00Z", current_user_role: "redigerer" }],
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
        tenants: [{ id: 3, name: "Tenant C", slug: "tenant-c", default_phone_region: null, created_at: "2026-01-01T00:00:00Z", current_user_role: "redigerer" }],
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
