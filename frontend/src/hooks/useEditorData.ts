import type { FormEvent } from "react";
import { useDeferredValue, useEffect, useMemo, useState, useTransition } from "react";
import {
  ApiError,
  createOrganization,
  createOrganizationPerson,
  createPerson,
  createPersonContact,
  deleteOrganizationPerson,
  deletePerson,
  deletePersonContact,
  getOrganizations,
  getOrganizationPeople,
  getPersonContacts,
  getPersons,
  getTenants,
  patchOrganization,
  patchOrganizationPerson,
  patchPerson,
  patchPersonContact,
  type OrganizationPatch,
  type PersonPayload,
} from "../api";
import type { SaveState } from "../editor-utils";
import type { Organization, OrganizationPerson, Person, PersonContact, Tenant } from "../types";

export type ContactDraft = {
  type: "EMAIL" | "PHONE";
  value: string;
  is_primary: boolean;
  is_public: boolean;
};
type FormFieldErrors = Partial<Record<"org_number" | "email" | "phone", string>>;
type PersonFieldErrors = Partial<Record<"email" | "phone", string>>;
type ContactFieldErrors = Partial<Record<"value", string>>;

const emptyDraft: OrganizationPatch = {
  name: "",
  org_number: "",
  email: "",
  phone: "",
  municipalities: "",
  note: "",
  is_published: false,
  publish_phone: false,
};

const emptyPersonDraft: PersonPayload = {
  full_name: "",
  email: "",
  phone: "",
  municipality: "",
  note: "",
};

const emptyContactDraft: ContactDraft = {
  type: "EMAIL",
  value: "",
  is_primary: false,
  is_public: false,
};

