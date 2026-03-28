import type { FormEvent } from "react";
import { useDeferredValue, useEffect, useMemo, useState, useTransition } from "react";
import {
  ApiError,
  createOrganization,
  getCategories,
  createOrganizationPerson,
  createPerson,
  createPersonContact,
  getSubcategories,
  deleteOrganizationPerson,
  deletePerson,
  deletePersonContact,
  getOrganizations,
  getOrganizationPeople,
  getPersonContacts,
  getPersons,
  getTags,
  getTenants,
  patchOrganization,
  patchOrganizationPerson,
  patchPerson,
  patchPersonContact,
  refreshOrganizationPreview,
  type OrganizationPatch,
  type PersonPayload,
} from "../api";
import type { SaveState } from "../editor-utils";
import type {
  Category,
  Organization,
  OrganizationPerson,
  Person,
  PersonContact,
  Subcategory,
  Tag,
  Tenant,
} from "../types";

export type ContactDraft = {
  type: "EMAIL" | "PHONE";
  value: string;
  is_primary: boolean;
  is_public: boolean;
};
export type LinkedPersonDraft = {
  full_name: string;
  municipality: string;
  email: string;
  phone: string;
  publish_email: boolean;
  publish_phone: boolean;
  publish_person: boolean;
  status: "ACTIVE" | "INACTIVE";
};
type FormFieldErrors = Partial<
  Record<
    | "org_number"
    | "email"
    | "phone"
    | "website_url"
    | "facebook_url"
    | "instagram_url"
    | "tiktok_url"
    | "linkedin_url"
    | "youtube_url",
    string
  >
>;
type PersonFieldErrors = Partial<
  Record<
    | "email"
    | "phone"
    | "website_url"
    | "instagram_url"
    | "tiktok_url"
    | "linkedin_url"
    | "facebook_url"
    | "youtube_url",
    string
  >
>;
type ContactFieldErrors = Partial<Record<"value", string>>;
type LinkedPersonFieldErrors = Partial<Record<"full_name" | "email" | "phone", string>>;

const emptyDraft: OrganizationPatch = {
  name: "",
  org_number: "",
  email: "",
  phone: "",
  municipalities: "",
  note: "",
  is_published: false,
  publish_phone: false,
  website_url: "",
  facebook_url: "",
  instagram_url: "",
  tiktok_url: "",
  linkedin_url: "",
  youtube_url: "",
  tag_ids: [],
  subcategory_ids: [],
};

const emptyPersonDraft: PersonPayload = {
  full_name: "",
  email: "",
  phone: "",
  municipality: "",
  note: "",
  website_url: "",
  instagram_url: "",
  tiktok_url: "",
  linkedin_url: "",
  facebook_url: "",
  youtube_url: "",
  tag_ids: [],
  subcategory_ids: [],
};

const emptyContactDraft: ContactDraft = {
  type: "EMAIL",
  value: "",
  is_primary: false,
  is_public: false,
};

const emptyLinkedPersonDraft: LinkedPersonDraft = {
  full_name: "",
  municipality: "",
  email: "",
  phone: "",
  publish_email: true,
  publish_phone: true,
  publish_person: true,
  status: "ACTIVE",
};

