import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, createPerson, createPersonContact, deletePersonContact, patchPerson, patchPersonContact, type PersonPayload } from "../api";
import type { Person, PersonContact } from "../types";
import type { SaveState } from "../editor-utils";
import { initialPhoneRegion } from "../components/PhoneRegionSelect";

export type PersonContactRow = {
  key: string; id?: number; type: "EMAIL" | "PHONE"; value: string;
  phone_region: string | null; is_primary: boolean; is_public: boolean;
  removed?: boolean; removedMainValue?: string | null; deleted?: boolean; mainClearPending?: boolean;
  deleteUncertain?: boolean; unknown?: boolean; baseline?: PersonContact;
};

// A session-local write ledger. Confirmed identities survive every later failure.
// Unknown POST outcomes deliberately have no automatic retry or value matching.
export function usePersonForm(options: {
  tenantId: number | null; selectedId: number | "new" | null; person: Person | null;
  region: string | null; empty: PersonPayload;
  normalize: (draft: PersonPayload) => PersonPayload;
  validate: (draft: PersonPayload) => Partial<Record<string, string>>;
  resolveTags: (tenantId: number, input: string) => Promise<number[]>;
  select: (id: number) => void;
  remember: (person: Person) => void;
  setError: (error: string | null) => void;
}) {
  const { tenantId, selectedId, person, region, empty, normalize, validate, resolveTags, select, remember, setError } = options;
  const [personDraft, setPersonDraft] = useState(empty);
  const [personTagInput, setPersonTagInput] = useState("");
  const [personContactRows, setRows] = useState<PersonContactRow[]>([]);
  const [personSaveState, setState] = useState<SaveState>("idle");
  const [personFieldErrors, setErrors] = useState<Partial<Record<string, string>>>({});
  const [personLastSavedAt, setLastSaved] = useState<string | null>(null);
  const [personSaveMessage, setMessage] = useState<string | null>(null);
  const [persistedPersonId, setPersistedId] = useState<number | null>(null);
  const [unknownCreate, setUnknownCreate] = useState(false);
  const identity = useRef("");
  const baseline = useRef(empty);
  const baselineTags = useRef("");
  const knownPerson = useRef<Person | null>(null);
  const writing = useRef(false);
  const unknownPost = useRef(false);
  const unresolvedDeletes = useRef(new Map<string, { ids: number[]; mainTypes: Array<"EMAIL" | "PHONE"> }>());
  const sequence = useRef(0);

  function rowsFor(value: Person | null): PersonContactRow[] {
    const unresolved = value ? unresolvedDeletes.current.get(`${tenantId}:${value.id}`) : undefined;
    const contacts = (value?.contacts ?? []).filter(contact => !unresolved?.ids.includes(contact.id));
    const rows: PersonContactRow[] = contacts.map(contact => ({
      key: `contact-${contact.id}`, id: contact.id, type: contact.type, value: contact.value,
      phone_region: initialPhoneRegion(contact.value, contact.phone_region_used, region) || null,
      is_primary: contact.is_primary, is_public: contact.is_public, baseline: contact,
    }));
    for (const type of ["EMAIL", "PHONE"] as const) {
      if (unresolved?.mainTypes.includes(type)) continue;
      if (!rows.some(row => row.type === type && row.is_primary)) {
        const field = type === "EMAIL" ? "email" : "phone";
        // Empty entry preserves the existing Person main-field create contract.
        rows.unshift({ key: `main-${type}`, type, value: value?.[field] ?? "",
          phone_region: type === "PHONE" ? initialPhoneRegion(value?.phone, value?.phone_region_used, region) || null : null,
          is_primary: true, is_public: false });
      }
    }
    return rows;
  }

  function hydrate(value: Person | null) {
    const payload: PersonPayload = value ? {
      ...empty, ...Object.fromEntries(Object.keys(empty).filter(key => key in value).map(key => [key, value[key as keyof Person] ?? ""])),
      phone_region: initialPhoneRegion(value.phone, value.phone_region_used, region) || null,
      tag_ids: (value.tags ?? []).map(tag => tag.id),
      category_ids: [...new Set([...(value.categories ?? []).map(item => item.id), ...(value.subcategories ?? []).map(item => item.category.id)])],
      subcategory_ids: (value.subcategories ?? []).map(item => item.id),
    } : { ...empty, phone_region: region };
    baseline.current = normalize(payload);
    baselineTags.current = (value?.tags ?? []).map(tag => tag.name).join(", ");
    knownPerson.current = value; setPersistedId(value?.id ?? null);
    setPersonDraft(payload); setPersonTagInput(baselineTags.current); setRows(rowsFor(value));
    const needsRead = Boolean(value && unresolvedDeletes.current.has(`${tenantId}:${value.id}`));
    setState(needsRead ? "error" : "idle"); setErrors({});
    setMessage(needsRead ? "En tidligere fjerning er delvis gjennomført eller ikke bekreftet. Oppdater siden for å lese faktisk lagret resultat før du redigerer videre." : null);
    setUnknownCreate(needsRead); unknownPost.current = needsRead;
  }

  useEffect(() => {
    const nextIdentity = `${tenantId}:${selectedId}`;
    if (identity.current === nextIdentity || (typeof selectedId === "number" && !person)) return;
    identity.current = nextIdentity;
    hydrate(selectedId === "new" ? null : person);
    // Same-ID server updates must never overwrite an unfinished local save.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId, selectedId, person]);

  function updatePersonContact(key: string, patch: Partial<PersonContactRow>) {
    const row = personContactRows.find(item => item.key === key);
    if (patch.removed === false && (row?.deleted || row?.deleteUncertain)) return;
    if (row?.type === "PHONE" && patch.value?.trim().startsWith("+")) patch = { ...patch, phone_region: null };
    if (patch.removed && row?.is_primary) patch = { ...patch, removedMainValue: personDraft[row.type === "EMAIL" ? "email" : "phone"] };
    setRows(rows => rows.flatMap(row => row.key === key ? (patch.removed && !row.id && !row.is_primary ? [] : [{ ...row, ...patch }]) : [row]));
    if (row?.is_primary) {
      const field = row.type === "EMAIL" ? "email" : "phone";
      setPersonDraft(draft => ({ ...draft,
        ...(patch.value !== undefined ? { [field]: patch.value } : {}),
        ...(patch.removed ? { [field]: "" } : {}),
        ...(patch.removed === false ? { [field]: row.removedMainValue ?? "" } : {}),
        ...(row.type === "PHONE" && patch.phone_region !== undefined ? { phone_region: patch.phone_region } : {}),
      }));
    }
  }

  function addPersonContact(type: "EMAIL" | "PHONE") {
    setRows(rows => [...rows, { key: `new-${++sequence.current}`, type, value: "", phone_region: type === "PHONE" ? region : null, is_primary: false, is_public: false }]);
  }

  const regionChanged = (row: PersonContactRow) => row.type === "PHONE" && Boolean(row.baseline) &&
    (row.phone_region ?? "") !== initialPhoneRegion(row.baseline?.value, row.baseline?.phone_region_used, region);
  const rowDirty = (row: PersonContactRow) => row.unknown || row.removed || (row.baseline
    ? row.value.trim() !== row.baseline.value || row.is_public !== row.baseline.is_public || regionChanged(row)
    : Boolean((!row.is_primary && row.value.trim()) || row.is_public));
  const personDraftHasUnsavedChanges = unknownCreate || personSaveState === "error" ||
    JSON.stringify(normalize(personDraft)) !== JSON.stringify(baseline.current) ||
    personTagInput !== baselineTags.current || personContactRows.some(rowDirty);

  async function submitPersonDraft(): Promise<boolean> {
    if (!tenantId || selectedId === null || writing.current || unknownPost.current || unknownCreate || personContactRows.some(row => row.unknown)) return false;
    const errors = validate(personDraft);
    for (const row of personContactRows.filter(row => !row.removed)) {
      if (regionChanged(row) && row.value.trim() === row.baseline?.value) errors[row.key] = "Land/region brukes når nummeret endres. Behold lagret region eller endre nummeret før du lagrer.";
      if (row.baseline && !row.value.trim()) errors[row.key] = "Tom verdi fjerner ikke en lagret kontakt. Fyll inn verdien eller velg Fjern.";
      if (row.is_public && !row.value.trim()) errors[row.key] = "Fyll inn en kontaktverdi før du velger offentlig visning.";
      if (row.value.trim() && row.type === "EMAIL" && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(row.value.trim())) errors[row.key] = "Ugyldig e-postadresse.";
    }
    setErrors(errors);
    if (Object.keys(errors).length) { setState("error"); setMessage("Rett de markerte feltene før du lagrer."); return false; }
    writing.current = true; setState("saving"); setMessage(null); setError(null);
    let rows = personContactRows.map(row => ({ ...row }));
    let progress = knownPerson.current ? `Person #${knownPerson.current.id} finnes.` : "Personen er ennå ikke bekreftet opprettet.";
    let stage = "profil";
    let activeContactKey: string | null = null;
    const publishRows = () => setRows(rows.map(row => ({ ...row })));
    try {
      const tagIds = await resolveTags(tenantId, personTagInput);
      const fullPayload = normalize({ ...personDraft, tag_ids: tagIds });
      const changedMainFields = new Set((['email', 'phone'] as const).filter(field => !knownPerson.current || fullPayload[field] !== baseline.current[field]));
      // Delete by actual ID, then clear any corresponding legacy main field.
      for (const row of rows.filter(row => row.removed && row.id && !row.deleted)) {
        stage = "fjerning av kontakt";
        try { await deletePersonContact(tenantId, row.id!); }
        catch (error) {
          if (!(error instanceof ApiError && error.status === 404)) {
            if (!(error instanceof ApiError && error.status >= 400 && error.status < 500)) row.deleteUncertain = true;
            publishRows(); throw error;
          }
        }
        row.deleted = true; row.mainClearPending = row.is_primary; row.deleteUncertain = false;
        publishRows(); progress += ` Kontakt #${row.id} er fjernet.`;
        if (knownPerson.current) {
          knownPerson.current = { ...knownPerson.current, contacts: (knownPerson.current.contacts ?? []).filter(contact => contact.id !== row.id) };
          remember(knownPerson.current);
        }
      }
      let result = knownPerson.current;
      if (!result) {
        stage = "oppretting av person";
        try { result = await createPerson(tenantId, fullPayload); }
        catch (error) {
          if (!(error instanceof ApiError && error.status >= 400 && error.status < 500)) { unknownPost.current = true; setUnknownCreate(true); }
          throw error;
        }
        // Keep ID before any contact calls or reads, including on /people/new.
        knownPerson.current = result; identity.current = `${tenantId}:${result.id}`;
        setPersistedId(result.id); remember(result); progress = `Person #${result.id} er opprettet.`;
      } else {
        const payload: Partial<PersonPayload> = { ...fullPayload };
        for (const field of ["email", "phone"] as const) {
          if (fullPayload[field] === baseline.current[field]) delete payload[field];
        }
        if (!("phone" in payload)) delete payload.phone_region;
        stage = "profil";
        result = await patchPerson(tenantId, result.id, payload);
        knownPerson.current = result; remember(result); progress = `Profil #${result.id} er lagret.`;
      }
      // Capture server-created main-contact IDs from this write response, never by value.
      for (const row of rows.filter(row => row.is_primary && !row.removed)) {
        const contact = result.contacts?.find(contact => contact.type === row.type && contact.is_primary);
        if (contact) { row.id = contact.id; row.baseline = contact; }
      }
      for (const row of rows) if (row.deleted) row.mainClearPending = false;
      baseline.current = fullPayload; baselineTags.current = personTagInput;
      setPersonDraft(draft => ({ ...draft, tag_ids: tagIds })); publishRows();
      for (const row of rows.filter(row => !row.removed && row.value.trim())) {
        activeContactKey = row.key;
        stage = `lagring av ${row.type === "EMAIL" ? "e-post" : "telefon"}`;
        let confirmed: PersonContact;
        if (row.id) {
          const patch: { value?: string; phone_region?: string | null; is_public?: boolean } = {};
          if (row.value.trim() !== row.baseline?.value) { patch.value = row.value.trim(); if (row.type === "PHONE") patch.phone_region = row.phone_region; }
          if (row.is_public !== row.baseline?.is_public) patch.is_public = row.is_public;
          if (!Object.keys(patch).length) continue;
          confirmed = await patchPersonContact(tenantId, row.id, patch);
        } else {
          // A primary supplied through Person must be returned by that same write.
          if (row.is_primary) {
            if (!row.is_public && !changedMainFields.has(row.type === "EMAIL" ? "email" : "phone")) continue;
            throw new Error("Hovedkontaktens ID mangler i profilsvaret. Ikke opprett en ny kontakt.");
          }
          try { confirmed = await createPersonContact(tenantId, { person: result.id, type: row.type, value: row.value.trim(), phone_region: row.phone_region, is_primary: false, is_public: row.is_public }); }
          catch (error) {
            if (!(error instanceof ApiError && error.status >= 400 && error.status < 500)) { row.unknown = true; unknownPost.current = true; setUnknownCreate(true); }
            publishRows(); throw error;
          }
        }
        row.id = confirmed.id; row.baseline = confirmed; row.value = confirmed.value;
        knownPerson.current = { ...knownPerson.current!, contacts: [
          ...(knownPerson.current?.contacts ?? []).filter(contact => contact.id !== confirmed.id), confirmed,
        ] };
        remember(knownPerson.current);
        publishRows(); progress += ` Kontakt #${confirmed.id} er lagret.`;
      }
      rows = rows.filter(row => !row.removed);
      const saved = { ...result, contacts: rows.flatMap(row => row.baseline ? [row.baseline] : []) };
      knownPerson.current = saved; remember(saved); publishRows();
      select(result.id); setState("saved"); setLastSaved(new Date().toISOString()); setMessage(null); return true;
    } catch (error) {
      publishRows(); setState("error");
      let backendMessage = error instanceof Error ? error.message : "";
      if (error instanceof ApiError && error.data && typeof error.data === "object") {
        const fields: Record<string, string> = {};
        for (const [key, value] of Object.entries(error.data)) {
          const message = Array.isArray(value) ? value.join(" ") : typeof value === "string" ? value : "";
          if (!message) continue;
          backendMessage = message;
          const row = rows.find(row => row.is_primary && row.type === (key === "email" ? "EMAIL" : key === "phone" ? "PHONE" : null));
          fields[key === "value" && activeContactKey ? activeContactKey : row?.key ?? key] = message;
        }
        setErrors(fields);
      }
      const uncertain = !(error instanceof ApiError && error.status >= 400 && error.status < 500);
      const message = `${progress} ${stage} er ikke bekreftet. ${uncertain ? "Resultatet kan være lagret. Ukjent opprettingsresultat må avklares før nytt opprettingsforsøk." : "Ubekreftede endringer er beholdt. Du kan rette og prøve igjen."} ${backendMessage}`;
      setMessage(message); setError(message); return false;
    } finally { writing.current = false; }
  }

  function onResetPersonDraft() {
    if (writing.current) return;
    const incomplete = personContactRows.filter(row => row.deleteUncertain || row.mainClearPending);
    if (knownPerson.current && incomplete.length) unresolvedDeletes.current.set(`${tenantId}:${knownPerson.current.id}`, {
      ids: incomplete.flatMap(row => row.id ? [row.id] : []),
      mainTypes: incomplete.filter(row => row.is_primary).map(row => row.type),
    });
    hydrate(knownPerson.current);
  }
  async function onSubmitPerson(event: FormEvent) { event.preventDefault(); await submitPersonDraft(); }
  return { persistedPersonId, personDraft, setPersonDraft, personTagInput, setPersonTagInput, personContactRows,
    startNewPerson: () => { if (!writing.current) { identity.current = `${tenantId}:new`; hydrate(null); } },
    updatePersonContact, addPersonContact, personSaveState, personSaveMessage, personFieldErrors,
    personLastSavedAt, personDraftHasUnsavedChanges, peopleHasUnsavedChanges: personDraftHasUnsavedChanges,
    contactDraftHasUnsavedChanges: false, onResetPersonDraft, onSubmitPerson, submitPersonDraft,
    personSaveBlocked: unknownCreate || personContactRows.some(row => row.unknown),
  };
}
