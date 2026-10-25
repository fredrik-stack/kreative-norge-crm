import { useEffect, useMemo, useRef, useState } from "react";
import { useBlocker } from "react-router-dom";
import type { Tenant } from "../types";

export function useUnsavedChangesGuard(params: {
  hasUnsavedChanges: boolean;
  tenants: Tenant[];
  dirtySummary: string[];
  applyTenantSelection: (tenantId: number | null) => void;
  saveAllPendingChanges: () => Promise<boolean>;
  discardAllPendingChanges: () => void;
  isSaving?: boolean;
}) {
  const { hasUnsavedChanges, tenants, dirtySummary, applyTenantSelection, saveAllPendingChanges, discardAllPendingChanges } =
    params;
  const blocker = useBlocker(hasUnsavedChanges);
  const continuedLocation = useRef<unknown>(null);
  const [pendingTenantId, setPendingTenantId] = useState<number | null>(null);
  const [continuing, setBusy] = useState(false);
  const busy = continuing || Boolean(params.isSaving);
  const actionInFlight = useRef(false);
  const [pendingAction, setPendingAction] = useState<{ label: string; run: () => void } | null>(null);
  const stayButtonRef = useRef<HTMLButtonElement | null>(null);
  const leaveButtonRef = useRef<HTMLButtonElement | null>(null);
  const saveButtonRef = useRef<HTMLButtonElement | null>(null);

  const showRouteBlockModal = blocker.state === "blocked";
  const showTenantBlockModal = pendingTenantId !== null;
  const open = showRouteBlockModal || showTenantBlockModal || pendingAction !== null;
  const targetKind: "route" | "tenant" | "action" | null = pendingAction ? "action" : showRouteBlockModal
    ? "route"
    : showTenantBlockModal
      ? "tenant"
      : null;
  const canSaveAndContinue = !busy;

  useEffect(() => {
    if (!open) return;
    stayButtonRef.current?.focus();
  }, [open]);

  function proceedRoute() {
    if (blocker.state !== "blocked" || continuedLocation.current === blocker.location) return;
    continuedLocation.current = blocker.location;
    blocker.proceed?.();
  }

  useEffect(() => {
    // A completed save can race the router's blocker subscription. Both this
    // effect and explicit continuation consume the same blocked location once.
    if (!hasUnsavedChanges && !busy) proceedRoute();
  }, [blocker, hasUnsavedChanges, busy]);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        if (busy) return;
        setPendingAction(null);
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
  }, [blocker, busy, open, showRouteBlockModal, showTenantBlockModal]);

  const targetLabel = useMemo(() => {
    if (pendingAction) return pendingAction.label;
    if (showRouteBlockModal && blocker.location) return blocker.location.pathname;
    if (showTenantBlockModal && pendingTenantId !== null) {
      const tenant = tenants.find((t) => t.id === pendingTenantId);
      return tenant ? `${tenant.name} (${tenant.slug})` : `Tenant #${pendingTenantId}`;
    }
    return null;
  }, [blocker.location, pendingAction, pendingTenantId, showRouteBlockModal, showTenantBlockModal, tenants]);

  function continuePending() {
    if (pendingAction) { pendingAction.run(); setPendingAction(null); }
    if (showRouteBlockModal) proceedRoute();
    if (showTenantBlockModal) {
      applyTenantSelection(pendingTenantId);
      setPendingTenantId(null);
    }
  }

  async function onSaveAndContinue() {
    if (actionInFlight.current || params.isSaving) return;
    actionInFlight.current = true;
    setBusy(true);
    try {
      if (!hasUnsavedChanges || await saveAllPendingChanges()) continuePending();
    } finally { actionInFlight.current = false; setBusy(false); }
  }

  function onDiscardAndContinue() {
    if (actionInFlight.current || params.isSaving) return;
    actionInFlight.current = true;
    try { discardAllPendingChanges(); continuePending(); }
    finally { actionInFlight.current = false; }
  }

  function onStay() {
    if (actionInFlight.current) return;
    setPendingAction(null);
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
    requestAction(label: string, run: () => void) {
      if (hasUnsavedChanges) setPendingAction({ label, run });
      else run();
    },
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