export function useEditorData() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [tenantId, setTenantId] = useState<number | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [persons, setPersons] = useState<Person[]>([]);
  const [organizationPeople, setOrganizationPeople] = useState<OrganizationPerson[]>([]);
  const [personContacts, setPersonContacts] = useState<PersonContact[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<number | "new" | null>(null);
  const [selectedPersonId, setSelectedPersonId] = useState<number | "new" | null>(null);
  const [draft, setDraft] = useState<OrganizationPatch>(emptyDraft);
  const [personDraft, setPersonDraft] = useState<PersonPayload>(emptyPersonDraft);
  const [query, setQuery] = useState("");
  const [personQuery, setPersonQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const deferredPersonQuery = useDeferredValue(personQuery);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [personSaveState, setPersonSaveState] = useState<SaveState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [linkPersonId, setLinkPersonId] = useState<number | null>(null);
  const [linkStatus, setLinkStatus] = useState<"ACTIVE" | "INACTIVE">("ACTIVE");
  const [linkPublishPerson, setLinkPublishPerson] = useState(true);
  const [contactDraft, setContactDraft] = useState<ContactDraft>(emptyContactDraft);
  const [organizationFieldErrors, setOrganizationFieldErrors] = useState<FormFieldErrors>({});
  const [personFieldErrors, setPersonFieldErrors] = useState<PersonFieldErrors>({});
  const [contactFieldErrors, setContactFieldErrors] = useState<ContactFieldErrors>({});
  const [organizationLastSavedAt, setOrganizationLastSavedAt] = useState<string | null>(null);
  const [personLastSavedAt, setPersonLastSavedAt] = useState<string | null>(null);
  const [tenantDataLoaded, setTenantDataLoaded] = useState(false);
  const [tenantDataLoading, setTenantDataLoading] = useState(false);
  const [personContactsLoading, setPersonContactsLoading] = useState(false);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    let cancelled = false;
    setError(null);
    getTenants()
      .then((data) => {
        if (cancelled) return;
        setTenants(data);
        if (data.length > 0) setTenantId((current) => current ?? data[0].id);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!tenantId) return;
    let cancelled = false;

    setError(null);
    setSaveState("idle");
    setTenantDataLoaded(false);
    setTenantDataLoading(true);

    Promise.all([getOrganizations(tenantId), getPersons(tenantId), getOrganizationPeople(tenantId)])
      .then(([orgs, people, links]) => {
        if (cancelled) return;
        setOrganizations(orgs);
        setPersons(people);
        setOrganizationPeople(links);
        setSelectedPersonId((current) => current ?? people[0]?.id ?? "new");
        setLinkPersonId((current) => current ?? people[0]?.id ?? null);
        startTransition(() => {
          const first = orgs[0];
          if (!first) {
            setSelectedOrgId("new");
            setDraft(emptyDraft);
            return;
          }
          setSelectedOrgId((current) => {
            if (current === "new") return "new";
            return typeof current === "number" ? current : first.id;
          });
        });
        setTenantDataLoaded(true);
        setTenantDataLoading(false);
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
          setTenantDataLoaded(true);
          setTenantDataLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [tenantId]);

  const selectedOrganization =
    typeof selectedOrgId === "number"
      ? organizations.find((org) => org.id === selectedOrgId) ?? null
      : null;

  const selectedPerson =
    typeof selectedPersonId === "number"
      ? persons.find((person) => person.id === selectedPersonId) ?? null
      : null;

  useEffect(() => {
    if (selectedOrgId === "new") {
      setDraft(emptyDraft);
      setSaveState("idle");
      setOrganizationFieldErrors({});
      return;
    }
    if (!selectedOrganization) return;

    setDraft({
      name: selectedOrganization.name ?? "",
      org_number: selectedOrganization.org_number ?? "",
      email: selectedOrganization.email ?? "",
      phone: selectedOrganization.phone ?? "",
      municipalities: selectedOrganization.municipalities ?? "",
      note: selectedOrganization.note ?? "",
      is_published: selectedOrganization.is_published,
      publish_phone: selectedOrganization.publish_phone,
    });
    setSaveState("idle");
    setOrganizationFieldErrors({});
  }, [selectedOrgId, selectedOrganization]);

  useEffect(() => {
    if (selectedPersonId === "new") {
      setPersonDraft(emptyPersonDraft);
      setPersonSaveState("idle");
      setPersonContacts([]);
      setPersonFieldErrors({});
      setContactFieldErrors({});
      setPersonContactsLoading(false);
      return;
    }
    if (!selectedPerson) return;

    setPersonDraft({
      full_name: selectedPerson.full_name ?? "",
      email: selectedPerson.email ?? "",
      phone: selectedPerson.phone ?? "",
      municipality: selectedPerson.municipality ?? "",
      note: selectedPerson.note ?? "",
    });
    setPersonContacts(selectedPerson.contacts ?? []);
    setPersonSaveState("idle");
    setPersonFieldErrors({});
    setContactFieldErrors({});
  }, [selectedPersonId, selectedPerson]);

  useEffect(() => {
    if (!tenantId || typeof selectedPersonId !== "number") return;
    let cancelled = false;
    setPersonContactsLoading(true);

    getPersonContacts(tenantId, selectedPersonId)
      .then((contacts) => {
        if (!cancelled) {
          setPersonContacts(contacts);
          setPersonContactsLoading(false);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
          setPersonContactsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [tenantId, selectedPersonId]);

  const visibleOrganizations = useMemo(() => {
    const q = deferredQuery.trim().toLowerCase();
    if (!q) return organizations;
    return organizations.filter(
      (org) =>
        org.name.toLowerCase().includes(q) ||
        (org.org_number ?? "").toLowerCase().includes(q) ||
        (org.municipalities ?? "").toLowerCase().includes(q),
    );
  }, [organizations, deferredQuery]);

  const personsById = useMemo(() => new Map(persons.map((person) => [person.id, person])), [persons]);

  const visiblePersons = useMemo(() => {
    const q = deferredPersonQuery.trim().toLowerCase();
    if (!q) return persons;
    return persons.filter(
      (person) =>
        person.full_name.toLowerCase().includes(q) ||
        (person.email ?? "").toLowerCase().includes(q) ||
        (person.phone ?? "").toLowerCase().includes(q) ||
        (person.municipality ?? "").toLowerCase().includes(q),
    );
  }, [deferredPersonQuery, persons]);

  const selectedOrganizationLinks = useMemo(() => {
    if (typeof selectedOrgId !== "number") return [];
    return organizationPeople
      .filter((link) => link.organization === selectedOrgId)
      .sort((a, b) => {
        const aName = personsById.get(a.person)?.full_name ?? "";
        const bName = personsById.get(b.person)?.full_name ?? "";
        return aName.localeCompare(bName, "nb");
      });
  }, [organizationPeople, personsById, selectedOrgId]);

  const availablePersonsForLink = useMemo(() => {
    if (typeof selectedOrgId !== "number") return [];
    const linkedIds = new Set(
      organizationPeople
        .filter((link) => link.organization === selectedOrgId)
        .map((link) => link.person),
    );
    return persons.filter((person) => !linkedIds.has(person.id));
  }, [organizationPeople, persons, selectedOrgId]);

  useEffect(() => {
    if (typeof selectedOrgId !== "number") return;
    if (availablePersonsForLink.length === 0) {
      setLinkPersonId(null);
      return;
    }
    setLinkPersonId((current) =>
      current && availablePersonsForLink.some((person) => person.id === current)
        ? current
        : availablePersonsForLink[0].id,
    );
  }, [availablePersonsForLink, selectedOrgId]);

  const organizationHasUnsavedChanges = useMemo(() => {
    const baseline =
      selectedOrgId === "new"
        ? emptyDraft
        : selectedOrganization
          ? {
              name: selectedOrganization.name ?? "",
              org_number: selectedOrganization.org_number ?? "",
              email: selectedOrganization.email ?? "",
              phone: selectedOrganization.phone ?? "",
              municipalities: selectedOrganization.municipalities ?? "",
              note: selectedOrganization.note ?? "",
              is_published: selectedOrganization.is_published,
              publish_phone: selectedOrganization.publish_phone,
            }
          : emptyDraft;
    return !isEqualShallowOrganizationDraft(normalizeDraft(draft), normalizeDraft(baseline));
  }, [draft, selectedOrgId, selectedOrganization]);

  const peopleHasUnsavedChanges = useMemo(() => {
    const baseline =
      selectedPersonId === "new"
        ? emptyPersonDraft
        : selectedPerson
          ? {
              full_name: selectedPerson.full_name ?? "",
              email: selectedPerson.email ?? "",
              phone: selectedPerson.phone ?? "",
              municipality: selectedPerson.municipality ?? "",
              note: selectedPerson.note ?? "",
            }
          : emptyPersonDraft;
    const personDirty = !isEqualShallowPersonDraft(normalizePersonDraft(personDraft), normalizePersonDraft(baseline));
    const contactDirty =
      contactDraft.value.trim() !== "" ||
      contactDraft.type !== emptyContactDraft.type ||
      contactDraft.is_primary !== emptyContactDraft.is_primary ||
      contactDraft.is_public !== emptyContactDraft.is_public;
    return personDirty || contactDirty;
  }, [contactDraft, personDraft, selectedPerson, selectedPersonId]);
  const personDraftHasUnsavedChanges = useMemo(() => {
    const baseline =
      selectedPersonId === "new"
        ? emptyPersonDraft
        : selectedPerson
          ? {
              full_name: selectedPerson.full_name ?? "",
              email: selectedPerson.email ?? "",
              phone: selectedPerson.phone ?? "",
              municipality: selectedPerson.municipality ?? "",
              note: selectedPerson.note ?? "",
            }
          : emptyPersonDraft;
    return !isEqualShallowPersonDraft(normalizePersonDraft(personDraft), normalizePersonDraft(baseline));
  }, [personDraft, selectedPerson, selectedPersonId]);
  const contactDraftHasUnsavedChanges =
    contactDraft.value.trim() !== "" ||
    contactDraft.type !== emptyContactDraft.type ||
    contactDraft.is_primary !== emptyContactDraft.is_primary ||
    contactDraft.is_public !== emptyContactDraft.is_public;

  const hasUnsavedChanges = organizationHasUnsavedChanges || peopleHasUnsavedChanges;

  useEffect(() => {
    if (!hasUnsavedChanges) return;

    function handleBeforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
      event.returnValue = "";
    }

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [hasUnsavedChanges]);

  async function reloadOrganizations(nextSelectedId?: number | "new") {
    if (!tenantId) return;
    const data = await getOrganizations(tenantId);
    setOrganizations(data);
    if (nextSelectedId !== undefined) {
      setSelectedOrgId(nextSelectedId);
      return;
    }
    if (typeof selectedOrgId === "number" && data.some((org) => org.id === selectedOrgId)) return;
    setSelectedOrgId(data[0]?.id ?? "new");
  }

  async function reloadPeopleAndLinks() {
    if (!tenantId) return;
    const [people, links] = await Promise.all([getPersons(tenantId), getOrganizationPeople(tenantId)]);
    setPersons(people);
    setOrganizationPeople(links);
    setLinkPersonId((current) => {
      if (current && people.some((person) => person.id === current)) return current;
      return people[0]?.id ?? null;
    });
    setSelectedPersonId((current) => {
      if (current === "new") return current;
      if (current && people.some((person) => person.id === current)) return current;
      return people[0]?.id ?? "new";
    });
  }

  async function submitOrganizationDraft(): Promise<boolean> {
    if (!tenantId) return false;
    const nextErrors = validateOrganizationDraft(draft);
    setOrganizationFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      setSaveState("error");
      return false;
    }
    setSaveState("saving");
    setError(null);
    try {
      if (selectedOrgId === "new") {
        const created = await createOrganization(tenantId, normalizeDraft(draft));
        await reloadOrganizations(created.id);
      } else if (typeof selectedOrgId === "number") {
        await patchOrganization(tenantId, selectedOrgId, normalizeDraft(draft));
        await reloadOrganizations(selectedOrgId);
      } else {
        throw new Error("Ingen organisasjon valgt");
      }
      setSaveState("saved");
      setOrganizationLastSavedAt(new Date().toISOString());
      return true;
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setOrganizationFieldErrors((current) => ({
          ...current,
          ...pickFieldErrors(err.data, ["org_number", "email", "phone"]),
        }));
      }
      setSaveState("error");
      setError(apiErrorMessage(err, "Kunne ikke lagre organisasjon"));
      return false;
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    await submitOrganizationDraft();
  }

  async function onCreateLink(event: FormEvent) {
    event.preventDefault();
    if (!tenantId || typeof selectedOrgId !== "number" || !linkPersonId) return;
    try {
      setError(null);
      await createOrganizationPerson(tenantId, {
        organization: selectedOrgId,
        person: linkPersonId,
        status: linkStatus,
        publish_person: linkPublishPerson,
      });
      await reloadPeopleAndLinks();
    } catch (err) {
      setError(apiErrorMessage(err, "Kunne ikke opprette kobling"));
    }
  }

  async function submitPersonDraft(): Promise<boolean> {
    if (!tenantId) return false;
    const nextErrors = validatePersonDraft(personDraft);
    setPersonFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      setPersonSaveState("error");
      return false;
    }
    setPersonSaveState("saving");
    setError(null);
    try {
      if (selectedPersonId === "new") {
        const created = await createPerson(tenantId, normalizePersonDraft(personDraft));
        await reloadPeopleAndLinks();
        setSelectedPersonId(created.id);
      } else if (typeof selectedPersonId === "number") {
        const updated = await patchPerson(tenantId, selectedPersonId, normalizePersonDraft(personDraft));
        setPersons((current) =>
          current.map((person) => (person.id === updated.id ? { ...person, ...updated } : person)),
        );
      } else {
        throw new Error("Ingen person valgt");
      }
      setPersonSaveState("saved");
      setPersonLastSavedAt(new Date().toISOString());
      return true;
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setPersonFieldErrors((current) => ({
          ...current,
          ...pickFieldErrors(err.data, ["email", "phone"]),
        }));
      }
      setPersonSaveState("error");
      setError(apiErrorMessage(err, "Kunne ikke lagre person"));
      return false;
    }
  }

  async function onSubmitPerson(event: FormEvent) {
    event.preventDefault();
    await submitPersonDraft();
  }

  async function onDeletePerson() {
    if (!tenantId || typeof selectedPersonId !== "number") return;
    try {
      setError(null);
      await deletePerson(tenantId, selectedPersonId);
      await reloadPeopleAndLinks();
      setPersonContacts([]);
    } catch (err) {
      setError(apiErrorMessage(err, "Kunne ikke slette person"));
    }
  }

  async function createContactFromDraft(): Promise<boolean> {
    if (!tenantId || typeof selectedPersonId !== "number") return false;
    const nextErrors = validateContactDraft(contactDraft);
    setContactFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return false;
    try {
      setError(null);
      const created = await createPersonContact(tenantId, {
        person: selectedPersonId,
        ...contactDraft,
        value: contactDraft.value.trim(),
      });
      setPersonContacts((current) => sortContacts([...current, created]));
      setPersons((current) =>
        current.map((person) =>
          person.id === selectedPersonId
            ? { ...person, contacts: sortContacts([...(person.contacts ?? []), created]) }
            : person,
        ),
      );
      setContactDraft((prev) => ({ ...prev, value: "", is_primary: false, is_public: false }));
      setContactFieldErrors({});
      return true;
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setContactFieldErrors((current) => ({
          ...current,
          ...pickFieldErrors(err.data, ["value"]),
        }));
      }
      setError(apiErrorMessage(err, "Kunne ikke opprette kontakt"));
      return false;
    }
  }

  async function onCreateContact(event: FormEvent) {
    event.preventDefault();
    await createContactFromDraft();
  }

  async function updateContact(
    contactId: number,
    payload: Partial<{ type: "EMAIL" | "PHONE"; value: string; is_primary: boolean; is_public: boolean }>,
  ) {
    if (!tenantId || typeof selectedPersonId !== "number") return;
    try {
      setError(null);
      const updated = await patchPersonContact(tenantId, contactId, payload);
      setPersonContacts((current) =>
        sortContacts(current.map((contact) => (contact.id === contactId ? updated : contact))),
      );
      setPersons((current) =>
        current.map((person) =>
          person.id === selectedPersonId
            ? {
                ...person,
                contacts: sortContacts(
                  (person.contacts ?? []).map((contact) => (contact.id === contactId ? updated : contact)),
                ),
              }
            : person,
        ),
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setContactFieldErrors((current) => ({
          ...current,
          ...pickFieldErrors(err.data, ["value"]),
        }));
      }
      setError(apiErrorMessage(err, "Kunne ikke oppdatere kontakt"));
    }
  }

  async function removeContact(contactId: number) {
    if (!tenantId || typeof selectedPersonId !== "number") return;
    try {
      setError(null);
      await deletePersonContact(tenantId, contactId);
      setPersonContacts((current) => current.filter((contact) => contact.id !== contactId));
      setPersons((current) =>
        current.map((person) =>
          person.id === selectedPersonId
            ? {
                ...person,
                contacts: (person.contacts ?? []).filter((contact) => contact.id !== contactId),
              }
            : person,
        ),
      );
    } catch (err) {
      setError(apiErrorMessage(err, "Kunne ikke slette kontakt"));
    }
  }

  async function updateLink(
    linkId: number,
    payload: Partial<Pick<OrganizationPerson, "status" | "publish_person">>,
  ) {
    if (!tenantId) return;
    try {
      setError(null);
      const updated = await patchOrganizationPerson(tenantId, linkId, payload);
      setOrganizationPeople((current) => current.map((link) => (link.id === linkId ? updated : link)));
    } catch (err) {
      setError(apiErrorMessage(err, "Kunne ikke oppdatere kobling"));
    }
  }

  async function removeLink(linkId: number) {
    if (!tenantId) return;
    try {
      setError(null);
      await deleteOrganizationPerson(tenantId, linkId);
      setOrganizationPeople((current) => current.filter((link) => link.id !== linkId));
    } catch (err) {
      setError(apiErrorMessage(err, "Kunne ikke slette kobling"));
    }
  }

  function onResetOrganizationDraft() {
    if (selectedOrgId === "new") {
      setDraft(emptyDraft);
      setOrganizationFieldErrors({});
      return;
    }
    if (!selectedOrganization) return;
    setDraft({
      name: selectedOrganization.name ?? "",
      org_number: selectedOrganization.org_number ?? "",
      email: selectedOrganization.email ?? "",
      phone: selectedOrganization.phone ?? "",
      municipalities: selectedOrganization.municipalities ?? "",
      note: selectedOrganization.note ?? "",
      is_published: selectedOrganization.is_published,
      publish_phone: selectedOrganization.publish_phone,
    });
    setSaveState("idle");
    setOrganizationFieldErrors({});
  }

  function onResetPersonDraft() {
    if (selectedPersonId === "new") {
      setPersonDraft(emptyPersonDraft);
      setPersonFieldErrors({});
      return;
    }
    if (!selectedPerson) return;
    setPersonDraft({
      full_name: selectedPerson.full_name ?? "",
      email: selectedPerson.email ?? "",
      phone: selectedPerson.phone ?? "",
      municipality: selectedPerson.municipality ?? "",
      note: selectedPerson.note ?? "",
    });
    setPersonSaveState("idle");
    setPersonFieldErrors({});
  }

  async function saveAllPendingChanges(): Promise<boolean> {
    let ok = true;
    if (organizationHasUnsavedChanges) {
      ok = (await submitOrganizationDraft()) && ok;
      if (!ok) return false;
    }
    if (personDraftHasUnsavedChanges) {
      ok = (await submitPersonDraft()) && ok;
      if (!ok) return false;
    }
    if (contactDraftHasUnsavedChanges) {
      ok = (await createContactFromDraft()) && ok;
      if (!ok) return false;
    }
    return ok;
  }

  function applyTenantSelection(nextTenantId: number | null) {
    setTenantId(nextTenantId);
    setSelectedOrgId(null);
    setSelectedPersonId(null);
  }

  return {
    tenants,
    tenantId,
    setTenantId,
    applyTenantSelection,
    organizations,
    persons,
    personContacts,
    selectedOrgId,
    setSelectedOrgId,
    selectedPersonId,
    setSelectedPersonId,
    draft,
    setDraft,
    personDraft,
    setPersonDraft,
    query,
    setQuery,
    personQuery,
    setPersonQuery,
    saveState,
    personSaveState,
    error,
    setError,
    linkPersonId,
    setLinkPersonId,
    linkStatus,
    setLinkStatus,
    linkPublishPerson,
    setLinkPublishPerson,
    contactDraft,
    setContactDraft,
    organizationFieldErrors,
    personFieldErrors,
    contactFieldErrors,
    organizationLastSavedAt,
    personLastSavedAt,
    organizationHasUnsavedChanges,
    personDraftHasUnsavedChanges,
    contactDraftHasUnsavedChanges,
    peopleHasUnsavedChanges,
    hasUnsavedChanges,
    saveAllPendingChanges,
    tenantDataLoaded,
    tenantDataLoading,
    personContactsLoading,
    isPending,
    visibleOrganizations,
    visiblePersons,
    personsById,
    selectedOrganization,
    selectedOrganizationLinks,
    availablePersonsForLink,
    onSubmit,
    onCreateLink,
    onSubmitPerson,
    onDeletePerson,
    onCreateContact,
    updateContact,
    removeContact,
    updateLink,
    removeLink,
    onResetOrganizationDraft,
    onResetPersonDraft,
    setPersonContacts,
  };
}

export type EditorData = ReturnType<typeof useEditorData>;

function validateOrganizationDraft(draft: OrganizationPatch): FormFieldErrors {
  const errors: FormFieldErrors = {};
  const orgNumber = (draft.org_number ?? "").trim();
  const email = (draft.email ?? "").trim();
  const phone = (draft.phone ?? "").trim();

  if (orgNumber && !/^\d{9}$/.test(orgNumber.replace(/\s+/g, ""))) {
    errors.org_number = "Org.nr må være 9 sifre.";
  }
  if (email && !isValidEmail(email)) {
    errors.email = "Ugyldig e-postadresse.";
  }
  if (phone && !isLikelyValidPhone(phone)) {
    errors.phone = "Ugyldig telefonnummer.";
  }
  return errors;
}

function validatePersonDraft(draft: PersonPayload): PersonFieldErrors {
  const errors: PersonFieldErrors = {};
  const email = (draft.email ?? "").trim();
  const phone = (draft.phone ?? "").trim();
  if (email && !isValidEmail(email)) {
    errors.email = "Ugyldig e-postadresse.";
  }
  if (phone && !isLikelyValidPhone(phone)) {
    errors.phone = "Ugyldig telefonnummer.";
  }
  return errors;
}

function validateContactDraft(draft: ContactDraft): ContactFieldErrors {
  const errors: ContactFieldErrors = {};
  const value = draft.value.trim();
  if (!value) {
    errors.value = "Kontaktverdi er påkrevd.";
    return errors;
  }
  if (draft.type === "EMAIL" && !isValidEmail(value)) {
    errors.value = "Ugyldig e-postadresse.";
  }
  if (draft.type === "PHONE" && !isLikelyValidPhone(value)) {
    errors.value = "Ugyldig telefonnummer.";
  }
  return errors;
}

function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function isLikelyValidPhone(value: string): boolean {
  const normalized = value.replace(/[^\d+]/g, "");
  const digits = normalized.replace(/\D/g, "");
  return digits.length >= 8 && digits.length <= 15;
}

function pickFieldErrors<T extends string>(
  data: unknown,
  fields: T[],
): Partial<Record<T, string>> {
  if (!data || typeof data !== "object" || Array.isArray(data)) return {};
  const source = data as Record<string, unknown>;
  const out: Partial<Record<T, string>> = {};

  for (const field of fields) {
    const message = normalizeBackendFieldMessage(source[field]);
    if (message) out[field] = message;
  }
  return out;
}

function normalizeBackendFieldMessage(value: unknown): string | null {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    const parts = value
      .map((item) => (typeof item === "string" ? item : null))
      .filter((item): item is string => Boolean(item));
    return parts.length > 0 ? parts.join(" ") : null;
  }
  return null;
}

function apiErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return extractApiBannerMessage(error.data) ?? fallback;
  }
  return error instanceof Error ? error.message : fallback;
}