export function useEditorData() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [tenantId, setTenantId] = useState<number | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [persons, setPersons] = useState<Person[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [subcategories, setSubcategories] = useState<Subcategory[]>([]);
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
  const [linkedPersonDraft, setLinkedPersonDraft] = useState<LinkedPersonDraft>(emptyLinkedPersonDraft);
  const [linkedPersonSaveState, setLinkedPersonSaveState] = useState<SaveState>("idle");
  const [organizationFieldErrors, setOrganizationFieldErrors] = useState<FormFieldErrors>({});
  const [personFieldErrors, setPersonFieldErrors] = useState<PersonFieldErrors>({});
  const [contactFieldErrors, setContactFieldErrors] = useState<ContactFieldErrors>({});
  const [linkedPersonFieldErrors, setLinkedPersonFieldErrors] = useState<LinkedPersonFieldErrors>({});
  const [organizationLastSavedAt, setOrganizationLastSavedAt] = useState<string | null>(null);
  const [personLastSavedAt, setPersonLastSavedAt] = useState<string | null>(null);
  const [previewRefreshState, setPreviewRefreshState] = useState<SaveState>("idle");
  const [tenantDataLoaded, setTenantDataLoaded] = useState(false);
  const [tenantDataLoading, setTenantDataLoading] = useState(false);
  const [personContactsLoading, setPersonContactsLoading] = useState(false);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    let cancelled = false;
    setError(null);
    Promise.all([getTenants(), getCategories(), getSubcategories()])
      .then(([tenantData, categoryData, subcategoryData]) => {
        if (cancelled) return;
        setTenants(tenantData);
        setCategories(categoryData);
        setSubcategories(subcategoryData);
        if (tenantData.length > 0) setTenantId((current) => current ?? tenantData[0].id);
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

    Promise.all([
      getOrganizations(tenantId),
      getPersons(tenantId),
      getTags(tenantId),
      getOrganizationPeople(tenantId),
    ])
      .then(([orgs, people, tenantTags, links]) => {
        if (cancelled) return;
        setOrganizations(orgs);
        setPersons(people);
        setTags(tenantTags);
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
      website_url: selectedOrganization.website_url ?? "",
      facebook_url: selectedOrganization.facebook_url ?? "",
      instagram_url: selectedOrganization.instagram_url ?? "",
      tiktok_url: selectedOrganization.tiktok_url ?? "",
      linkedin_url: selectedOrganization.linkedin_url ?? "",
      youtube_url: selectedOrganization.youtube_url ?? "",
      tag_ids: (selectedOrganization.tags ?? []).map((tag) => tag.id),
      subcategory_ids: (selectedOrganization.subcategories ?? []).map((item) => item.id),
    });
    setSaveState("idle");
    setOrganizationFieldErrors({});
  }, [selectedOrgId, selectedOrganization]);

  useEffect(() => {
    if (selectedPersonId === "new") {
      setPersonDraft(emptyPersonDraft);
      setContactDraft(emptyContactDraft);
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
      website_url: selectedPerson.website_url ?? "",
      instagram_url: selectedPerson.instagram_url ?? "",
      tiktok_url: selectedPerson.tiktok_url ?? "",
      linkedin_url: selectedPerson.linkedin_url ?? "",
      facebook_url: selectedPerson.facebook_url ?? "",
      youtube_url: selectedPerson.youtube_url ?? "",
      tag_ids: (selectedPerson.tags ?? []).map((tag) => tag.id),
      subcategory_ids: (selectedPerson.subcategories ?? []).map((item) => item.id),
    });
    setContactDraft(emptyContactDraft);
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
              website_url: selectedOrganization.website_url ?? "",
              facebook_url: selectedOrganization.facebook_url ?? "",
              instagram_url: selectedOrganization.instagram_url ?? "",
              tiktok_url: selectedOrganization.tiktok_url ?? "",
              linkedin_url: selectedOrganization.linkedin_url ?? "",
              youtube_url: selectedOrganization.youtube_url ?? "",
              tag_ids: (selectedOrganization.tags ?? []).map((tag) => tag.id),
              subcategory_ids: (selectedOrganization.subcategories ?? []).map((item) => item.id),
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
              website_url: selectedPerson.website_url ?? "",
              instagram_url: selectedPerson.instagram_url ?? "",
              tiktok_url: selectedPerson.tiktok_url ?? "",
              linkedin_url: selectedPerson.linkedin_url ?? "",
              facebook_url: selectedPerson.facebook_url ?? "",
              youtube_url: selectedPerson.youtube_url ?? "",
              tag_ids: (selectedPerson.tags ?? []).map((tag) => tag.id),
              subcategory_ids: (selectedPerson.subcategories ?? []).map((item) => item.id),
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
              website_url: selectedPerson.website_url ?? "",
              instagram_url: selectedPerson.instagram_url ?? "",
              tiktok_url: selectedPerson.tiktok_url ?? "",
              linkedin_url: selectedPerson.linkedin_url ?? "",
              facebook_url: selectedPerson.facebook_url ?? "",
              youtube_url: selectedPerson.youtube_url ?? "",
              tag_ids: (selectedPerson.tags ?? []).map((tag) => tag.id),
              subcategory_ids: (selectedPerson.subcategories ?? []).map((item) => item.id),
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
      setError("Rett feltene markert i rødt før du lagrer aktøren.");
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
          ...pickFieldErrors(err.data, [
            "website_url",
            "facebook_url",
            "instagram_url",
            "tiktok_url",
            "linkedin_url",
            "youtube_url",
          ]),
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

  async function onRefreshOrganizationPreview() {
    if (!tenantId || typeof selectedOrgId !== "number") return;
    setPreviewRefreshState("saving");
    setError(null);
    try {
      const updated = await refreshOrganizationPreview(tenantId, selectedOrgId);
      setOrganizations((current) => current.map((org) => (org.id === updated.id ? updated : org)));
      setPreviewRefreshState("saved");
    } catch (err) {
      setPreviewRefreshState("error");
      setError(apiErrorMessage(err, "Kunne ikke oppdatere preview"));
    }
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

  async function onCreateLinkedPerson(event: FormEvent) {
    event.preventDefault();
    if (!tenantId || typeof selectedOrgId !== "number") return;

    const nextErrors = validateLinkedPersonDraft(linkedPersonDraft);
    setLinkedPersonFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      setLinkedPersonSaveState("error");
      setError("Rett feltene markert i rødt før du oppretter kontaktpersonen.");
      return;
    }

    const fullName = linkedPersonDraft.full_name.trim();
    setLinkedPersonSaveState("saving");
    setError(null);

    try {
      const createdPerson = await createPerson(tenantId, {
        ...emptyPersonDraft,
        full_name: fullName,
        municipality: linkedPersonDraft.municipality.trim(),
        email: nullableString(linkedPersonDraft.email),
        phone: nullableString(linkedPersonDraft.phone),
      });

      const emailValue = linkedPersonDraft.email.trim();
      if (emailValue) {
        await createPersonContact(tenantId, {
          person: createdPerson.id,
          type: "EMAIL",
          value: emailValue,
          is_primary: true,
          is_public: linkedPersonDraft.publish_email,
        });
      }

      const phoneValue = linkedPersonDraft.phone.trim();
      if (phoneValue) {
        await createPersonContact(tenantId, {
          person: createdPerson.id,
          type: "PHONE",
          value: phoneValue,
          is_primary: true,
          is_public: linkedPersonDraft.publish_phone,
        });
      }

      await createOrganizationPerson(tenantId, {
        organization: selectedOrgId,
        person: createdPerson.id,
        status: linkedPersonDraft.status,
        publish_person: linkedPersonDraft.publish_person,
      });

      await reloadPeopleAndLinks();
      setLinkedPersonDraft(emptyLinkedPersonDraft);
      setLinkedPersonFieldErrors({});
      setLinkedPersonSaveState("saved");
      setSelectedPersonId(createdPerson.id);
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setLinkedPersonFieldErrors((current) => ({
          ...current,
          ...pickFieldErrors(err.data, ["full_name", "email", "phone"]),
        }));
      }
      setLinkedPersonSaveState("error");
      setError(apiErrorMessage(err, "Kunne ikke opprette og knytte kontaktperson"));
    }
  }

  async function submitPersonDraft(): Promise<boolean> {
    if (!tenantId) return false;
    const nextErrors = validatePersonDraft(personDraft);
    setPersonFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      setPersonSaveState("error");
      setError("Rett feltene markert i rødt før du lagrer personen.");
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
          ...pickFieldErrors(err.data, [
            "website_url",
            "instagram_url",
            "tiktok_url",
            "linkedin_url",
            "facebook_url",
            "youtube_url",
          ]),
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
    if (Object.keys(nextErrors).length > 0) {
      setError("Rett feltet markert i rødt før du lagrer kontaktkanalen.");
      return false;
    }
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
      website_url: selectedOrganization.website_url ?? "",
      facebook_url: selectedOrganization.facebook_url ?? "",
      instagram_url: selectedOrganization.instagram_url ?? "",
      tiktok_url: selectedOrganization.tiktok_url ?? "",
      linkedin_url: selectedOrganization.linkedin_url ?? "",
      youtube_url: selectedOrganization.youtube_url ?? "",
      tag_ids: (selectedOrganization.tags ?? []).map((tag) => tag.id),
      subcategory_ids: (selectedOrganization.subcategories ?? []).map((item) => item.id),
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
      website_url: selectedPerson.website_url ?? "",
      instagram_url: selectedPerson.instagram_url ?? "",
      tiktok_url: selectedPerson.tiktok_url ?? "",
      linkedin_url: selectedPerson.linkedin_url ?? "",
      facebook_url: selectedPerson.facebook_url ?? "",
      youtube_url: selectedPerson.youtube_url ?? "",
      tag_ids: (selectedPerson.tags ?? []).map((tag) => tag.id),
      subcategory_ids: (selectedPerson.subcategories ?? []).map((item) => item.id),
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
    tags,
    categories,
    subcategories,
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
    previewRefreshState,
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
    linkedPersonDraft,
    setLinkedPersonDraft,
    linkedPersonSaveState,
    linkedPersonFieldErrors,
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
    onRefreshOrganizationPreview,
    onCreateLink,
    onCreateLinkedPerson,
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
  const websiteUrl = (draft.website_url ?? "").trim();
  const facebookUrl = (draft.facebook_url ?? "").trim();
  const instagramUrl = (draft.instagram_url ?? "").trim();
  const tiktokUrl = (draft.tiktok_url ?? "").trim();
  const linkedinUrl = (draft.linkedin_url ?? "").trim();
  const youtubeUrl = (draft.youtube_url ?? "").trim();

  if (orgNumber && !/^\d{9}$/.test(orgNumber.replace(/\s+/g, ""))) {
    errors.org_number = "Org.nr må være 9 sifre.";
  }
  if (email && !isValidEmail(email)) {
    errors.email = "Ugyldig e-postadresse.";
  }
  if (phone && !isLikelyValidPhone(phone)) {
    errors.phone = "Ugyldig telefonnummer.";
  }
  if (websiteUrl && !isLikelyValidHttpUrl(websiteUrl)) {
    errors.website_url = "Ugyldig URL.";
  }
  if (facebookUrl && !isLikelyValidHttpUrl(facebookUrl)) {
    errors.facebook_url = "Ugyldig URL.";
  }
  if (instagramUrl && !isLikelyValidHttpUrl(instagramUrl)) {
    errors.instagram_url = "Ugyldig URL.";
  }
  if (tiktokUrl && !isLikelyValidHttpUrl(tiktokUrl)) {
    errors.tiktok_url = "Ugyldig URL.";
  }
  if (linkedinUrl && !isLikelyValidHttpUrl(linkedinUrl)) {
    errors.linkedin_url = "Ugyldig URL.";
  }
  if (youtubeUrl && !isLikelyValidHttpUrl(youtubeUrl)) {
    errors.youtube_url = "Ugyldig URL.";
  }
  return errors;
}

function validatePersonDraft(draft: PersonPayload): PersonFieldErrors {
  const errors: PersonFieldErrors = {};
  const email = (draft.email ?? "").trim();
  const phone = (draft.phone ?? "").trim();
  const websiteUrl = (draft.website_url ?? "").trim();
  const instagramUrl = (draft.instagram_url ?? "").trim();
  const tiktokUrl = (draft.tiktok_url ?? "").trim();
  const linkedinUrl = (draft.linkedin_url ?? "").trim();
  const facebookUrl = (draft.facebook_url ?? "").trim();
  const youtubeUrl = (draft.youtube_url ?? "").trim();
  if (email && !isValidEmail(email)) {
    errors.email = "Ugyldig e-postadresse.";
  }
  if (phone && !isLikelyValidPhone(phone)) {
    errors.phone = "Ugyldig telefonnummer.";
  }
  if (websiteUrl && !isLikelyValidHttpUrl(websiteUrl)) {
    errors.website_url = "Ugyldig URL.";
  }
  if (instagramUrl && !isLikelyValidHttpUrl(instagramUrl)) {
    errors.instagram_url = "Ugyldig URL.";
  }
  if (tiktokUrl && !isLikelyValidHttpUrl(tiktokUrl)) {
    errors.tiktok_url = "Ugyldig URL.";
  }
  if (linkedinUrl && !isLikelyValidHttpUrl(linkedinUrl)) {
    errors.linkedin_url = "Ugyldig URL.";
  }
  if (facebookUrl && !isLikelyValidHttpUrl(facebookUrl)) {
    errors.facebook_url = "Ugyldig URL.";
  }
  if (youtubeUrl && !isLikelyValidHttpUrl(youtubeUrl)) {
    errors.youtube_url = "Ugyldig URL.";
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

function validateLinkedPersonDraft(draft: LinkedPersonDraft): LinkedPersonFieldErrors {
  const errors: LinkedPersonFieldErrors = {};
  const fullName = draft.full_name.trim();
  const email = draft.email.trim();
  const phone = draft.phone.trim();

  if (!fullName) {
    errors.full_name = "Navn er påkrevd.";
  }
  if (email && !isValidEmail(email)) {
    errors.email = "Ugyldig e-postadresse.";
  }
  if (phone && !isLikelyValidPhone(phone)) {
    errors.phone = "Ugyldig telefonnummer.";
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

function isLikelyValidHttpUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
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
    website_url: nullableString(draft.website_url),
    facebook_url: nullableString(draft.facebook_url),
    instagram_url: nullableString(draft.instagram_url),
    tiktok_url: nullableString(draft.tiktok_url),
    linkedin_url: nullableString(draft.linkedin_url),
    youtube_url: nullableString(draft.youtube_url),
    tag_ids: uniqueSortedIds(draft.tag_ids),
    subcategory_ids: uniqueSortedIds(draft.subcategory_ids),
  };
}

function normalizePersonDraft(draft: PersonPayload): PersonPayload {
  return {
    full_name: draft.full_name.trim(),
    email: nullableString(draft.email),
    phone: nullableString(draft.phone),
    municipality: draft.municipality.trim(),
    note: nullableString(draft.note),
    website_url: nullableString(draft.website_url),
    instagram_url: nullableString(draft.instagram_url),
    tiktok_url: nullableString(draft.tiktok_url),
    linkedin_url: nullableString(draft.linkedin_url),
    facebook_url: nullableString(draft.facebook_url),
    youtube_url: nullableString(draft.youtube_url),
    tag_ids: uniqueSortedIds(draft.tag_ids),
    subcategory_ids: uniqueSortedIds(draft.subcategory_ids),
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
    a.publish_phone === b.publish_phone &&
    a.website_url === b.website_url &&
    a.facebook_url === b.facebook_url &&
    a.instagram_url === b.instagram_url &&
    a.tiktok_url === b.tiktok_url &&
    a.linkedin_url === b.linkedin_url &&
    a.youtube_url === b.youtube_url &&
    isEqualIdList(a.tag_ids, b.tag_ids) &&
    isEqualIdList(a.subcategory_ids, b.subcategory_ids)
  );
}

function isEqualShallowPersonDraft(a: PersonPayload, b: PersonPayload): boolean {
  return (
    a.full_name === b.full_name &&
    a.email === b.email &&
    a.phone === b.phone &&
    a.municipality === b.municipality &&
    a.note === b.note &&
    a.website_url === b.website_url &&
    a.instagram_url === b.instagram_url &&
    a.tiktok_url === b.tiktok_url &&
    a.linkedin_url === b.linkedin_url &&
    a.facebook_url === b.facebook_url &&
    a.youtube_url === b.youtube_url &&
    isEqualIdList(a.tag_ids, b.tag_ids) &&
    isEqualIdList(a.subcategory_ids, b.subcategory_ids)
  );
}

function nullableString(value: string | null): string | null {
  if (value == null) return null;
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

function uniqueSortedIds(values: number[]): number[] {
  return [...new Set(values)].sort((a, b) => a - b);
}

function isEqualIdList(a: number[], b: number[]): boolean {
  if (a.length !== b.length) return false;
  const normalizedA = uniqueSortedIds(a);
  const normalizedB = uniqueSortedIds(b);
  return normalizedA.every((value, index) => value === normalizedB[index]);
}
