const CATEGORY_SLUG_ORDER = [
  "musikk",
  "film",
  "kunst-design",
  "scenekunst",
  "kreativ-teknologi",
  "litteratur",
] as const;

const SUBCATEGORY_SLUG_ORDER = [
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

export function sortedCategories<T extends { slug: string; name: string }>(categories: T[]) {
  return [...categories].sort((left, right) => compareBySlugOrder(left.slug, right.slug, CATEGORY_SLUG_ORDER, left.name, right.name));
}

export function sortedSubcategories<T extends { slug: string; name: string }>(subcategories: T[]) {
  return [...subcategories].sort((left, right) =>
    compareBySlugOrder(left.slug, right.slug, SUBCATEGORY_SLUG_ORDER, left.name, right.name),
  );
}

export function sortedTags<T extends { name: string }>(tags: T[]) {
  return [...tags].sort((left, right) => left.name.localeCompare(right.name, "nb"));
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
