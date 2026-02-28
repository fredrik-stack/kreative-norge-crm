import { useEffect, useMemo, useRef, useState } from "react";
import { useBlocker } from "react-router-dom";
import type { Tenant } from "../types";

export function useUnsavedChangesGuard(params: {
  hasUnsavedChanges: boolean;
  tenants: Tenant[];
  dirtySummary: string[];
  applyTenantSelection: (tenantId: number | null) => void;
  saveAllPendingChanges: () => Promise<boolean>;
}) {
  const { hasUnsavedChanges, tenants, dirtySummary, applyTenantSelection, saveAllPendingChanges } =
    params;
  const blocker = useBlocker(hasUnsavedChanges);
  const [pendingTenantId, setPendingTenantId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const stayButtonRef = useRef<HTMLButtonElement | null>(null);
  const leaveButtonRef = useRef<HTMLButtonElement | null>(null);
  const saveButtonRef = useRef<HTMLButtonElement | null>(null);

  const showRouteBlockModal = blocker.state === "blocked";
  const showTenantBlockModal = pendingTenantId !== null;
  const open = showRouteBlockModal || showTenantBlockModal;
  const targetKind: "route" | "tenant" | null = showRouteBlockModal
    ? "route"
    : showTenantBlockModal
      ? "tenant"
      : null;
  const canSaveAndContinue = hasUnsavedChanges && !busy;

  useEffect(() => {
    if (!open) return;
    stayButtonRef.current?.focus();
  }, [open]);

  useEffect(() => {
    // A blocked route can become safe immediately after a save updates local baselines.
    // In that case, continue the blocked navigation automatically instead of leaving
    // a stale modal open over the UI.
    if (hasUnsavedChanges) return;
    if (blocker.state === "blocked") {
      blocker.proceed?.();
    }
  }, [blocker, hasUnsavedChanges]);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        if (showRouteBlockModal) blocker.reset?.();
        if (showTenantBlockModal) setPendingTenantId(null);
        return;
      }
      if (event.key !== "Tab") return;
      const focusables = [stayButtonRef.current, leaveButtonRef.current, saveButtonRef.current].filter(
        Boolean,
      ) as HTMLButtonElement[];
      if (focusables.length === 0) return;
      const active = document.activeElement as HTMLElement | null;
      const currentIndex = focusables.findIndex((el) => el === active);
      const nextIndex = event.shiftKey
        ? currentIndex <= 0
          ? focusables.length - 1
          : currentIndex - 1
        : currentIndex >= focusables.length - 1
          ? 0
          : currentIndex + 1;
      event.preventDefault();
      focusables[nextIndex]?.focus();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [blocker, open, showRouteBlockModal, showTenantBlockModal]);

  const targetLabel = useMemo(() => {
    if (showRouteBlockModal && blocker.location) return blocker.location.pathname;
    if (showTenantBlockModal && pendingTenantId !== null) {
      const tenant = tenants.find((t) => t.id === pendingTenantId);
      return tenant ? `${tenant.name} (${tenant.slug})` : `Tenant #${pendingTenantId}`;
    }
    return null;
  }, [blocker.location, pendingTenantId, showRouteBlockModal, showTenantBlockModal, tenants]);

  async function onSaveAndContinue() {
    if (!hasUnsavedChanges) {
      if (showRouteBlockModal) blocker.proceed?.();
      if (showTenantBlockModal) {
        applyTenantSelection(pendingTenantId);
        setPendingTenantId(null);
      }
      return;
    }
    setBusy(true);
    const ok = await saveAllPendingChanges();
    setBusy(false);
    if (!ok) return;
    if (showRouteBlockModal) blocker.proceed?.();
    if (showTenantBlockModal) {
      applyTenantSelection(pendingTenantId);
      setPendingTenantId(null);
    }
  }

  function onDiscardAndContinue() {
    if (showRouteBlockModal) blocker.proceed?.();
    if (showTenantBlockModal) {
      applyTenantSelection(pendingTenantId);
      setPendingTenantId(null);
    }
  }

  function onStay() {
    if (showRouteBlockModal) blocker.reset?.();
    if (showTenantBlockModal) setPendingTenantId(null);
  }

  function requestTenantSelection(nextTenantId: number | null) {
    if (hasUnsavedChanges) {
      setPendingTenantId(nextTenantId);
      return;
    }
    applyTenantSelection(nextTenantId);
  }

  return {
    modal: {
      open,
      busy,
      canSaveAndContinue,
      targetLabel,
      targetKind,
      dirtySummary,
      onStay,
      onSaveAndContinue,
      onDiscardAndContinue,
      stayButtonRef,
      saveButtonRef,
      leaveButtonRef,
    },
    requestTenantSelection,
  };
}
