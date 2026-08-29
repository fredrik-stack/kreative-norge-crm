import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useLocation } from "react-router-dom";
import { Field } from "../components/Field";
import { PhoneLink } from "../components/PhoneLink";
import { PhoneRegionSelect } from "../components/PhoneRegionSelect";
import { useEditor } from "../context/EditorContext";
import { describeEffectivePublication } from "../editorPublication";
import { filterSubcategoriesForCategory, sortedCategories as sortCategoriesByTaxonomy } from "../editorTaxonomy";
import { saveLabel } from "../editor-utils";
import { useRouteSyncedSelection } from "../hooks/useRouteSyncedSelection";
import {
  ApiError,
  approveOrganizationImage,
  createDirectUrlCandidate,
  discoverOfficialImages,
  getCandidatePreview,
  getImageSearchContext,
  getLegacyImageCandidates,
  getOrganizationImageState,
  getRenditionPreview,
  processOrganizationImage,
  processUploadedOrganizationImage,
  searchBraveImages,
} from "../api";
import type {
  OrganizationImageCandidate,
  OrganizationImageSearchContext,
  OrganizationImageState,
  PersonContact,
  ProcessedOrganizationImage,
} from "../types";

export function OrganizationsPage() {
  const editor = useEditor();
  const location = useLocation();
  const { navigate, paramValue: orgId } = useRouteSyncedSelection({
    routeParam: "orgId",
    basePath: "/organizations",
    selectedId: editor.selectedOrgId,
    setSelectedId: editor.setSelectedOrgId,
    syncWhenParamMissing: false,
  });

  const inOverviewMode = !orgId;
  const orgRouteIsNew = orgId === "new";
  const orgRouteParsed = orgId && !orgRouteIsNew ? Number(orgId) : null;
  const orgRouteIsNumeric = typeof orgRouteParsed === "number" && !Number.isNaN(orgRouteParsed);
  const invalidOrgRoute =
    editor.tenantId !== null &&
    editor.tenantDataLoaded &&
    !!orgId &&
    !orgRouteIsNew &&
    (!orgRouteIsNumeric || !editor.organizations.some((org) => org.id === orgRouteParsed));

  const filterSummary = editor.overviewFilterSummary;
  const [overviewModalOrgId, setOverviewModalOrgId] = useState<number | null>(null);

  useEffect(() => {
    if (orgId) return;
    const params = new URLSearchParams(location.search);
    const openOrg = params.get("openOrg");
    if (!openOrg) {
      setOverviewModalOrgId(null);
      return;
    }
    const parsed = Number(openOrg);
    if (!Number.isNaN(parsed)) setOverviewModalOrgId(parsed);
  }, [location.search, orgId]);

  useEffect(() => {
    if (!inOverviewMode && !editor.canWrite) {
      navigate("/organizations");
    }
  }, [editor.canWrite, inOverviewMode, navigate]);

  if (inOverviewMode) {
    return (
      <main className="editor-overview-layout">
        <OrganizationOverviewPanel
          organizations={editor.filteredOverviewOrganizations}
          navigate={navigate}
          filterSummary={filterSummary}
          modalOrgId={overviewModalOrgId}
          onModalOrgIdChange={(nextId) => {
            setOverviewModalOrgId(nextId);
            const params = new URLSearchParams(location.search);
            if (nextId === null) {
              params.delete("openOrg");
            } else {
              params.set("openOrg", String(nextId));
            }
            const nextSearch = params.toString();
            navigate(nextSearch ? `/organizations?${nextSearch}` : "/organizations");
          }}
        />
      </main>
    );
  }

  if (!editor.canWrite) {
    return null;
  }

  return (
    <main className="workspace no-sidebar">
      <>
        <OrganizationEditorPanel navigate={navigate} orgId={orgId} invalidOrgRoute={invalidOrgRoute} />
        <OrganizationPreviewPanel invalidOrgRoute={invalidOrgRoute} />
      </>
    </main>
  );
}

function OrganizationOverviewPanel(props: {
  organizations: ReturnType<typeof useEditor>["organizations"];
  navigate: (to: string) => void;
  filterSummary: string | null;
  modalOrgId: number | null;
  onModalOrgIdChange: (nextId: number | null) => void;
}) {
  const { organizations, navigate, filterSummary, modalOrgId, onModalOrgIdChange } = props;
  const editor = useEditor();
  const activeOrganization = modalOrgId ? organizations.find((organization) => organization.id === modalOrgId) ?? null : null;

  return (
    <section className="panel overview-panel">
      <div className="sidebar-header">
        <div>
          <p className="eyebrow small">Oversikt</p>
          <h2>Aktørkort</h2>
        </div>
        <span className="meta">{organizations.length} synlige</span>
      </div>
      <p className="muted">
        Her ser du alle aktører i en mer lesbar kortvisning. Klikk på et kort for å åpne all informasjon, og bruk{" "}
        <strong>Rediger</strong> når du vil åpne skjemaet.
      </p>
      {filterSummary ? <div className="filter-summary">{filterSummary}</div> : null}
      <div className="editor-card-grid">
        {organizations.map((organization) => {
          const overviewPills = getOverviewPills(organization);
          return (
          <article
            key={organization.id}
            className="editor-card public-like"
            onClick={() => onModalOrgIdChange(organization.id)}
          >
            {organization.preview_image_url ? (
              <img
                src={organization.preview_image_url}
                alt={organization.name}
                className="editor-card-thumb"
              />
            ) : (
              <div className="editor-card-thumb editor-card-thumb-fallback">
                <span>{organization.name.slice(0, 2).toUpperCase()}</span>
              </div>
            )}
            <div className="editor-card-body">
              <div className="editor-card-head">
                <h3>{organization.name}</h3>
                <span className="meta">{organization.municipalities || "Ingen kommune"}</span>
              </div>
              <div className="meta-row">
                {overviewPills.map((pill) => (
                  <span key={pill.key} className={`mini-pill ${pill.kind}`}>{pill.label}</span>
                ))}
              </div>
              <div className="editor-card-actions">
                <span className={`save-pill ${organization.is_published ? "saved" : "idle"}`}>
                  {organization.is_published ? "Publisert" : "Kun intern"}
                </span>
                {editor.canWrite ? (
                  <button
                    type="button"
                    className="ghost-button compact-button"
                    onClick={(event) => {
                      event.stopPropagation();
                      editor.setSelectedOrgId(organization.id);
                      navigate(`/organizations/${organization.id}`);
                    }}
                  >
                    Rediger
                  </button>
                ) : null}
              </div>
            </div>
          </article>
        )})}
      </div>
      {organizations.length === 0 ? <div className="empty-state">Ingen aktører matcher filtreringen.</div> : null}
      {activeOrganization ? (
        <OrganizationOverviewModal
          organization={activeOrganization}
          onClose={() => onModalOrgIdChange(null)}
          onEdit={
            editor.canWrite
              ? () => {
                  editor.setSelectedOrgId(activeOrganization.id);
                  navigate(`/organizations/${activeOrganization.id}`);
                }
              : null
          }
        />
      ) : null}
    </section>
  );
}

