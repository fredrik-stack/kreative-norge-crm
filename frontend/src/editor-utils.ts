export type SaveState = "idle" | "saving" | "saved" | "error";

export function profileStatus(state: SaveState, dirty: boolean, isNew: boolean, model: "aktør" | "person") {
  if (state === "saving") return { kind: "saving", label: `Lagrer ${model}skjema…` };
  if (state === "error") return { kind: "error", label: "Lagring ikke bekreftet" };
  if (dirty) return { kind: "dirty", label: "Ulagrede profilfelt" };
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

export function parseInternalTags(value: string): string[] {
  return [...new Set(value.split(",").map(name => name.trim()).filter(Boolean))];
}

/** Describe the current draft without changing its classification or tag values. */
export function classificationSummary(
  categories: Array<{ id: number; name: string }>, categoryIds: number[],
  subcategories: Array<{ id: number; name: string }>, subcategoryIds: number[],
  tags: string, internalTags: string,
): string {
  const categoryNames = categories.filter(item => categoryIds.includes(item.id)).map(item => item.name).join(", ");
  const subcategoryNames = subcategories.filter(item => subcategoryIds.includes(item.id)).map(item => item.name).join(", ");
  return [
    categoryNames && `Kategori: ${categoryNames}`,
    subcategoryNames && `Underkategori: ${subcategoryNames}`,
    tags.trim() && `Tags: ${tags.trim()}`,
    internalTags.trim() && `Interne tags: ${internalTags.trim()}`,
  ].filter(Boolean).join(" · ") || "Ingen kategorier eller tags valgt";
}
