export type SaveState = "idle" | "saving" | "saved" | "error";

export function profileStatus(state: SaveState, dirty: boolean, isNew: boolean, model: "aktør" | "person") {
  if (state === "saving") return { kind: "saving", label: `Lagrer ${model}skjema…` };
  if (state === "error") return { kind: "error", label: "Lagring ikke bekreftet" };
  if (dirty) return { kind: "idle", label: "Ulagrede profilfelt" };
  if (state === "saved") return { kind: "saved", label: `${model === "aktør" ? "Aktør" : "Person"}skjema lagret` };
  return { kind: "idle", label: isNew ? "Nytt profilutkast" : "Ingen ulagrede profilfelt" };
}

export function saveLabel(state: SaveState): string {
  switch (state) {
    case "saving":
      return "Lagrer";
    case "saved":
      return "Lagret";
    case "error":
      return "Feil";
    default:
      return "Klar";
  }
}