function OrganizationOverviewModal(props: {
  organization: ReturnType<typeof useEditor>["organizations"][number];
  onClose: () => void;
  onEdit: (() => void) | null;
}) {
  const { organization, onClose, onEdit } = props;
  const editor = useEditor();
  const externalLinks = getOrganizationLinkRows(organization);
  const contactsByPersonId = useMemo(() => {
    const grouped = new Map<number, PersonContact[]>();
    for (const person of editor.persons) {
      for (const contact of person.contacts ?? []) {
        const current = grouped.get(person.id) ?? [];
        current.push(contact);
        grouped.set(person.id, current);
      }
    }
    for (const contact of editor.personContacts) {
      if (!contact.person) continue;
      const current = (grouped.get(contact.person) ?? []).filter((item) => item.id !== contact.id);
      current.push(contact);
      grouped.set(contact.person, current);
    }
    return grouped;
  }, [editor.personContacts, editor.persons]);
  const modal = (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div className="detail-modal" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
        <div className="sidebar-header modal-header">
          <div>
            <p className="eyebrow small">Aktørkort</p>
            <h2>{organization.name}</h2>
          </div>
          <button type="button" className="ghost-button" onClick={onClose}>
            Lukk
          </button>
        </div>
        <div className="editor-card modal-card modal-shell">
          {organization.preview_image_url ? (
            <img src={organization.preview_image_url} alt={organization.name} className="editor-card-thumb modal-thumb" />
          ) : (
            <div className="editor-card-thumb editor-card-thumb-fallback modal-thumb">
              <span>{organization.name.slice(0, 2).toUpperCase()}</span>
            </div>
          )}
          <div className="editor-card-body">
            <div className="editor-card-head">
              <div>
                <h3>{organization.name}</h3>
                <span className="meta">{organization.municipalities || "Ingen kommune"}</span>
              </div>
              <span className={`save-pill ${organization.is_published ? "saved" : "idle"}`}>
                {organization.is_published ? "Publisert" : "Kun intern"}
              </span>
            </div>
            <div className="meta-row">
              {organization.categories.map((category) => (
                <span key={category.id} className="mini-pill category">{category.name.toUpperCase()}</span>
              ))}
              {organization.subcategories.map((subcategory) => (
                <span key={subcategory.id} className="mini-pill subcategory">{subcategory.name}</span>
              ))}
              {organization.tags.map((tag) => (
                <span key={tag.id} className="mini-pill tag">{tag.name}</span>
              ))}
            </div>
            <p className="muted editor-card-copy">
              {organization.description || organization.note || "Ingen beskrivelse lagt inn ennå."}
            </p>
            <div className="editor-detail-grid">
              <div>
                <span className="meta">E-post</span>
                {organization.email ? <a href={`mailto:${organization.email}`}>{organization.email}</a> : <strong>—</strong>}
              </div>
              <div>
                <span className="meta">Telefon · {organization.publish_phone ? "Offentlig" : "Kun intern"}</span>
                <PhoneLink
                  value={organization.phone}
                  dialUri={organization.phone_dial_uri}
                  countryCallingCodeHint={organization.phone_country_calling_code_hint}
                  empty={<strong>—</strong>}
                />
              </div>
              <div>
                <span className="meta">Org.nr</span>
                <strong>{organization.org_number || "—"}</strong>
              </div>
              <div>
                <span className="meta">Primærlenke</span>
                {organization.primary_link ? (
                  <a href={organization.primary_link} target="_blank" rel="noreferrer">
                    {organization.primary_link}
                  </a>
                ) : (
                  <strong>—</strong>
                )}
              </div>
            </div>
            {externalLinks.length > 0 ? (
              <div className="editor-detail-section">
                <h4>Lenker</h4>
                <div className="editor-link-list">
                  {externalLinks.map((link) => (
                    <a key={`${organization.id}-${link.label}`} href={link.href} target="_blank" rel="noreferrer">
                      {link.label}
                    </a>
                  ))}
                </div>
              </div>
            ) : null}
            <div className="editor-detail-section">
              <h4>Kontaktpersoner</h4>
              {organization.active_people && organization.active_people.length > 0 ? (
                <div className="editor-contact-list">
                  {organization.active_people.map((link) => {
                    const visibleContacts = getEditorVisibleContacts(link, editor.personsById, contactsByPersonId);
                    return (
                      <div key={link.id} className="editor-contact-card">
                        <strong>{link.person?.full_name || "Ukjent person"}</strong>
                        <span className="meta">
                          {[link.person?.title || null, link.person?.municipality || null].filter(Boolean).join(" · ") || "Ingen kommune"}
                        </span>
                        {visibleContacts.length > 0 ? (
                          <div className="editor-inline-links">
                            {visibleContacts.map((contact, index) => (
                              <span key={`${link.id}-${contact.type}-${index}-${contact.value}`} className="editor-contact-chip">
                                {contact.type === "EMAIL" ? (
                                  <a href={`mailto:${contact.value}`}>{contact.value}</a>
                                ) : (
                                  <PhoneLink
                                    value={contact.value}
                                    dialUri={contact.phone_dial_uri}
                                    countryCallingCodeHint={contact.phone_country_calling_code_hint}
                                  />
                                )}
                                <span className="meta">{contact.is_public ? "Offentlig" : "Intern"}</span>
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="meta">Ingen kontaktinfo lagret</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="empty-state compact">Ingen kontaktpersoner knyttet til aktøren.</div>
              )}
            </div>
            <div className="actions modal-footer">
              <button type="button" className="ghost-button compact-button" onClick={onClose}>
                Lukk
              </button>
              {onEdit ? (
                <button type="button" className="primary-button compact-button" onClick={onEdit}>
                  Rediger
                </button>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
  return createPortal(modal, document.body);
}

function OrganizationEditorPanel(props: {
  navigate: (to: string) => void;
  orgId: string | undefined;
  invalidOrgRoute: boolean;
}) {
  const { navigate, orgId, invalidOrgRoute } = props;
  const editor = useEditor();

  return (
    <section className="panel editor">
      {editor.tenantDataLoading ? (
        <div className="route-missing">
          <p className="eyebrow small">Laster</p>
          <h2>Henter aktørdata...</h2>
          <p className="muted">Vent litt mens tenant-data lastes inn.</p>
        </div>
      ) : invalidOrgRoute ? (
        <div className="route-missing">
          <p className="eyebrow small">Ugyldig URL</p>
          <h2>Aktør ikke funnet</h2>
          <p className="muted">
            Ingen organisasjon matcher ruten <code>/organizations/{orgId}</code>.
          </p>
          <div className="actions">
            <button type="button" className="primary-button" onClick={() => navigate("/organizations/new")}>
              Opprett ny aktør
            </button>
            {editor.organizations[0] ? (
              <button
                type="button"
                className="ghost-button"
                onClick={() => {
                  editor.setSelectedOrgId(editor.organizations[0].id);
                  navigate(`/organizations/${editor.organizations[0].id}`);
                }}
              >
                Gå til første aktør
              </button>
            ) : null}
          </div>
        </div>
      ) : (
        <>
          {editor.organizationHasUnsavedChanges ? (
            <div className="inline-banner warn">Du har ulagrede endringer i aktørskjemaet.</div>
          ) : null}
          {editor.organizationLastSavedAt && !editor.organizationHasUnsavedChanges ? (
            <div className="inline-banner success">
              Sist lagret {formatTime(editor.organizationLastSavedAt)}
            </div>
          ) : null}
          <div className="editor-header">
            <div>
              <p className="eyebrow small">
                {editor.selectedOrgId === "new" ? "Ny aktør" : `Aktør #${editor.selectedOrgId ?? "-"}`}
              </p>
              <h2>{editor.draft.name || "Organisasjon"}</h2>
            </div>
            <div className={`save-pill ${editor.saveState}`}>{saveLabel(editor.saveState)}</div>
          </div>

          <form onSubmit={editor.onSubmit} className="editor-form">
            <div className="grid two">
              <Field label="Navn" required>
                <input
                  value={editor.draft.name}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, name: e.target.value }))}
                  required
                />
              </Field>
              <Field label="Org.nr" error={editor.organizationFieldErrors.org_number}>
                <input
                  value={editor.draft.org_number ?? ""}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, org_number: e.target.value }))}
                  inputMode="numeric"
                />
              </Field>
            </div>

            <div className="grid two">
              <Field label="E-post" error={editor.organizationFieldErrors.email}>
                <input
                  type="email"
                  value={editor.draft.email ?? ""}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, email: e.target.value }))}
                />
              </Field>
              <Field label="Telefon" error={editor.organizationFieldErrors.phone}>
                <div className="contact-inline-input">
                  <input
                    aria-label="Telefon"
                    value={editor.draft.phone ?? ""}
                    onChange={(e) =>
                      editor.setDraft((state) => ({
                        ...state,
                        phone: e.target.value,
                        ...(e.target.value.trim().startsWith("+") ? { phone_region: null } : {}),
                      }))
                    }
                  />
                  <PhoneRegionSelect
                    value={editor.draft.phone_region ?? ""}
                    onChange={(phoneRegion) =>
                      editor.setDraft((state) => ({ ...state, phone_region: phoneRegion || null }))
                    }
                  />
                </div>
                <small className="meta">Land/region kreves bare for nasjonalt skrevne numre.</small>
              </Field>
            </div>

            <Field label="Kommune(r)">
              <input
                value={editor.draft.municipalities}
                onChange={(e) => editor.setDraft((s) => ({ ...s, municipalities: e.target.value }))}
                placeholder="Bodø, Tromsø"
              />
            </Field>

            <Field label="Notat">
              <textarea
                rows={3}
                value={editor.draft.note ?? ""}
                onChange={(e) => editor.setDraft((s) => ({ ...s, note: e.target.value }))}
                placeholder="Interne kommentarer, status eller ting som ikke skal vises offentlig."
              />
            </Field>

            <Field label="Beskrivelse">
              <textarea
                rows={5}
                value={editor.draft.description ?? ""}
                onChange={(e) => editor.setDraft((s) => ({ ...s, description: e.target.value }))}
                placeholder="Denne teksten vises offentlig under Profil på aktørsiden."
              />
              <p className="muted" style={{ margin: "6px 0 0" }}>
                Dette feltet brukes i public-visningen under Profil-seksjonen.
              </p>
            </Field>

            <CategorySelectFields
              title="Kategori og underkategori"
              description="Velg først en hovedkategori, og deretter en underkategori som hører til den."
              categories={editor.categories}
              subcategories={editor.subcategories}
              selectedCategoryIds={editor.draft.category_ids}
              selectedIds={editor.draft.subcategory_ids}
              onSelect={(categoryId, subcategoryId) =>
                editor.setDraft((state) => ({
                  ...state,
                  category_ids: categoryId ? [categoryId] : [],
                  subcategory_ids: subcategoryId ? [subcategoryId] : [],
                }))
              }
            />

            <Field label="Tags">
              <input
                value={editor.organizationTagInput}
                onChange={(e) => editor.setOrganizationTagInput(e.target.value)}
                placeholder="f.eks. live, management, booking"
              />
              <TagSuggestions
                value={editor.organizationTagInput}
                tags={editor.tags}
                onSelect={(nextValue) => editor.setOrganizationTagInput(nextValue)}
              />
              <p className="muted" style={{ margin: "6px 0 0" }}>
                Skriv egne tags separert med komma. Maks 5 tags.
              </p>
            </Field>

            <div className="grid two">
              <Field label="Website URL" error={editor.organizationFieldErrors.website_url}>
                <input
                  type="url"
                  value={editor.draft.website_url ?? ""}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, website_url: e.target.value }))}
                  placeholder="https://..."
                />
              </Field>
              <Field label="Facebook URL" error={editor.organizationFieldErrors.facebook_url}>
                <input
                  type="url"
                  value={editor.draft.facebook_url ?? ""}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, facebook_url: e.target.value }))}
                  placeholder="https://facebook.com/..."
                />
              </Field>
            </div>

            <div className="grid two">
              <Field label="Instagram URL" error={editor.organizationFieldErrors.instagram_url}>
                <input
                  type="url"
                  value={editor.draft.instagram_url ?? ""}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, instagram_url: e.target.value }))}
                  placeholder="https://instagram.com/..."
                />
              </Field>
              <Field label="TikTok URL" error={editor.organizationFieldErrors.tiktok_url}>
                <input
                  type="url"
                  value={editor.draft.tiktok_url ?? ""}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, tiktok_url: e.target.value }))}
                  placeholder="https://tiktok.com/@..."
                />
              </Field>
            </div>

            <div className="grid two">
              <Field label="LinkedIn URL" error={editor.organizationFieldErrors.linkedin_url}>
                <input
                  type="url"
                  value={editor.draft.linkedin_url ?? ""}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, linkedin_url: e.target.value }))}
                  placeholder="https://linkedin.com/..."
                />
              </Field>
            </div>

            <Field label="YouTube URL" error={editor.organizationFieldErrors.youtube_url}>
              <input
                type="url"
                value={editor.draft.youtube_url ?? ""}
                onChange={(e) => editor.setDraft((s) => ({ ...s, youtube_url: e.target.value }))}
                placeholder="https://youtube.com/..."
              />
            </Field>

            <div className="toggle-grid">
              <label className="toggle-card">
                <input
                  type="checkbox"
                  checked={editor.draft.is_published}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, is_published: e.target.checked }))}
                />
                <div>
                  <strong>Publiser aktør</strong>
                  <p>Synlig i public API når slått på.</p>
                </div>
              </label>

              <label className="toggle-card">
                <input
                  type="checkbox"
                  checked={editor.draft.publish_phone}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, publish_phone: e.target.checked }))}
                />
                <div>
                  <strong>Publiser telefon</strong>
                  <p>Telefon returneres i public API når slått på.</p>
                </div>
              </label>
            </div>

            <div className="actions">
              <button
                type="submit"
                className="primary-button"
                disabled={!editor.tenantId || editor.saveState === "saving"}
              >
                {editor.selectedOrgId === "new" ? "Opprett aktør" : "Lagre endringer"}
              </button>
              <button type="button" className="ghost-button" onClick={editor.onResetOrganizationDraft}>
                Nullstill
              </button>
              {editor.isPending ? <span className="meta">Oppdaterer visning...</span> : null}
            </div>
          </form>

          {typeof editor.selectedOrgId === "number" && editor.selectedOrganization?.image_asset_feature_enabled ? (
            <OrganizationImagePanel
              key={`${editor.tenantId}:${editor.selectedOrgId}`}
              tenantId={editor.tenantId!}
              organizationId={editor.selectedOrgId}
              organizationName={editor.selectedOrganization.name}
            />
          ) : null}

          <OrganizationLinksPanel navigate={navigate} />
        </>
      )}
    </section>
  );
}

type ImageVariant = "square" | "landscape" | "share";
const IMAGE_VARIANTS: ImageVariant[] = ["square", "landscape", "share"];
const IMAGE_VARIANT_LABELS: Record<ImageVariant, string> = {
  square: "Kvadrat",
  landscape: "Landskap",
  share: "Deling",
};
const IMAGE_VARIANT_SIZES: Record<ImageVariant, readonly [number, number]> = {
  square: [512, 512],
  landscape: [800, 450],
  share: [1200, 630],
};
const MIN_COVER_ZOOM = 1;
const MAX_COVER_ZOOM = 3;
const MAX_CANDIDATE_PREVIEW_CONCURRENCY = 4;

type ImageSourcePanel = "brave" | "url" | "upload" | null;
type ImageFlowOperation = "generic" | "brave" | "direct_url" | "upload";
type CandidatePreviewTask = {
  candidateRef: string;
  generation: number;
  candidateSetVersion: number;
};

const QUERY_SOURCE_LABELS: Record<string, string> = {
  organization_name: "aktørnavn",
  municipality: "kommune",
  category: "kategori",
  person: "tilknyttet person",
  manual_edit: "redigert av redaktør",
};

