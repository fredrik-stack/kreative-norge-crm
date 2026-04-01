const CATEGORY_SLUG_ORDER: readonly string[] = [
  "musikk",
  "film",
  "kunst-design",
  "scenekunst",
  "kreativ-teknologi",
  "litteratur",
] as const;

const SUBCATEGORY_SLUG_ORDER: readonly string[] = [
  "artister-band",
  "konsertarrangorer",
  "musikere",
  "musikkbransjen",
  "produsent",
  "regi-manus",
  "foto-lys",
  "filmlyd",
  "filmproduksjon",
  "visuell-kunst",
  "grafisk-design",
  "klesdesign",
  "teater",
  "dans",
] as const;

const CATEGORY_NAME_TO_SLUG: Record<string, string> = {
  Musikk: "musikk",
  Film: "film",
  "Kunst & Design": "kunst-design",
  Scenekunst: "scenekunst",
  "Kreativ teknologi": "kreativ-teknologi",
  Litteratur: "litteratur",
} as const;

const ALLOWED_SUBCATEGORY_NAMES_BY_CATEGORY: Record<string, string[]> = {
  musikk: ["Artister & Band", "Konsertarrangører", "Musikere", "Musikkbransjen"],
  film: ["Produsent", "Regi & Manus", "Foto/ Lys", "Filmlyd", "Filmproduksjon"],
  "kunst-design": ["Visuell kunst", "Grafisk design", "Klesdesign"],
  scenekunst: ["Teater", "Dans"],
  "kreativ-teknologi": [],
  litteratur: [],
} as const;

export function sortedCategories<T extends { slug: string; name: string }>(categories: T[]) {
  return [...categories]
    .filter((category) => category.slug in invertCategoryMap())
    .sort((left, right) => compareBySlugOrder(left.slug, right.slug, CATEGORY_SLUG_ORDER, left.name, right.name));
}

export function sortedSubcategories<T extends { slug: string; name: string }>(subcategories: T[]) {
  return [...subcategories]
    .filter((subcategory) => isAllowedSubcategory(subcategory.name))
    .sort((left, right) => compareSubcategories(left.slug, right.slug, left.name, right.name));
}

export function sortedTags<T extends { name: string }>(tags: T[]) {
  return [...tags].sort((left, right) => left.name.localeCompare(right.name, "nb"));
}

export function filterSubcategoriesForCategory<T extends { slug: string; name: string; category: { slug: string; name: string } }>(
  subcategories: T[],
  categorySlug: string,
) {
  const allowedNames = new Set(ALLOWED_SUBCATEGORY_NAMES_BY_CATEGORY[categorySlug as keyof typeof ALLOWED_SUBCATEGORY_NAMES_BY_CATEGORY] ?? []);
  if (!categorySlug) return sortedSubcategories(subcategories);
  return sortedSubcategories(
    subcategories.filter(
      (subcategory) =>
        subcategory.category.slug === categorySlug &&
        allowedNames.has(normalizeSubcategoryName(subcategory.name)),
    ),
  );
}

export function getAllowedCategorySlugByName(name: string) {
  return CATEGORY_NAME_TO_SLUG[name as keyof typeof CATEGORY_NAME_TO_SLUG] ?? null;
}

function invertCategoryMap() {
  return Object.fromEntries(Object.entries(CATEGORY_NAME_TO_SLUG).map(([name, slug]) => [slug, name]));
}

function isAllowedSubcategory(name: string) {
  const normalized = normalizeSubcategoryName(name);
  return Object.values(ALLOWED_SUBCATEGORY_NAMES_BY_CATEGORY).some((items) => items.includes(normalized));
}

function normalizeSubcategoryName(name: string) {
  if (name === "Artister & band") return "Artister & Band";
  return name;
}

function compareSubcategories(leftSlug: string, rightSlug: string, leftName: string, rightName: string) {
  const leftIndex = SUBCATEGORY_SLUG_ORDER.indexOf(leftSlug);
  const rightIndex = SUBCATEGORY_SLUG_ORDER.indexOf(rightSlug);
  if (leftIndex === -1 && rightIndex === -1) {
    return normalizeSubcategoryName(leftName).localeCompare(normalizeSubcategoryName(rightName), "nb");
  }
  if (leftIndex === -1) return 1;
  if (rightIndex === -1) return -1;
  return leftIndex - rightIndex;
}

function compareBySlugOrder(
  leftSlug: string,
  rightSlug: string,
  order: readonly string[],
  leftName: string,
  rightName: string,
) {
  const leftIndex = order.indexOf(leftSlug);
  const rightIndex = order.indexOf(rightSlug);
  if (leftIndex === -1 && rightIndex === -1) return leftName.localeCompare(rightName, "nb");
  if (leftIndex === -1) return 1;
  if (rightIndex === -1) return -1;
  return leftIndex - rightIndex;
}