function extractApiBannerMessage(data: unknown): string | null {
  if (!data) return null;
  if (typeof data === "string" && data.trim()) return data.trim();
  if (typeof data !== "object" || Array.isArray(data)) return null;

  const source = data as Record<string, unknown>;
  const detail = normalizeBackendFieldMessage(source.detail);
  if (detail) return detail;

  const nonField = normalizeBackendFieldMessage(source.non_field_errors);
  if (nonField) return nonField;

  return null;
}

function normalizeDraft(draft: OrganizationPatch): OrganizationPatch {
  return {
    ...draft,
    name: draft.name.trim(),
    org_number: nullableString(draft.org_number),
    email: nullableString(draft.email),
    phone: nullableString(draft.phone),
    municipalities: draft.municipalities.trim(),
    note: nullableString(draft.note),
  };
}

function normalizePersonDraft(draft: PersonPayload): PersonPayload {
  return {
    full_name: draft.full_name.trim(),
    email: nullableString(draft.email),
    phone: nullableString(draft.phone),
    municipality: draft.municipality.trim(),
    note: nullableString(draft.note),
  };
}

function sortContacts<T extends { is_primary?: boolean; type?: string; value?: string }>(contacts: T[]): T[] {
  return [...contacts].sort((a, b) => {
    const primaryDelta = Number(Boolean(b.is_primary)) - Number(Boolean(a.is_primary));
    if (primaryDelta !== 0) return primaryDelta;
    const typeCmp = (a.type ?? "").localeCompare(b.type ?? "");
    if (typeCmp !== 0) return typeCmp;
    return (a.value ?? "").localeCompare(b.value ?? "");
  });
}

function isEqualShallowOrganizationDraft(a: OrganizationPatch, b: OrganizationPatch): boolean {
  return (
    a.name === b.name &&
    a.org_number === b.org_number &&
    a.email === b.email &&
    a.phone === b.phone &&
    a.municipalities === b.municipalities &&
    a.note === b.note &&
    a.is_published === b.is_published &&
    a.publish_phone === b.publish_phone
  );
}

function isEqualShallowPersonDraft(a: PersonPayload, b: PersonPayload): boolean {
  return (
    a.full_name === b.full_name &&
    a.email === b.email &&
    a.phone === b.phone &&
    a.municipality === b.municipality &&
    a.note === b.note
  );
}

function nullableString(value: string | null): string | null {
  if (value == null) return null;
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}