function imageFlowError(error: unknown, operation: ImageFlowOperation = "generic"): string {
  if (error instanceof ApiError && error.status === 413) {
    return "Bildet er for stort. Velg en fil på maks 15 MB.";
  }

  const code = error instanceof ApiError && error.data && typeof error.data === "object" && "code" in error.data
    ? String((error.data as { code: unknown }).code)
    : "";

  if (
    operation === "direct_url"
    && ["content_type", "html_instead_of_image", "image_mismatch", "html_mismatch"].includes(code)
  ) {
    return "Lenken peker ikke direkte til et støttet bilde.";
  }
  if (["provider_not_configured", "brave_not_configured", "missing_provider_key"].includes(code)) {
    return "Bildesøk er ikke konfigurert i dette miljøet.";
  }
  if (["provider_unavailable", "provider_timeout", "provider_rate_limited", "rate_limited"].includes(code)) {
    return "Bildesøket er midlertidig utilgjengelig. Prøv igjen senere.";
  }

  switch (code) {
    case "upscale_required":
      return "Bildet er for lite til å lage alle nødvendige formater uten kvalitetstap. Velg et større bilde.";
    case "invalid_zoom":
    case "invalid_crop_recipe":
      return "Utsnittet er ugyldig. Tilbakestill utsnittet og prøv igjen.";
    case "invalid_url":
    case "credentials_forbidden":
    case "private_host":
    case "metadata_host":
    case "private_address":
    case "https_downgrade":
    case "invalid_redirect":
    case "too_many_redirects":
      return "Bilde-URL-en er ugyldig eller kan ikke brukes.";
    case "content_type":
    case "image_mismatch":
    case "html_mismatch":
      return "Bildekilden returnerte ikke et støttet bilde.";
    case "unsupported_format":
    case "mime_mismatch":
    case "decoder_format_mismatch":
      return "Bildeformatet støttes ikke. Bruk JPEG, PNG eller WebP.";
    case "animated_not_supported":
    case "preview_animated":
      return "Animerte bilder støttes ikke. Velg et statisk JPEG-, PNG- eller WebP-bilde.";
    case "file_too_large":
    case "response_too_large":
    case "preview_size_limit":
      return "Bildet er for stort. Velg en fil på maks 15 MB.";
    case "pixel_limit":
    case "preview_pixel_limit":
      return "Bildet har for mange bildepunkter. Velg et mindre bilde.";
    case "dns_failed":
    case "peer_mismatch":
    case "http_error":
    case "invalid_length":
    case "connection_failed":
      return "Bildekilden kunne ikke hentes. Kontroller lenken og prøv igjen.";
    case "timeout":
      return operation === "brave"
        ? "Bildesøket svarte ikke i tide. Prøv igjen."
        : "Bildekilden svarte ikke i tide. Prøv igjen.";
    case "decode_failed":
    case "preview_decode":
    case "empty_upload":
    case "empty_response":
    case "corrupt_icc_profile":
    case "icc_conversion_failed":
      return "Bildet er skadet eller kan ikke leses.";
    case "expired_ref":
    case "invalid_ref":
    case "wrong_scope":
      return "Bildeforslaget er utløpt eller ugyldig. Hent forslagene på nytt.";
    case "revision_conflict":
      return "Bildevalget er endret av en annen redaktør. Last inn siden på nytt og prøv igjen.";
    case "permission_denied":
      return "Du har ikke tilgang til denne bildehandlingen.";
    default:
      return "Bildehandlingen kunne ikke fullføres. Prøv igjen eller hent kandidatene på nytt.";
  }
}

function defaultSearchMunicipality(context: OrganizationImageSearchContext): string | null {
  return context.municipalities.length === 1 && context.query_sources.includes("municipality")
    ? context.municipalities[0]
    : null;
}

function searchBaseQuery(context: OrganizationImageSearchContext): string {
  const municipality = defaultSearchMunicipality(context);
  const suffix = municipality ? ` ${municipality}` : "";
  return suffix && context.suggested_query.endsWith(suffix)
    ? context.suggested_query.slice(0, -suffix.length)
    : context.suggested_query;
}

function buildRefinedSearchQuery(
  context: OrganizationImageSearchContext,
  municipality: string | null,
  categoryId: number | null,
  personId: number | null,
): string {
  const category = context.categories.find((item) => item.id === categoryId)?.name ?? null;
  const person = context.people.find((item) => item.id === personId)?.name ?? null;
  return [searchBaseQuery(context), municipality, category, person].filter(Boolean).join(" ");
}

function candidateSourceDetails(candidate: OrganizationImageCandidate): string {
  const values = [candidate.source_publisher, candidate.source_domain]
    .map((value) => value?.trim() ?? "")
    .filter(Boolean);
  const uniqueValues = values.filter(
    (value, index) => values.findIndex((item) => item.toLocaleLowerCase() === value.toLocaleLowerCase()) === index,
  );
  return uniqueValues.join(" · ") || "Ukjent kilde";
}

