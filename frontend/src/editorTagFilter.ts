type TagName = { id: number; name: string; slug: string };
export type EditorTagChoice = TagName & { kind: "tag" | "internal"; key: string };

export function editorTagChoices(tags: TagName[], internalTags: TagName[]): EditorTagChoice[] {
  const choices = new Map<string, EditorTagChoice>();
  for (const [kind, items] of [["tag", tags], ["internal", internalTags]] as const) {
    for (const tag of items) choices.set(`${kind}:${tag.id}`, { ...tag, kind, key: `${kind}:${tag.id}` });
  }
  return [...choices.values()].sort((a, b) => a.name.localeCompare(b.name, "nb") || a.kind.localeCompare(b.kind) || a.id - b.id);
}

export function matchesEditorTag(profile: { tags?: TagName[]; internal_tags?: TagName[] }, key: string): boolean {
  return !key || (profile.tags ?? []).some(tag => `tag:${tag.id}` === key)
    || (profile.internal_tags ?? []).some(tag => `internal:${tag.id}` === key);
}

export function editorTagLabel(choice?: EditorTagChoice): string {
  return choice ? `${choice.kind === "internal" ? "intern tag" : "tag"} «${choice.name}»` : "";
}
