export type SaveState = "idle" | "saving" | "saved" | "error";

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