export function OrganizationImagePanel(props: {
  tenantId: number;
  organizationId: number;
  organizationName: string;
}) {
  const { tenantId, organizationId, organizationName } = props;
  const objectUrls = useRef<string[]>([]);
  const scopeGeneration = useRef(0);
  const candidateSetVersion = useRef(0);
  const candidateRefs = useRef(new Set<string>());
  const candidatePreviewQueue = useRef<CandidatePreviewTask[]>([]);
  const candidatePreviewWorkers = useRef(0);
  const selectedPreviewRequest = useRef(0);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const [candidates, setCandidates] = useState<OrganizationImageCandidate[]>([]);
  const [legacyCandidates, setLegacyCandidates] = useState<OrganizationImageCandidate[]>([]);
  const [candidatePreviews, setCandidatePreviews] = useState<Record<string, string | null>>({});
  const [candidateOriginalPreviews, setCandidateOriginalPreviews] = useState<Record<string, string>>({});
  const [selectedRef, setSelectedRef] = useState<string | null>(null);
  const [selectedOriginalLoading, setSelectedOriginalLoading] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadPreview, setUploadPreview] = useState<string | null>(null);
  const [uploadSelected, setUploadSelected] = useState(false);
  const [imageKind, setImageKind] = useState<"photo" | "logo">("photo");
  const [focusX, setFocusX] = useState(0.5);
  const [focusY, setFocusY] = useState(0.5);
  const [zoom, setZoom] = useState(MIN_COVER_ZOOM);
  const [processed, setProcessed] = useState<ProcessedOrganizationImage | null>(null);
  const [processedPreviews, setProcessedPreviews] = useState<Partial<Record<ImageVariant, string>>>({});
  const [activePreviews, setActivePreviews] = useState<Partial<Record<ImageVariant, string>>>({});
  const [imageState, setImageState] = useState<OrganizationImageState | null>(null);
  const [altText, setAltText] = useState("");
  const [publicCredit, setPublicCredit] = useState("");
  const [officialAttempted, setOfficialAttempted] = useState(false);
  const [sourcePanel, setSourcePanel] = useState<ImageSourcePanel>(null);
  const [searchContext, setSearchContext] = useState<OrganizationImageSearchContext | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchQueryEdited, setSearchQueryEdited] = useState(false);
  const [selectedMunicipality, setSelectedMunicipality] = useState<string | null>(null);
  const [municipalityExplicit, setMunicipalityExplicit] = useState(false);
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null);
  const [selectedPersonId, setSelectedPersonId] = useState<number | null>(null);
  const [lastSearch, setLastSearch] = useState<{ query: string; sources: string[] } | null>(null);
  const [directImageUrl, setDirectImageUrl] = useState("");
  const [busy, setBusy] = useState<
    "state" | "discover" | "search-context" | "brave" | "url" | "process" | "approve" | null
  >(null);
  const [error, setError] = useState<string | null>(null);

  function rememberObjectUrl(blob: Blob, generation: number, expectedCandidateSetVersion?: number): string {
    const url = URL.createObjectURL(blob);
    if (
      scopeGeneration.current !== generation
      || (typeof expectedCandidateSetVersion === "number" && candidateSetVersion.current !== expectedCandidateSetVersion)
    ) {
      URL.revokeObjectURL(url);
      return "";
    }
    objectUrls.current.push(url);
    return url;
  }

  function revokePreviewUrls(
    urls: Partial<Record<ImageVariant, string>> | Record<string, string | null>,
  ) {
    const revoked = new Set(Object.values(urls).filter(Boolean));
    revoked.forEach((url) => URL.revokeObjectURL(url!));
    objectUrls.current = objectUrls.current.filter((url) => !revoked.has(url));
  }

  function pumpCandidatePreviewQueue() {
    while (
      candidatePreviewWorkers.current < MAX_CANDIDATE_PREVIEW_CONCURRENCY
      && candidatePreviewQueue.current.length > 0
    ) {
      const task = candidatePreviewQueue.current.shift()!;
      candidatePreviewWorkers.current += 1;
      getCandidatePreview(tenantId, organizationId, task.candidateRef)
        .then((blob) => {
          const url = rememberObjectUrl(blob, task.generation, task.candidateSetVersion);
          if (!url) return;
          setCandidatePreviews((current) => ({ ...current, [task.candidateRef]: url }));
        })
        .catch(() => {
          if (
            scopeGeneration.current === task.generation
            && candidateSetVersion.current === task.candidateSetVersion
          ) {
            setCandidatePreviews((current) => ({ ...current, [task.candidateRef]: null }));
          }
        })
        .finally(() => {
          candidatePreviewWorkers.current -= 1;
          pumpCandidatePreviewQueue();
        });
    }
  }

  function enqueueCandidatePreviews(nextCandidates: OrganizationImageCandidate[], generation: number) {
    const version = candidateSetVersion.current;
    candidatePreviewQueue.current.push(
      ...nextCandidates.map((candidate) => ({
        candidateRef: candidate.candidate_ref,
        generation,
        candidateSetVersion: version,
      })),
    );
    pumpCandidatePreviewQueue();
  }

  function clearSelectedCandidate() {
    selectedPreviewRequest.current += 1;
    setSelectedRef(null);
    setUploadSelected(false);
    setSelectedOriginalLoading(false);
  }

  function replaceCandidates(nextCandidates: OrganizationImageCandidate[], generation: number) {
    candidateSetVersion.current += 1;
    candidatePreviewQueue.current = [];
    candidateRefs.current = new Set(nextCandidates.map((candidate) => candidate.candidate_ref));
    revokePreviewUrls(candidatePreviews);
    revokePreviewUrls(candidateOriginalPreviews);
    setCandidatePreviews({});
    setCandidateOriginalPreviews({});
    setCandidates(nextCandidates);
    clearSelectedCandidate();
    enqueueCandidatePreviews(nextCandidates, generation);
  }

  function appendCandidates(nextCandidates: OrganizationImageCandidate[], generation: number) {
    const additions = nextCandidates.filter((candidate) => !candidateRefs.current.has(candidate.candidate_ref));
    if (additions.length === 0) return;
    additions.forEach((candidate) => candidateRefs.current.add(candidate.candidate_ref));
    setCandidates((current) => [...current, ...additions]);
    enqueueCandidatePreviews(additions, generation);
  }

  async function loadPreviews(
    previewRef: string,
    generation: number,
  ): Promise<Partial<Record<ImageVariant, string>>> {
    const entries = await Promise.all(
      IMAGE_VARIANTS.map(async (variant) => [
        variant,
        rememberObjectUrl(
          await getRenditionPreview(tenantId, organizationId, previewRef, variant),
          generation,
        ),
      ] as const),
    );
    if (scopeGeneration.current !== generation) return {};
    return Object.fromEntries(entries);
  }

  async function loadState(generation: number) {
    const state = await getOrganizationImageState(tenantId, organizationId);
    if (scopeGeneration.current !== generation) return;
    setImageState(state);
    if (state.active_selection) {
      setAltText(state.active_selection.alt_text);
      setPublicCredit(state.active_selection.public_credit);
      if (state.active_selection.rendition_preview_ref) {
        const previews = await loadPreviews(state.active_selection.rendition_preview_ref, generation);
        if (scopeGeneration.current !== generation) return;
        revokePreviewUrls(activePreviews);
        setActivePreviews(previews);
      }
    } else {
      revokePreviewUrls(activePreviews);
      setActivePreviews({});
      setAltText("");
      setPublicCredit("");
    }
  }

  function invalidateProcessing() {
    revokePreviewUrls(processedPreviews);
    setProcessed(null);
    setProcessedPreviews({});
  }

  useEffect(() => {
    const generation = scopeGeneration.current + 1;
    scopeGeneration.current = generation;
    candidateSetVersion.current += 1;
    selectedPreviewRequest.current += 1;
    candidateRefs.current = new Set();
    candidatePreviewQueue.current = [];
    setCandidates([]);
    setLegacyCandidates([]);
    setCandidatePreviews({});
    setCandidateOriginalPreviews({});
    setSelectedRef(null);
    setSelectedOriginalLoading(false);
    setUploadFile(null);
    setUploadPreview(null);
    setUploadSelected(false);
    setImageKind("photo");
    setFocusX(0.5);
    setFocusY(0.5);
    setZoom(MIN_COVER_ZOOM);
    setProcessed(null);
    setProcessedPreviews({});
    setActivePreviews({});
    setImageState(null);
    setAltText("");
    setPublicCredit("");
    setOfficialAttempted(false);
    setSourcePanel(null);
    setSearchContext(null);
    setSearchQuery("");
    setSearchQueryEdited(false);
    setSelectedMunicipality(null);
    setMunicipalityExplicit(false);
    setSelectedCategoryId(null);
    setSelectedPersonId(null);
    setLastSearch(null);
    setDirectImageUrl("");
    let cancelled = false;
    setBusy("state");
    setError(null);
    Promise.all([
      loadState(generation),
      getLegacyImageCandidates(tenantId, organizationId).then((items) => {
        if (scopeGeneration.current !== generation) return;
        setLegacyCandidates(items);
        items.forEach((candidate) => candidateRefs.current.add(candidate.candidate_ref));
      }),
    ])
      .catch((nextError) => {
        if (!cancelled && scopeGeneration.current === generation) setError(imageFlowError(nextError));
      })
      .finally(() => {
        if (!cancelled && scopeGeneration.current === generation) setBusy(null);
      });
    return () => {
      cancelled = true;
      scopeGeneration.current += 1;
      objectUrls.current.forEach((url) => URL.revokeObjectURL(url));
      objectUrls.current = [];
    };
    // Organization identity is the lifecycle boundary for all transient refs and blobs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId, organizationId]);

  async function onDiscover() {
    const generation = scopeGeneration.current;
    setOfficialAttempted(true);
    setBusy("discover");
    setError(null);
    invalidateProcessing();
    try {
      const discovered = await discoverOfficialImages(tenantId, organizationId);
      if (scopeGeneration.current !== generation) return;
      replaceCandidates(discovered, generation);
    } catch (nextError) {
      if (scopeGeneration.current === generation) setError(imageFlowError(nextError));
    } finally {
      if (scopeGeneration.current === generation) setBusy(null);
    }
  }

  function applySearchContext(context: OrganizationImageSearchContext) {
    setSearchContext(context);
    setSearchQuery(context.suggested_query);
    setSearchQueryEdited(false);
    setSelectedMunicipality(defaultSearchMunicipality(context));
    setMunicipalityExplicit(false);
    setSelectedCategoryId(null);
    setSelectedPersonId(null);
    setLastSearch(null);
  }

  async function onOpenBraveSearch() {
    setSourcePanel("brave");
    if (searchContext) return;
    const generation = scopeGeneration.current;
    setBusy("search-context");
    setError(null);
    try {
      const context = await getImageSearchContext(tenantId, organizationId);
      if (scopeGeneration.current !== generation) return;
      applySearchContext(context);
    } catch (nextError) {
      if (scopeGeneration.current === generation) setError(imageFlowError(nextError, "brave"));
    } finally {
      if (scopeGeneration.current === generation) setBusy(null);
    }
  }

  function resetSearchSuggestion() {
    if (searchContext) applySearchContext(searchContext);
  }

  function updateMunicipality(value: string) {
    if (!searchContext) return;
    const nextValue = selectedMunicipality === value && municipalityExplicit ? null : value;
    setSelectedMunicipality(nextValue);
    setMunicipalityExplicit(nextValue !== null);
    setSearchQuery(buildRefinedSearchQuery(searchContext, nextValue, selectedCategoryId, selectedPersonId));
    setSearchQueryEdited(false);
  }

  function updateCategory(categoryId: number) {
    if (!searchContext) return;
    const nextId = selectedCategoryId === categoryId ? null : categoryId;
    setSelectedCategoryId(nextId);
    setSearchQuery(buildRefinedSearchQuery(searchContext, selectedMunicipality, nextId, selectedPersonId));
    setSearchQueryEdited(false);
  }

  function updatePerson(personId: number) {
    if (!searchContext) return;
    const nextId = selectedPersonId === personId ? null : personId;
    setSelectedPersonId(nextId);
    setSearchQuery(buildRefinedSearchQuery(searchContext, selectedMunicipality, selectedCategoryId, nextId));
    setSearchQueryEdited(false);
  }

  async function onBraveSearch() {
    if (!searchContext || !searchQuery.trim()) return;
    const generation = scopeGeneration.current;
    setBusy("brave");
    setError(null);
    invalidateProcessing();
    try {
      const result = await searchBraveImages(tenantId, organizationId, {
        query: searchQuery,
        municipality: searchQueryEdited && !municipalityExplicit ? null : selectedMunicipality,
        category_id: selectedCategoryId,
        person_id: selectedPersonId,
        query_edited: searchQueryEdited,
      });
      if (scopeGeneration.current !== generation) return;
      setLastSearch({ query: result.search_query, sources: result.query_sources });
      appendCandidates(result.candidates, generation);
      clearSelectedCandidate();
    } catch (nextError) {
      if (scopeGeneration.current === generation) setError(imageFlowError(nextError, "brave"));
    } finally {
      if (scopeGeneration.current === generation) setBusy(null);
    }
  }

  async function onDirectUrlCandidate() {
    if (!directImageUrl.trim()) return;
    const generation = scopeGeneration.current;
    setBusy("url");
    setError(null);
    invalidateProcessing();
    try {
      const candidate = await createDirectUrlCandidate(tenantId, organizationId, directImageUrl.trim());
      if (scopeGeneration.current !== generation) return;
      const previewBlob = await getCandidatePreview(
        tenantId,
        organizationId,
        candidate.candidate_ref,
        { original: true },
      );
      const previewUrl = rememberObjectUrl(previewBlob, generation, candidateSetVersion.current);
      if (scopeGeneration.current !== generation || !previewUrl) return;
      if (!candidateRefs.current.has(candidate.candidate_ref)) {
        candidateRefs.current.add(candidate.candidate_ref);
        setCandidates((current) => [...current, candidate]);
      }
      setCandidatePreviews((current) => ({ ...current, [candidate.candidate_ref]: previewUrl }));
      setCandidateOriginalPreviews((current) => ({ ...current, [candidate.candidate_ref]: previewUrl }));
      clearSelectedCandidate();
    } catch (nextError) {
      if (scopeGeneration.current === generation) setError(imageFlowError(nextError, "direct_url"));
    } finally {
      if (scopeGeneration.current === generation) setBusy(null);
    }
  }

  function onUploadFile(nextFile: File | null) {
    if (uploadPreview) revokePreviewUrls({ upload: uploadPreview });
    setUploadFile(nextFile);
    clearSelectedCandidate();
    invalidateProcessing();
    if (!nextFile) {
      setUploadPreview(null);
      return;
    }
    setUploadPreview(rememberObjectUrl(nextFile, scopeGeneration.current));
  }

  async function selectRemoteCandidate(candidateRef: string) {
    const generation = scopeGeneration.current;
    const version = candidateSetVersion.current;
    const request = selectedPreviewRequest.current + 1;
    selectedPreviewRequest.current = request;
    setSelectedRef(candidateRef);
    setUploadSelected(false);
    setError(null);
    setFocusX(0.5);
    setFocusY(0.5);
    setZoom(MIN_COVER_ZOOM);
    invalidateProcessing();
    if (candidateOriginalPreviews[candidateRef]) {
      setSelectedOriginalLoading(false);
      return;
    }
    setSelectedOriginalLoading(true);
    try {
      const blob = await getCandidatePreview(tenantId, organizationId, candidateRef, { original: true });
      if (
        scopeGeneration.current !== generation
        || candidateSetVersion.current !== version
        || selectedPreviewRequest.current !== request
      ) return;
      const url = rememberObjectUrl(blob, generation, version);
      if (!url || selectedPreviewRequest.current !== request) return;
      setCandidateOriginalPreviews((current) => ({ ...current, [candidateRef]: url }));
    } catch (nextError) {
      if (
        scopeGeneration.current === generation
        && candidateSetVersion.current === version
        && selectedPreviewRequest.current === request
      ) {
        const candidate = [...legacyCandidates, ...candidates].find((item) => item.candidate_ref === candidateRef);
        setError(imageFlowError(nextError, candidate?.source_type === "pasted_url" ? "direct_url" : "generic"));
      }
    } finally {
      if (selectedPreviewRequest.current === request) setSelectedOriginalLoading(false);
    }
  }

  function selectUploadCandidate() {
    if (!uploadFile) return;
    selectedPreviewRequest.current += 1;
    setSelectedRef(null);
    setUploadSelected(true);
    setSelectedOriginalLoading(false);
    setFocusX(0.5);
    setFocusY(0.5);
    setZoom(MIN_COVER_ZOOM);
    invalidateProcessing();
  }

  function updateFocus(axis: "x" | "y", value: number) {
    if (axis === "x") setFocusX(value);
    else setFocusY(value);
    invalidateProcessing();
  }

  function updateZoom(value: number) {
    setZoom(value);
    invalidateProcessing();
  }

  function resetCropRecipe() {
    setFocusX(0.5);
    setFocusY(0.5);
    setZoom(MIN_COVER_ZOOM);
    invalidateProcessing();
  }

  async function onProcess() {
    if (
      !(uploadSelected && uploadFile)
      && (!selectedRef || !candidateOriginalPreviews[selectedRef])
    ) return;
    const generation = scopeGeneration.current;
    setBusy("process");
    setError(null);
    try {
      const processingPayload = {
        image_kind: imageKind,
        ...(imageKind === "photo" ? { focus_x: focusX, focus_y: focusY, zoom } : {}),
      };
      const result = uploadSelected && uploadFile
        ? await processUploadedOrganizationImage(tenantId, organizationId, {
            file: uploadFile,
            ...processingPayload,
          })
        : await processOrganizationImage(tenantId, organizationId, {
            candidate_ref: selectedRef!,
            ...processingPayload,
          });
      if (scopeGeneration.current !== generation) return;
      const previews = await loadPreviews(result.rendition_preview_ref, generation);
      if (scopeGeneration.current !== generation) return;
      revokePreviewUrls(processedPreviews);
      setProcessed(result);
      setProcessedPreviews(previews);
    } catch (nextError) {
      if (scopeGeneration.current === generation) {
        setError(imageFlowError(nextError, uploadSelected ? "upload" : "generic"));
      }
    } finally {
      if (scopeGeneration.current === generation) setBusy(null);
    }
  }

  async function onApprove() {
    if (!processed || !imageState) return;
    const generation = scopeGeneration.current;
    setBusy("approve");
    setError(null);
    try {
      await approveOrganizationImage(tenantId, organizationId, {
        approval_ref: processed.approval_ref,
        expected_revision: imageState.expected_revision,
        alt_text: altText.trim(),
        public_credit: publicCredit.trim(),
      });
      if (scopeGeneration.current !== generation) return;
      await loadState(generation);
      if (scopeGeneration.current !== generation) return;
      invalidateProcessing();
    } catch (nextError) {
      if (scopeGeneration.current === generation) setError(imageFlowError(nextError));
    } finally {
      if (scopeGeneration.current === generation) setBusy(null);
    }
  }

  const selectedPreviewUrl = uploadSelected
    ? uploadPreview
    : selectedRef
      ? candidateOriginalPreviews[selectedRef] ?? null
      : null;
  const hasSelectedCandidate = Boolean(
    (uploadSelected && uploadFile)
    || (selectedRef && candidateOriginalPreviews[selectedRef]),
  );
  const currentQuerySources = searchQueryEdited
    ? [
        "manual_edit",
        ...(municipalityExplicit && selectedMunicipality ? ["municipality"] : []),
        ...(selectedCategoryId ? ["category"] : []),
        ...(selectedPersonId ? ["person"] : []),
      ]
    : [
        "organization_name",
        ...(selectedMunicipality ? ["municipality"] : []),
        ...(selectedCategoryId ? ["category"] : []),
        ...(selectedPersonId ? ["person"] : []),
      ];
  const unusedQuerySources = [
    ...(searchContext?.municipalities.length && !selectedMunicipality ? ["kommune"] : []),
    ...(!selectedCategoryId ? ["kategorier"] : []),
    "tags",
    ...(!selectedPersonId ? ["personer"] : []),
  ];

  return (
    <section className="organization-image-panel" aria-labelledby="organization-image-heading">
      <div className="sidebar-header">
        <div>
          <p className="eyebrow small">Intern bildeflyt</p>
          <h2 id="organization-image-heading">Aktørbilde</h2>
        </div>
        <button type="button" className="ghost-button" onClick={onDiscover} disabled={busy !== null}>
          {busy === "discover" ? "Finner bilder..." : "Finn bilder"}
        </button>
      </div>
      <p className="muted">
        Finn kandidater fra aktørens offisielle nettside. Ingenting blir valgt før du godkjenner eksplisitt.
      </p>
      {error ? <div className="inline-banner warn" role="alert">{error}</div> : null}
      {imageState?.active_selection ? (
        <div className="image-active-state">
          <strong>Aktivt bilde</strong>
          <span className="meta">Revisjon {imageState.active_selection.revision}</span>
          <span className="meta">{imageState.active_selection.alt_text || "Ingen alt-tekst"}</span>
          <ImagePreviewGrid urls={activePreviews} label="Forhåndsvisning av aktivt bilde" />
        </div>
      ) : busy !== "state" ? (
        <div className="empty-state compact">Ingen aktivt valgt bilde ennå.</div>
      ) : null}

      {legacyCandidates.length > 0 ? (
        <div className="image-source-section" aria-label="Tidligere lagrede bilder">
          <strong>Tidligere lagrede bilder</strong>
          <p className="muted">
            Disse historiske URL-ene er bare forslag. Forhåndsvisning og godkjenning må gjøres eksplisitt.
          </p>
          <div className="image-candidate-grid">
            {legacyCandidates.map((candidate) => (
              <button
                type="button"
                key={candidate.candidate_ref}
                className={`image-candidate-card ${selectedRef === candidate.candidate_ref ? "active" : ""}`}
                disabled={busy !== null}
                onClick={() => { void selectRemoteCandidate(candidate.candidate_ref); }}
              >
                {candidateOriginalPreviews[candidate.candidate_ref] ? (
                  <img src={candidateOriginalPreviews[candidate.candidate_ref]} alt="" />
                ) : (
                  <span className="empty-state compact">Ingen automatisk forhåndshenting</span>
                )}
                <strong>{candidate.source_label}</strong>
                <span className="meta">{candidate.source_domain ?? "Ukjent kilde"}</span>
                <span>{selectedRef === candidate.candidate_ref ? "Valgt bilde" : "Forhåndsvis og velg"}</span>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {candidates.length > 0 || uploadFile ? (
        <div className="image-candidate-grid">
          {candidates.map((candidate) => (
            <button
              type="button"
              key={candidate.candidate_ref}
              className={`image-candidate-card ${selectedRef === candidate.candidate_ref ? "active" : ""}`}
              disabled={busy !== null}
              onClick={() => { void selectRemoteCandidate(candidate.candidate_ref); }}
            >
              {candidatePreviews[candidate.candidate_ref] ? (
                <img src={candidatePreviews[candidate.candidate_ref]!} alt="" />
              ) : candidatePreviews[candidate.candidate_ref] === null ? (
                <span className="empty-state compact">Preview utilgjengelig</span>
              ) : (
                <span className="empty-state compact">Laster preview...</span>
              )}
              <strong>{candidate.source_label}</strong>
              {candidate.source_title ? <span>{candidate.source_title}</span> : null}
              <span className="meta">{candidateSourceDetails(candidate)}</span>
              <span className="meta">
                {candidate.width && candidate.height ? `${candidate.width} × ${candidate.height}` : "Ukjente dimensjoner"}
              </span>
              <span>{selectedRef === candidate.candidate_ref ? "Valgt bilde" : "Velg bilde"}</span>
            </button>
          ))}
          {uploadFile ? (
            <button
              type="button"
              className={`image-candidate-card ${uploadSelected ? "active" : ""}`}
              disabled={busy !== null}
              onClick={selectUploadCandidate}
            >
              {uploadPreview ? <img src={uploadPreview} alt="" /> : <span className="empty-state compact">Preview utilgjengelig</span>}
              <strong>Lastet opp</strong>
              <span>{uploadFile.name}</span>
              <span className="meta">{Math.max(1, Math.round(uploadFile.size / 1024))} kB · kontrolleres av serveren ved processing</span>
              <span>{uploadSelected ? "Valgt bilde" : "Velg bilde"}</span>
            </button>
          ) : null}
        </div>
      ) : busy === null && officialAttempted ? (
        <div className="empty-state compact">Ingen kandidater funnet fra offisiell nettside. Prøv en alternativ kilde.</div>
      ) : busy === null ? (
        <div className="empty-state compact">Klikk «Finn bilder» for å hente kandidater fra offisiell nettside.</div>
      ) : null}

      {selectedRef && selectedOriginalLoading ? (
        <div className="empty-state compact" role="status">Henter originalbilde for live crop...</div>
      ) : null}

      {officialAttempted ? (
        <div className="image-source-section">
          <div className="image-source-actions" aria-label="Alternative bildekilder">
            <button type="button" className="ghost-button" aria-pressed={sourcePanel === "brave"} disabled={busy !== null} onClick={onOpenBraveSearch}>
              Søk etter flere bilder
            </button>
            <button type="button" className="ghost-button" aria-pressed={sourcePanel === "url"} disabled={busy !== null} onClick={() => setSourcePanel("url")}>
              Lim inn bilde-URL
            </button>
            <button type="button" className="ghost-button" aria-pressed={sourcePanel === "upload"} disabled={busy !== null} onClick={() => setSourcePanel("upload")}>
              Last opp bilde
            </button>
          </div>
          <p className="muted">
            Oppgi eventuell kreditering før bildet godkjennes.
          </p>

          {sourcePanel === "brave" ? (
            <div className="image-source-panel" aria-label="Bildesøk">
              {searchContext ? (
                <>
                  <p className="muted">
                    Bildesøket utføres via Brave Search. Søketeksten sendes til Brave og kan lagres der i opptil 90 dager. Ikke skriv sensitiv eller intern informasjon i søket.
                  </p>
                  <Field label={searchQueryEdited ? "Søk" : "Forslått søk"}>
                    <input
                      value={searchQuery}
                      disabled={busy !== null}
                      onChange={(event) => {
                        setSearchQuery(event.target.value);
                        setSearchQueryEdited(true);
                        setSelectedMunicipality(null);
                        setMunicipalityExplicit(false);
                        setSelectedCategoryId(null);
                        setSelectedPersonId(null);
                      }}
                    />
                  </Field>
                  <div className="image-query-explanation">
                    <span><strong>Basert på:</strong> {currentQuerySources.map((source) => QUERY_SOURCE_LABELS[source] ?? source).join(" + ")}</span>
                    <span className="meta"><strong>Ikke brukt:</strong> {unusedQuerySources.join(", ")}</span>
                  </div>

                  {searchContext.municipalities.length > 1 ? (
                    <fieldset className="image-refinement-group">
                      <legend>Refiner med sted</legend>
                      <div className="image-choice-row">
                        {searchContext.municipalities.map((municipality) => (
                          <button
                            key={municipality}
                            type="button"
                            className="ghost-button"
                            aria-pressed={municipalityExplicit && selectedMunicipality === municipality}
                            disabled={busy !== null}
                            onClick={() => updateMunicipality(municipality)}
                          >
                            {municipality}
                          </button>
                        ))}
                      </div>
                    </fieldset>
                  ) : null}

                  {searchContext.categories.length > 0 ? (
                    <fieldset className="image-refinement-group">
                      <legend>Legg til kategori</legend>
                      <div className="image-choice-row">
                        {searchContext.categories.map((category) => (
                          <button
                            key={category.id}
                            type="button"
                            className="ghost-button"
                            aria-pressed={selectedCategoryId === category.id}
                            disabled={busy !== null}
                            onClick={() => updateCategory(category.id)}
                          >
                            {category.name}
                          </button>
                        ))}
                      </div>
                    </fieldset>
                  ) : null}

                  {searchContext.people.length > 0 ? (
                    <fieldset className="image-refinement-group">
                      <legend>Søk med tilknyttet person</legend>
                      <div className="image-choice-row">
                        {searchContext.people.map((person) => (
                          <button
                            key={person.id}
                            type="button"
                            className="ghost-button"
                            aria-pressed={selectedPersonId === person.id}
                            disabled={busy !== null}
                            onClick={() => updatePerson(person.id)}
                          >
                            {person.name}
                          </button>
                        ))}
                      </div>
                    </fieldset>
                  ) : null}

                  <div className="image-source-actions">
                    <button type="button" className="primary-button" disabled={!searchQuery.trim() || busy !== null} onClick={onBraveSearch}>
                      {busy === "brave" ? "Søker..." : "Søk"}
                    </button>
                    <button type="button" className="ghost-button" disabled={busy !== null} onClick={resetSearchSuggestion}>
                      Tilbakestill til forslag
                    </button>
                  </div>
                  {lastSearch ? (
                    <div className="image-query-result" aria-live="polite">
                      <span><strong>Søk:</strong> «{lastSearch.query}»</span>
                      <span className="meta"><strong>Basert på:</strong> {lastSearch.sources.map((source) => QUERY_SOURCE_LABELS[source] ?? source).join(" + ")}</span>
                    </div>
                  ) : null}
                  <p className="muted">Bildesøk viser forslag fra nettet. Kontroller at bildet kan brukes før du godkjenner det.</p>
                </>
              ) : (
                <div className="empty-state compact">{busy === "search-context" ? "Laster søkeforslag..." : "Søkeforslaget kunne ikke lastes."}</div>
              )}
            </div>
          ) : null}

          {sourcePanel === "url" ? (
            <div className="image-source-panel" aria-label="Direkte bilde-URL">
              <Field label="Direkte bilde-URL">
                <input
                  type="url"
                  value={directImageUrl}
                  disabled={busy !== null}
                  placeholder="https://eksempel.no/bilde.jpg"
                  onChange={(event) => setDirectImageUrl(event.target.value)}
                />
              </Field>
              <button type="button" className="primary-button" disabled={!directImageUrl.trim() || busy !== null} onClick={onDirectUrlCandidate}>
                {busy === "url" ? "Henter bilde..." : "Hent bilde"}
              </button>
            </div>
          ) : null}

          {sourcePanel === "upload" ? (
            <div className="image-source-panel" aria-label="Last opp bilde">
              <input
                ref={uploadInputRef}
                className="visually-hidden-input"
                aria-label="Velg JPEG-, PNG- eller WebP-bilde"
                type="file"
                accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
                disabled={busy !== null}
                onChange={(event) => onUploadFile(event.target.files?.[0] ?? null)}
              />
              <div className="file-picker-field">
                <button type="button" className="ghost-button" disabled={busy !== null} onClick={() => uploadInputRef.current?.click()}>
                  Velg fil
                </button>
                <span className="meta">{uploadFile?.name || "Ingen fil valgt"}</span>
              </div>
              <p className="muted">Støttede formater: JPEG, PNG og WebP. Filen kontrolleres av serveren når du prosesserer bildet.</p>
            </div>
          ) : null}
        </div>
      ) : null}

      {hasSelectedCandidate ? (
        <div className="image-processing-controls">
          <div className="image-processing-layout">
            <Field label="Bildetype">
              <select
                value={imageKind}
                disabled={busy !== null}
                onChange={(event) => {
                  setImageKind(event.target.value as "photo" | "logo");
                  invalidateProcessing();
                }}
              >
                <option value="photo">Foto</option>
                <option value="logo">Logo</option>
              </select>
            </Field>
            {imageKind === "photo" ? (
              <div className="image-focus-and-preview">
                <p className="muted">Foto fyller hele bildeflaten og kan derfor beskjæres. Bruk fokus og zoom for å styre utsnittet.</p>
                <div className="image-focus-controls">
                  <fieldset className="image-focus-group">
                    <legend>Horisontalt</legend>
                    <div className="image-choice-row">
                      {([0, 0.5, 1] as const).map((value, index) => (
                        <button
                          key={value}
                          type="button"
                          className="ghost-button"
                          aria-pressed={focusX === value}
                          disabled={busy !== null}
                          onClick={() => updateFocus("x", value)}
                        >
                          {(["Venstre", "Midt", "Høyre"] as const)[index]}
                        </button>
                      ))}
                    </div>
                  </fieldset>
                  <fieldset className="image-focus-group">
                    <legend>Vertikalt</legend>
                    <div className="image-choice-row">
                      {([0, 0.5, 1] as const).map((value, index) => (
                        <button
                          key={value}
                          type="button"
                          className="ghost-button"
                          aria-pressed={focusY === value}
                          disabled={busy !== null}
                          onClick={() => updateFocus("y", value)}
                        >
                          {(["Topp", "Midt", "Bunn"] as const)[index]}
                        </button>
                      ))}
                    </div>
                  </fieldset>
                </div>
                <details className="image-fine-crop-controls">
                  <summary>Finjuster utsnitt</summary>
                  <div className="image-slider-grid">
                    <label>
                      <span>Horisontal plassering: {Math.round(focusX * 100)} %</span>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.01"
                        value={focusX}
                        disabled={busy !== null}
                        aria-label="Horisontal plassering"
                        onChange={(event) => updateFocus("x", Number(event.target.value))}
                      />
                    </label>
                    <label>
                      <span>Vertikal plassering: {Math.round(focusY * 100)} %</span>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.01"
                        value={focusY}
                        disabled={busy !== null}
                        aria-label="Vertikal plassering"
                        onChange={(event) => updateFocus("y", Number(event.target.value))}
                      />
                    </label>
                    <label>
                      <span>Zoom: {Math.round(zoom * 100)} %</span>
                      <input
                        type="range"
                        min={MIN_COVER_ZOOM}
                        max={MAX_COVER_ZOOM}
                        step="0.01"
                        value={zoom}
                        disabled={busy !== null}
                        aria-label="Zoom"
                        onChange={(event) => updateZoom(Number(event.target.value))}
                      />
                    </label>
                  </div>
                  <button type="button" className="ghost-button" disabled={busy !== null} onClick={resetCropRecipe}>
                    Tilbakestill utsnitt
                  </button>
                </details>
                <LiveCropPreviewGrid url={selectedPreviewUrl} focusX={focusX} focusY={focusY} zoom={zoom} />
                <p className="muted">Forhåndsvisningen oppdateres med én gang. Det endelige utsnittet lages med samme fokus og zoom når du trykker «Prosesser valgt bilde».</p>
              </div>
            ) : (
              <div className="image-logo-preview-block">
                <p className="muted">Logo viser hele motivet uten beskjæring.</p>
                {selectedPreviewUrl ? <img className="image-logo-preview" src={selectedPreviewUrl} alt="Forhåndsvisning av hele logoen" /> : null}
              </div>
            )}
          </div>
          <button type="button" className="primary-button" onClick={onProcess} disabled={busy !== null}>
            {busy === "process" ? "Prosesserer..." : "Prosesser valgt bilde"}
          </button>
        </div>
      ) : null}

      {processed ? (
        <div className="image-approval-panel">
          <ImagePreviewGrid urls={processedPreviews} label="Serverens bildeformater" />
          {processed.warnings.length > 0 ? (
            <div className="inline-banner warn">Tekniske varsler: {processed.warnings.join(", ")}</div>
          ) : null}
          <Field label="Alt-tekst (valgfritt)">
            <input maxLength={500} value={altText} onChange={(event) => setAltText(event.target.value)} placeholder={`Beskriv bildet av ${organizationName}`} />
            <span className="meta">Anbefalt for tilgjengelighet.</span>
          </Field>
          <Field label="Offentlig kreditering (valgfritt)">
            <input value={publicCredit} onChange={(event) => setPublicCredit(event.target.value)} />
          </Field>
          <button type="button" className="primary-button" onClick={onApprove} disabled={busy !== null}>
            {busy === "approve"
              ? "Godkjenner..."
              : imageState?.active_selection
                ? "Godkjenn og erstatt bilde"
                : "Godkjenn og lås bilde"}
          </button>
        </div>
      ) : null}
    </section>
  );
}

function LiveCropPreviewGrid(props: {
  url: string | null;
  focusX: number;
  focusY: number;
  zoom: number;
}) {
  const [sourceSize, setSourceSize] = useState<readonly [number, number] | null>(null);
  useEffect(() => setSourceSize(null), [props.url]);
  return (
    <div className="image-live-crop-grid" aria-label="Live crop-preview">
      {IMAGE_VARIANTS.map((variant) => {
        const geometry = sourceSize
          ? calculateCoverCrop(sourceSize, IMAGE_VARIANT_SIZES[variant], props.focusX, props.focusY, props.zoom)
          : null;
        return (
        <figure key={variant}>
          <div className={`image-live-crop-frame ${variant}`}>
            {props.url ? (
              <img
                src={props.url}
                alt={`Live crop-preview: ${variant}`}
                onLoad={(event) => setSourceSize([event.currentTarget.naturalWidth, event.currentTarget.naturalHeight])}
                style={geometry ? {
                  width: `${(sourceSize![0] / geometry.width) * 100}%`,
                  height: `${(sourceSize![1] / geometry.height) * 100}%`,
                  left: `${(-geometry.left / geometry.width) * 100}%`,
                  top: `${(-geometry.top / geometry.height) * 100}%`,
                } : undefined}
              />
            ) : (
              <div className="empty-state compact">Laster preview...</div>
            )}
          </div>
          <figcaption>{IMAGE_VARIANT_LABELS[variant]}</figcaption>
        </figure>
      );})}
    </div>
  );
}

function roundHalfEven(value: number): number {
  const floor = Math.floor(value);
  const fraction = value - floor;
  if (fraction < 0.5) return floor;
  if (fraction > 0.5) return floor + 1;
  return floor % 2 === 0 ? floor : floor + 1;
}

export function calculateCoverCrop(
  source: readonly [number, number],
  target: readonly [number, number],
  focusX: number,
  focusY: number,
  zoom: number,
) {
  const sourceRatio = source[0] / source[1];
  const targetRatio = target[0] / target[1];
  let width: number;
  let height: number;
  if (sourceRatio > targetRatio) {
    height = Math.max(1, roundHalfEven(source[1] / zoom));
    width = Math.max(1, roundHalfEven(height * targetRatio));
  } else {
    width = Math.max(1, roundHalfEven(source[0] / zoom));
    height = Math.max(1, roundHalfEven(width / targetRatio));
  }
  const left = Math.min(Math.max(0, roundHalfEven(focusX * source[0] - width / 2)), source[0] - width);
  const top = Math.min(Math.max(0, roundHalfEven(focusY * source[1] - height / 2)), source[1] - height);
  return { left, top, width, height };
}

function ImagePreviewGrid(props: {
  urls: Partial<Record<ImageVariant, string>>;
  label: string;
}) {
  return (
    <div className="image-preview-grid" aria-label={props.label}>
      {IMAGE_VARIANTS.map((variant) => (
        <figure key={variant}>
          {props.urls[variant] ? <img src={props.urls[variant]} alt={`${props.label}: ${variant}`} /> : <div className="empty-state compact">Laster...</div>}
          <figcaption>{IMAGE_VARIANT_LABELS[variant]}</figcaption>
        </figure>
      ))}
    </div>
  );
}

function OrganizationLinksPanel({ navigate }: { navigate: (to: string) => void }) {
  const editor = useEditor();
  const [linkQuery, setLinkQuery] = useState("");
  const filteredAvailablePersons = useMemo(() => {
    const normalizedQuery = linkQuery.trim().toLowerCase();
    if (!normalizedQuery) return [];
    return editor.availablePersonsForLink
      .filter((person) =>
        [person.full_name, person.email ?? "", person.phone ?? "", person.municipality ?? ""]
          .join(" ")
          .toLowerCase()
          .includes(normalizedQuery),
      )
      .slice(0, 12);
  }, [editor.availablePersonsForLink, linkQuery]);
  return (
    <div className="link-section">
      <div className="sidebar-header">
        <h2>Personkoblinger</h2>
        <span className="meta">{editor.selectedOrganizationLinks.length} koblinger</span>
      </div>

      {typeof editor.selectedOrgId === "number" ? (
        <>
          <div className="link-section">
            <div className="sidebar-header">
              <h2>Opprett ny kontaktperson for denne aktøren</h2>
              <span className={`save-pill ${editor.linkedPersonSaveState}`}>{saveLabel(editor.linkedPersonSaveState)}</span>
            </div>
            <p className="muted">
              Denne flyten oppretter personen, lager første e-post/telefon hvis du fyller det ut, og knytter personen
              direkte til aktøren.
            </p>
            <form className="editor-form" onSubmit={editor.onCreateLinkedPerson}>
              <div className="grid two">
                <Field label="Fullt navn" required error={editor.linkedPersonFieldErrors.full_name}>
                  <input
                    value={editor.linkedPersonDraft.full_name}
                    onChange={(e) => editor.setLinkedPersonDraft((s) => ({ ...s, full_name: e.target.value }))}
                    required
                  />
                </Field>
                <Field label="Tittel">
                  <input
                    value={editor.linkedPersonDraft.title}
                    onChange={(e) => editor.setLinkedPersonDraft((s) => ({ ...s, title: e.target.value }))}
                    placeholder="f.eks. daglig leder, booking eller produsent"
                  />
                </Field>
              </div>

              <div className="grid two">
                <Field label="Kommune">
                  <input
                    value={editor.linkedPersonDraft.municipality}
                    onChange={(e) => editor.setLinkedPersonDraft((s) => ({ ...s, municipality: e.target.value }))}
                  />
                </Field>
              </div>

              <div className="grid two">
                <Field label="E-post" error={editor.linkedPersonFieldErrors.email}>
                  <input
                    type="email"
                    value={editor.linkedPersonDraft.email}
                    onChange={(e) => editor.setLinkedPersonDraft((s) => ({ ...s, email: e.target.value }))}
                  />
                </Field>
                <Field label="Telefon" error={editor.linkedPersonFieldErrors.phone}>
                  <div className="contact-inline-input">
                    <input
                      aria-label="Telefon"
                      value={editor.linkedPersonDraft.phone}
                      onChange={(e) =>
                        editor.setLinkedPersonDraft((state) => ({
                          ...state,
                          phone: e.target.value,
                          ...(e.target.value.trim().startsWith("+") ? { phone_region: null } : {}),
                        }))
                      }
                    />
                    <PhoneRegionSelect
                      value={editor.linkedPersonDraft.phone_region ?? ""}
                      onChange={(phoneRegion) =>
                        editor.setLinkedPersonDraft((state) => ({
                          ...state,
                          phone_region: phoneRegion || null,
                        }))
                      }
                    />
                  </div>
                </Field>
              </div>

              <div className="grid two">
                <label className="toggle-card">
                  <input
                    type="checkbox"
                    checked={editor.linkedPersonDraft.publish_email}
                    onChange={(e) => editor.setLinkedPersonDraft((s) => ({ ...s, publish_email: e.target.checked }))}
                  />
                  <div>
                    <strong>Gjør denne e-postadressen offentlig</strong>
                    <p>Vises i PUBLIC når personen også er publisert som kontaktperson.</p>
                  </div>
                </label>
                <label className="toggle-card">
                  <input
                    type="checkbox"
                    checked={editor.linkedPersonDraft.publish_phone}
                    onChange={(e) => editor.setLinkedPersonDraft((s) => ({ ...s, publish_phone: e.target.checked }))}
                  />
                  <div>
                    <strong>Gjør dette telefonnummeret offentlig</strong>
                    <p>Vises i PUBLIC når personen også er publisert som kontaktperson.</p>
                  </div>
                </label>
              </div>

              <div className="grid two">
                <label className="toggle-card">
                  <input
                    type="checkbox"
                    checked={editor.linkedPersonDraft.publish_person}
                    onChange={(e) => editor.setLinkedPersonDraft((s) => ({ ...s, publish_person: e.target.checked }))}
                  />
                  <div>
                    <strong>Vis ny person som kontaktperson offentlig</strong>
                    <p>Styrer om navn og eventuell tittel vises på denne aktørsiden.</p>
                  </div>
                </label>
                <Field label="Status på kobling">
                  <select
                    value={editor.linkedPersonDraft.status}
                    onChange={(e) =>
                      editor.setLinkedPersonDraft((s) => ({ ...s, status: e.target.value as "ACTIVE" | "INACTIVE" }))
                    }
                  >
                    <option value="ACTIVE">ACTIVE</option>
                    <option value="INACTIVE">INACTIVE</option>
                  </select>
                </Field>
              </div>

              <div className="actions">
                <button
                  type="submit"
                  className="primary-button"
                  disabled={!editor.linkedPersonDraft.full_name.trim() || editor.linkedPersonSaveState === "saving"}
                >
                  Opprett og knytt kontaktperson
                </button>
              </div>
            </form>
          </div>

          <form className="link-create searchable-link-create" onSubmit={editor.onCreateLink}>
            <div className="link-search-panel">
              <input
                type="search"
                className="search-input link-search-input"
                value={linkQuery}
                onChange={(event) => setLinkQuery(event.target.value)}
                placeholder="Søk etter person å knytte til aktøren"
                disabled={editor.availablePersonsForLink.length === 0}
              />
              {editor.availablePersonsForLink.length === 0 ? (
                <div className="empty-state compact">Alle personer er allerede koblet til denne aktøren.</div>
              ) : !linkQuery.trim() ? (
                <div className="empty-state compact">Skriv navn, kommune, e-post eller telefon for å finne riktig person.</div>
              ) : (
                <div className="link-search-results">
                  {filteredAvailablePersons.length > 0 ? (
                    filteredAvailablePersons.map((person) => {
                      const selected = editor.linkPersonId === person.id;
                      return (
                        <button
                          key={person.id}
                          type="button"
                          className={`link-search-result ${selected ? "active" : ""}`}
                          onClick={() => editor.setLinkPersonId(person.id)}
                        >
                          <strong>{person.full_name}</strong>
                          <span className="meta">
                            {[person.municipality, person.email, person.phone].filter(Boolean).join(" · ") || "Ingen kontaktinfo"}
                          </span>
                        </button>
                      );
                    })
                  ) : (
                    <div className="empty-state compact">Ingen personer matcher søket.</div>
                  )}
                </div>
              )}
            </div>
            <select
              value={editor.linkStatus}
              onChange={(e) => editor.setLinkStatus(e.target.value as "ACTIVE" | "INACTIVE")}
            >
              <option value="ACTIVE">ACTIVE</option>
              <option value="INACTIVE">INACTIVE</option>
            </select>

            <label className="inline-check">
              <input
                type="checkbox"
                checked={editor.linkPublishPerson}
                onChange={(e) => editor.setLinkPublishPerson(e.target.checked)}
              />
              <span>Vis eksisterende person som kontaktperson offentlig</span>
            </label>

            <button
              type="submit"
              className="ghost-button"
              disabled={!editor.linkPersonId || editor.availablePersonsForLink.length === 0}
            >
              Knytt eksisterende person
            </button>
          </form>

          <div className="link-list">
            {editor.selectedOrganizationLinks.map((link) => {
              const person = editor.personsById.get(link.person);
              const effectivePublication = describeEffectivePublication({
                linkStatus: link.status,
                publishPerson: link.publish_person,
                contacts: getPersonContacts(person, editor.personContacts),
              });
              return (
                <div key={link.id} className="link-row">
                  <div>
                    <div className="link-person">{person?.full_name ?? `Person #${link.person}`}</div>
                    <div className="meta">{person?.municipality || "Ingen kommune"} · ID {link.person}</div>
                    <div className={`publication-status ${effectivePublication.tone}`}>
                      {effectivePublication.message}
                    </div>
                  </div>

                  <div className="link-controls">
                    <select
                      value={link.status}
                      onChange={(e) =>
                        editor.updateLink(link.id, { status: e.target.value as "ACTIVE" | "INACTIVE" })
                      }
                    >
                      <option value="ACTIVE">ACTIVE</option>
                      <option value="INACTIVE">INACTIVE</option>
                    </select>

                    <label className="inline-check compact">
                      <input
                        type="checkbox"
                        checked={link.publish_person}
                        onChange={(e) => editor.updateLink(link.id, { publish_person: e.target.checked })}
                      />
                      <span>Vis person offentlig</span>
                    </label>

                    <button
                      type="button"
                      className="ghost-button"
                      onClick={() => {
                        editor.setSelectedPersonId(link.person);
                        navigate(`/people/${link.person}`);
                      }}
                    >
                      Rediger
                    </button>

                    <button
                      type="button"
                      className="link-delete"
                      onClick={() => {
                        const personName = person?.full_name ?? `Person #${link.person}`;
                        if (window.confirm(`Fjerne koblingen mellom organisasjonen og ${personName}?`)) {
                          editor.removeLink(link.id);
                        }
                      }}
                    >
                      Fjern
                    </button>
                  </div>
                </div>
              );
            })}
            {editor.selectedOrganizationLinks.length === 0 ? (
              <div className="empty-state">Ingen personer koblet til denne organisasjonen.</div>
            ) : null}
          </div>
        </>
      ) : (
        <div className="empty-state">Lagre eller velg en organisasjon for å administrere personkoblinger.</div>
      )}
    </div>
  );
}

function OrganizationPreviewPanel({ invalidOrgRoute }: { invalidOrgRoute: boolean }) {
  const editor = useEditor();
  return (
    <section className="panel preview">
      {editor.tenantDataLoading ? (
        <div className="route-missing">
          <p className="eyebrow small">Laster</p>
          <h2>Preview lastes...</h2>
          <p className="muted">Preview vises når aktørdata er lastet.</p>
        </div>
      ) : invalidOrgRoute ? (
        <div className="route-missing">
          <p className="eyebrow small">Preview utilgjengelig</p>
          <h2>Ingen aktør valgt</h2>
          <p className="muted">Velg en gyldig aktør fra listen for å se preview.</p>
        </div>
      ) : (
        <>
          <div className="sidebar-header">
            <h2>Public Preview (legacy)</h2>
            <div className="actions">
              <span className={`dot ${editor.draft.is_published ? "green" : "gray"}`} />
              <button
                type="button"
                className="ghost-button"
                onClick={editor.onRefreshOrganizationPreview}
                disabled={typeof editor.selectedOrgId !== "number" || editor.previewRefreshState === "saving"}
              >
                {editor.previewRefreshState === "saving" ? "Henter preview..." : "Oppdater preview"}
              </button>
            </div>
          </div>

          <div className="preview-card">
            {editor.selectedOrganization?.preview_image_url ? (
              <img
                src={editor.selectedOrganization.preview_image_url}
                alt={editor.draft.name || "Preview"}
                style={{ width: "100%", height: 180, objectFit: "cover", borderRadius: 10, marginBottom: 12 }}
              />
            ) : null}
            <h3>{editor.draft.name || "Ikke navngitt aktør"}</h3>
            <dl>
              <div>
                <dt>Org.nr</dt>
                <dd>{editor.draft.org_number || "Ikke satt"}</dd>
              </div>
              <div>
                <dt>Kommune(r)</dt>
                <dd>{editor.draft.municipalities || "Ikke satt"}</dd>
              </div>
              <div>
                <dt>Beskrivelse (public)</dt>
                <dd>{editor.draft.description || "Ikke satt"}</dd>
              </div>
              <div>
                <dt>E-post</dt>
                <dd>{editor.draft.email || "Ikke satt"}</dd>
              </div>
              <div>
                <dt>Telefon (public)</dt>
                <dd>{editor.draft.publish_phone ? editor.draft.phone || "Ikke satt" : "Skjult"}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>{editor.draft.is_published ? "Publisert" : "Ikke publisert"}</dd>
              </div>
              <div>
                <dt>Primærlenke</dt>
                <dd>{primaryLink(editor.draft) || "Ikke satt"}</dd>
              </div>
              <div>
                <dt>Kildetype</dt>
                <dd>{linkFieldLabel(editor.selectedOrganization?.primary_link_field) || "Ikke valgt"}</dd>
              </div>
              <div>
                <dt>OG-tittel</dt>
                <dd>{editor.selectedOrganization?.og_title || "Ikke hentet"}</dd>
              </div>
              <div>
                <dt>OG-beskrivelse</dt>
                <dd>{editor.selectedOrganization?.og_description || "Ikke hentet"}</dd>
              </div>
              <div>
                <dt>Automatisk thumbnail</dt>
                <dd>{editor.selectedOrganization?.auto_thumbnail_url || "Ikke valgt"}</dd>
              </div>
              <div>
                <dt>Sist hentet</dt>
                <dd>{editor.selectedOrganization?.og_last_fetched_at ? formatDateTime(editor.selectedOrganization.og_last_fetched_at) : "Aldri"}</dd>
              </div>
              <div>
                <dt>Tags</dt>
                <dd>{selectedNames(editor.tags, editor.draft.tag_ids) || "Ingen valgt"}</dd>
              </div>
              <div>
                <dt>Kategori</dt>
                <dd>{selectedNames(editor.categories, editor.draft.category_ids) || "Ingen valgt"}</dd>
              </div>
              <div>
                <dt>Underkategori</dt>
                <dd>{selectedSubcategoryNames(editor.subcategories, editor.draft.subcategory_ids) || "Ingen valgt"}</dd>
              </div>
            </dl>
            {editor.selectedOrganization?.active_people?.length ? (
              <div className="people-preview">
                <h4>Aktive personer (fra API)</h4>
                <ul>
                  {editor.selectedOrganization.active_people.map((link) => (
                    <li key={link.id}>
                      <span>{link.person?.full_name ?? "Ukjent person"}</span>
                      <small>
                        {link.publish_person ? "Publiseres" : "Skjult"} · {link.status}
                      </small>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="muted">Ingen aktive personer tilgjengelig i valgt organisasjon.</p>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("nb-NO", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("nb-NO", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function primaryLink(draft: {
  website_url: string | null;
  instagram_url: string | null;
  tiktok_url: string | null;
  linkedin_url: string | null;
  facebook_url: string | null;
  youtube_url: string | null;
}): string | null {
  return (
    draft.website_url ||
    draft.instagram_url ||
    draft.tiktok_url ||
    draft.linkedin_url ||
    draft.facebook_url ||
    draft.youtube_url ||
    null
  );
}

function linkFieldLabel(field: string | null | undefined): string | null {
  switch (field) {
    case "website_url":
      return "Website";
    case "instagram_url":
      return "Instagram";
    case "tiktok_url":
      return "TikTok";
    case "linkedin_url":
      return "LinkedIn";
    case "facebook_url":
      return "Facebook";
    case "youtube_url":
      return "YouTube";
    default:
      return null;
  }
}

function CategorySelectFields(props: {
  title: string;
  description: string;
  categories: Array<{ id: number; name: string; slug: string }>;
  subcategories: Array<{ id: number; name: string; slug: string; category: { id: number; name: string; slug: string } }>;
  selectedCategoryIds: number[];
  selectedIds: number[];
  onSelect: (categoryId: number | null, subcategoryId: number | null) => void;
}) {
  const { title, description, categories, subcategories, selectedCategoryIds, selectedIds, onSelect } = props;
  const selectedSubcategoryId = selectedIds[0] ?? null;
  const selectedSubcategory =
    selectedSubcategoryId !== null ? subcategories.find((item) => item.id === selectedSubcategoryId) ?? null : null;
  const selectedCategoryId = selectedCategoryIds[0] ?? selectedSubcategory?.category.id ?? null;
  const selectedCategory = selectedCategoryId !== null ? categories.find((item) => item.id === selectedCategoryId) ?? null : null;

  const sortedCategories = sortCategoriesByTaxonomy(categories);

  const availableSubcategories =
    selectedCategory === null ? [] : filterSubcategoriesForCategory(subcategories, selectedCategory.slug);

  return (
    <div className="link-section">
      <div className="sidebar-header">
        <h2>{title}</h2>
        <span className="meta">{selectedSubcategory ? selectedSubcategory.name : "Ingen valgt"}</span>
      </div>
      <p className="muted">{description}</p>
      <div className="grid two">
        <Field label="Hovedkategori">
          <select
            value={selectedCategoryId ?? ""}
            onChange={(e) => {
              const nextCategoryId = e.target.value ? Number(e.target.value) : null;
              onSelect(nextCategoryId, null);
            }}
          >
            <option value="">Velg hovedkategori</option>
            {sortedCategories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Underkategori">
          <select
            value={selectedSubcategoryId ?? ""}
            onChange={(e) => onSelect(selectedCategoryId, e.target.value ? Number(e.target.value) : null)}
            disabled={selectedCategoryId === null}
          >
            <option value="">
              {selectedCategoryId === null
                ? "Velg hovedkategori først"
                : availableSubcategories.length === 0
                  ? "Ingen underkategorier"
                  : "Ingen underkategori"}
            </option>
            {availableSubcategories.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </Field>
      </div>
    </div>
  );
}


function selectedNames(options: Array<{ id: number; name: string }>, ids: number[]): string {
  return options
    .filter((item) => ids.includes(item.id))
    .map((item) => item.name)
    .join(", ");
}

function selectedSubcategoryNames(options: Array<{ id: number; name: string; category: { name: string } }>, ids: number[]): string {
  return options
    .filter((item) => ids.includes(item.id))
    .map((item) => `${item.category.name}: ${item.name}`)
    .join(", ");
}

function getOrganizationLinkRows(organization: {
  website_url: string | null;
  instagram_url: string | null;
  tiktok_url: string | null;
  linkedin_url: string | null;
  facebook_url: string | null;
  youtube_url: string | null;
}) {
  return [
    { label: "Nettside", href: organization.website_url },
    { label: "Instagram", href: organization.instagram_url },
    { label: "TikTok", href: organization.tiktok_url },
    { label: "LinkedIn", href: organization.linkedin_url },
    { label: "Facebook", href: organization.facebook_url },
    { label: "YouTube", href: organization.youtube_url },
  ].filter((link): link is { label: string; href: string } => Boolean(link.href));
}

function getOverviewPills(organization: {
  categories: Array<{ id: number; name: string }>;
  subcategories: Array<{ id: number; name: string }>;
  tags: Array<{ id: number; name: string }>;
}) {
  const pills = [
    ...organization.categories.map((category) => ({
      key: `category-${category.id}`,
      label: category.name.toUpperCase(),
      kind: "category" as const,
    })),
    ...organization.subcategories.map((subcategory) => ({
      key: `subcategory-${subcategory.id}`,
      label: subcategory.name,
      kind: "subcategory" as const,
    })),
    ...organization.tags.map((tag) => ({
      key: `tag-${tag.id}`,
      label: tag.name,
      kind: "tag" as const,
    })),
  ];
  if (pills.length <= 5) return pills;
  return [...pills.slice(0, 4), { key: "more", label: `+${pills.length - 4}`, kind: "tag" as const }];
}

function getEditorVisibleContacts(
  link: NonNullable<ReturnType<typeof useEditor>["organizations"][number]["active_people"]>[number],
  personsById: ReturnType<typeof useEditor>["personsById"],
  contactsByPersonId: Map<number, PersonContact[]>,
) {
  const personId = link.person?.id;
  if (!personId) return [];
  const person = personsById.get(personId);
  const personContacts = contactsByPersonId.get(personId) ?? [];
  const explicitContacts = personContacts
    .filter((contact) => contact.value)
    .sort((left, right) => Number(Boolean(right.is_primary)) - Number(Boolean(left.is_primary)));
  if (explicitContacts.length > 0) return explicitContacts;

  const fallbackContacts = [
    ...(person?.email
      ? [{ type: "EMAIL" as const, value: person.email, phone_dial_uri: null, phone_country_calling_code_hint: null, is_primary: true }]
      : []),
    ...(person?.phone
      ? [
          {
            type: "PHONE" as const,
            value: person.phone,
            phone_dial_uri: person.phone_dial_uri,
            phone_country_calling_code_hint: person.phone_country_calling_code_hint,
            is_primary: true,
          },
        ]
      : []),
    ...((link.person?.public_contacts ?? []).map((contact) => ({
      type: contact.type,
      value: contact.value,
      phone_dial_uri: contact.phone_dial_uri,
      phone_country_calling_code_hint: contact.phone_country_calling_code_hint,
      is_primary: contact.is_primary,
    }))),
  ];
  const unique = new Map<string, PersonContact>();
  for (const contact of fallbackContacts) {
    if (!contact.value) continue;
    unique.set(`${contact.type}-${contact.value}`, {
      id: 0,
      type: contact.type as "EMAIL" | "PHONE",
      value: contact.value,
      phone_region_used: null,
      phone_dial_uri: contact.phone_dial_uri,
      phone_country_calling_code_hint: contact.phone_country_calling_code_hint ?? null,
      is_primary: Boolean(contact.is_primary),
      is_public: Boolean("is_public" in contact && contact.is_public),
      created_at: "",
    });
  }
  return [...unique.values()];
}

function getPersonContacts(
  person: ReturnType<typeof useEditor>["persons"][number] | undefined,
  loadedContacts: PersonContact[],
): PersonContact[] {
  if (!person) return [];
  const unique = new Map<number, PersonContact>();
  for (const contact of person.contacts ?? []) unique.set(contact.id, contact);
  for (const contact of loadedContacts) {
    if (contact.person === person.id) unique.set(contact.id, contact);
  }
  return [...unique.values()];
}

function TagSuggestions(props: {
  value: string;
  tags: Array<{ id: number; name: string }>;
  onSelect: (nextValue: string) => void;
}) {
  const { value, tags, onSelect } = props;
  const suggestions = getTagSuggestions(value, tags);
  if (suggestions.length === 0) return null;

  return (
    <div className="tag-suggestions" role="listbox" aria-label="Eksisterende tags">
      {suggestions.map((tag) => (
        <button
          key={tag.id}
          type="button"
          className="mini-pill tag suggestion-chip"
          onClick={() => onSelect(applyTagSuggestion(value, tag.name))}
        >
          {tag.name}
        </button>
      ))}
    </div>
  );
}

function getTagSuggestions(value: string, tags: Array<{ id: number; name: string }>) {
  const parsed = value.split(",");
  const activeTerm = (parsed[parsed.length - 1] ?? "").trim().toLocaleLowerCase("nb");
  const chosen = new Set(
    parsed
      .slice(0, -1)
      .map((item) => item.trim().toLocaleLowerCase("nb"))
      .filter(Boolean),
  );
  if (!activeTerm) return [];
  return tags
    .filter((tag) => !chosen.has(tag.name.toLocaleLowerCase("nb")))
    .filter((tag) => tag.name.toLocaleLowerCase("nb").includes(activeTerm))
    .slice(0, 6);
}

function applyTagSuggestion(currentValue: string, tagName: string) {
  const parts = currentValue
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  if (parts.length === 0) return tagName;
  parts[parts.length - 1] = tagName;
  return parts.join(", ");
}

function matchesOrganizationFilters(input: {
  organization: {
    name: string;
    org_number: string | null;
    email: string | null;
    phone: string | null;
    municipalities: string;
    note: string | null;
    description: string | null;
    tags: Array<{ slug: string; name: string }>;
    categories: Array<{ slug: string; name: string }>;
    subcategories: Array<{ slug: string; name: string }>;
  };
  query: string;
  categorySlug: string;
  subcategorySlug: string;
  tagSlug: string;
  personNames: string[];
}) {
  const { organization, query, categorySlug, subcategorySlug, tagSlug, personNames } = input;
  const normalizedQuery = query.trim().toLowerCase();
  if (categorySlug && !organization.categories.some((category) => category.slug === categorySlug)) {
    return false;
  }
  if (subcategorySlug && !organization.subcategories.some((subcategory) => subcategory.slug === subcategorySlug)) {
    return false;
  }
  if (tagSlug && !organization.tags.some((tag) => tag.slug === tagSlug)) {
    return false;
  }
  if (!normalizedQuery) return true;

  const haystack = [
    organization.name,
    organization.org_number ?? "",
    organization.email ?? "",
    organization.phone ?? "",
    organization.municipalities ?? "",
    organization.note ?? "",
    organization.description ?? "",
    ...organization.tags.map((tag) => tag.name),
    ...organization.categories.map((category) => category.name),
    ...organization.subcategories.map((subcategory) => subcategory.name),
    ...personNames,
  ]
    .join(" ")
    .toLowerCase();

  return haystack.includes(normalizedQuery);
}

function describeEditorFilterState(input: {
  query: string;
  categorySlug: string;
  subcategorySlug: string;
  tagSlug: string;
  entityLabel: string;
}) {
  const { query, categorySlug, subcategorySlug, tagSlug, entityLabel } = input;
  const parts: string[] = [];
  if (query.trim()) parts.push(`søk "${query.trim()}"`);
  if (categorySlug) parts.push(`hovedkategori ${humanizeSlug(categorySlug)}`);
  if (subcategorySlug) parts.push(`underkategori ${humanizeSlug(subcategorySlug)}`);
  if (tagSlug) parts.push(`tag ${humanizeSlug(tagSlug)}`);
  if (parts.length === 0) return null;
  return `Viser ${entityLabel} filtrert på ${parts.join(", ")}.`;
}

function humanizeSlug(value: string) {
  return value.replace(/-/g, " ");
}
