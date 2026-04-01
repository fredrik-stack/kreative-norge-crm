import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useEditor } from "../context/EditorContext";

type OverviewCard =
  | {
      kind: "organization";
      id: number;
      name: string;
      municipality: string;
      description: string;
      imageUrl: string | null;
      isPublished: boolean;
      categories: string[];
      subcategories: string[];
      tags: string[];
      editPath: string;
    }
  | {
      kind: "person";
      id: number;
      name: string;
      municipality: string;
      description: string;
      imageUrl: null;
      isPublished: false;
      categories: string[];
      subcategories: string[];
      tags: string[];
      editPath: string;
    };

export function EditorOverviewPage() {
  const editor = useEditor();
  const navigate = useNavigate();
  const [expandedKey, setExpandedKey] = useState<string | null>(null);

  const cards = useMemo<OverviewCard[]>(() => {
    const organizationCards: OverviewCard[] = editor.filteredOverviewOrganizations.map((organization) => ({
      kind: "organization",
      id: organization.id,
      name: organization.name,
      municipality: organization.municipalities || "Ingen kommune",
      description: organization.description || organization.note || "Ingen beskrivelse lagt inn ennå.",
      imageUrl: organization.preview_image_url,
      isPublished: organization.is_published,
      categories: organization.categories.map((category) => category.name),
      subcategories: organization.subcategories.map((subcategory) => subcategory.name),
      tags: organization.tags.map((tag) => tag.name),
      editPath: `/organizations/${organization.id}`,
    }));

    const personCards: OverviewCard[] = editor.filteredOverviewPersons.map((person) => ({
      kind: "person",
      id: person.id,
      name: person.full_name,
      municipality: person.municipality || "Ingen kommune",
      description: person.note || person.email || person.phone || "Ingen beskrivelse lagt inn ennå.",
      imageUrl: null,
      isPublished: false,
      categories: person.categories.map((category) => category.name),
      subcategories: person.subcategories.map((subcategory) => subcategory.name),
      tags: person.tags.map((tag) => tag.name),
      editPath: `/people/${person.id}`,
    }));

    return [...organizationCards, ...personCards].sort((left, right) => left.name.localeCompare(right.name, "nb"));
  }, [editor.filteredOverviewOrganizations, editor.filteredOverviewPersons]);

  return (
    <main className="editor-overview-layout">
      <section className="panel overview-panel unified">
        <div className="sidebar-header">
          <div>
            <p className="eyebrow small">Oversikt</p>
            <h2>Aktører og personer</h2>
          </div>
          <span className="meta">{cards.length} kort</span>
        </div>
        <p className="muted">
          Klikk på et kort for å se mer informasjon. Bruk <strong>Rediger</strong> når du vil åpne skjemaet.
        </p>
        {editor.overviewFilterSummary ? <div className="filter-summary">{editor.overviewFilterSummary}</div> : null}

        <div className="editor-card-grid">
          {cards.map((card) => {
            const expanded = expandedKey === `${card.kind}-${card.id}`;
            return (
              <article
                key={`${card.kind}-${card.id}`}
                className={`editor-card public-like ${expanded ? "expanded" : ""}`}
                onClick={() => setExpandedKey(expanded ? null : `${card.kind}-${card.id}`)}
              >
                {card.imageUrl ? (
                  <img src={card.imageUrl} alt={card.name} className="editor-card-thumb" />
                ) : (
                  <div className={`editor-card-thumb editor-card-thumb-fallback ${card.kind === "person" ? "person" : ""}`}>
                    <span>{card.name.slice(0, 2).toUpperCase()}</span>
                  </div>
                )}
                <div className="editor-card-body">
                  <div className="editor-card-head">
                    <div>
                      <p className="eyebrow small">{card.kind === "organization" ? "Aktør" : "Person"}</p>
                      <h3>{card.name}</h3>
                    </div>
                    <span className="meta">{card.municipality}</span>
                  </div>
                  <div className="meta-row">
                    {card.categories.map((category) => (
                      <span key={`category-${card.kind}-${card.id}-${category}`} className="mini-pill category">
                        {category.toUpperCase()}
                      </span>
                    ))}
                    {card.subcategories.map((subcategory) => (
                      <span key={`subcategory-${card.kind}-${card.id}-${subcategory}`} className="mini-pill subcategory">
                        {subcategory}
                      </span>
                    ))}
                    {card.tags.map((tag) => (
                      <span key={`tag-${card.kind}-${card.id}-${tag}`} className="mini-pill tag">
                        {tag}
                      </span>
                    ))}
                  </div>
                  {expanded ? (
                    <>
                      <p className="muted editor-card-copy">{card.description}</p>
                      <div className="editor-card-actions">
                        <span className={`save-pill ${card.isPublished ? "saved" : "idle"}`}>
                          {card.kind === "organization"
                            ? card.isPublished
                              ? "Publisert"
                              : "Kun intern"
                            : "Intern profil"}
                        </span>
                        <button
                          type="button"
                          className="ghost-button"
                          onClick={(event) => {
                            event.stopPropagation();
                            if (card.kind === "organization") {
                              editor.setSelectedOrgId(card.id);
                            } else {
                              editor.setSelectedPersonId(card.id);
                            }
                            navigate(card.editPath);
                          }}
                        >
                          Rediger
                        </button>
                      </div>
                    </>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
        {cards.length === 0 ? <div className="empty-state">Ingen kort matcher filtreringen.</div> : null}
      </section>
    </main>
  );
}
