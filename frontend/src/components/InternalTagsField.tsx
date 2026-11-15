import { parseInternalTags } from "../editor-utils";
import { useEffect, useState } from "react";
import { getInternalTags } from "../api";
import { Field } from "./Field";
import type { Tag } from "../types";

export function InternalTagsField({ tenantId, value, onChange, disabled, error }: {
  tenantId: number; value: string; onChange: (value: string) => void; disabled?: boolean; error?: string;
}) {
  const [options, setOptions] = useState<Array<Pick<Tag, "id" | "name" | "slug">>>([]);
  const [unavailable, setUnavailable] = useState(false);
  useEffect(() => {
    let cancelled = false;
    setOptions([]); setUnavailable(false);
    void getInternalTags(tenantId).then(tags => { if (!cancelled) setOptions(tags); })
      .catch(() => { if (!cancelled) setUnavailable(true); });
    return () => { cancelled = true; };
  }, [tenantId]);
  const names = parseInternalTags(value);
  return <Field label="Interne tags" name="internal_tag_names" error={error}>
    <input value={value} disabled={disabled} onChange={event => onChange(event.target.value)} placeholder="f.eks. prioritet, partner" />
    <div className="internal-tag-chips" aria-label="Valgte interne tags">{names.map(name => <span className="mini-pill internal-tag" key={name}>{name}</span>)}</div>
    <div className="internal-tag-chips" role="group" aria-label="Eksisterende interne tags">
      {options.filter(tag => !names.includes(tag.name)).slice(0, 8).map(tag => <button type="button" key={tag.id} className="mini-pill internal-tag" disabled={disabled}
        onClick={() => onChange([...names, tag.name].join(", "))}>{tag.name}</button>)}
    </div>
    <small className="meta">Kun i eget Musikkontors Editor. Skill med komma; lagres med profilen.</small>
    {unavailable ? <small className="meta">Taggforslag kunne ikke hentes. Lagrede valg beholdes; du kan skrive navn selv.</small> : null}
  </Field>;
}
