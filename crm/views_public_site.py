import random

from django.db.models import Q
from django.utils.text import slugify
from django.views.generic import DetailView, ListView

from .models import Organization, Tag


CATEGORY_ORDER = [
    "Musikk",
    "Film",
    "Kunst & Design",
    "Scenekunst",
    "Kreativ teknologi",
    "Litteratur",
]

SUBCATEGORY_ORDER = [
    "Artister & Band",
    "Konsertarrangører",
    "Musikere",
    "Musikkbransjen",
    "Produsent",
    "Regi & Manus",
    "Foto/ Lys",
    "Filmlyd",
    "Filmproduksjon",
    "Visuell kunst",
    "Grafisk design",
    "Klesdesign",
    "Teater",
    "Dans",
]

CATEGORY_OPTIONS = [{"name": name, "slug": slugify(name)} for name in CATEGORY_ORDER]
SUBCATEGORY_OPTIONS = [{"name": name, "slug": slugify(name)} for name in SUBCATEGORY_ORDER]


class PublicActorListView(ListView):
    template_name = "crm/public_actor_list.html"
    context_object_name = "actors"

    def get_queryset(self):
        qs = (
            Organization.objects.filter(is_published=True)
            .prefetch_related("tags", "categories", "subcategories__category", "org_people__person__contacts")
            .order_by("name")
        )

        query = (self.request.GET.get("q") or "").strip()
        tag_slug = (self.request.GET.get("tag") or "").strip()
        category_slug = (self.request.GET.get("category") or "").strip()
        subcategory_slug = (self.request.GET.get("subcategory") or "").strip()

        if query:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(org_number__icontains=query)
                | Q(municipalities__icontains=query)
                | Q(categories__name__icontains=query)
                | Q(subcategories__name__icontains=query)
                | Q(tags__name__icontains=query)
            )
        if tag_slug:
            qs = qs.filter(tags__slug=tag_slug)
        if category_slug:
            qs = qs.filter(Q(categories__slug=category_slug) | Q(subcategories__category__slug=category_slug))
        if subcategory_slug:
            qs = qs.filter(subcategories__slug=subcategory_slug)

        return qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = (self.request.GET.get("q") or "").strip()
        context["selected_tag"] = (self.request.GET.get("tag") or "").strip()
        context["selected_category"] = (self.request.GET.get("category") or "").strip()
        context["selected_subcategory"] = (self.request.GET.get("subcategory") or "").strip()
        tags = dedupe_tags(
            Tag.objects.filter(organizations__is_published=True)
            .order_by("name")
            .distinct()
        )
        random.shuffle(tags)

        context["available_tags"] = tags
        context["available_categories"] = CATEGORY_OPTIONS
        context["available_subcategories"] = SUBCATEGORY_OPTIONS
        context["active_filter_summary"] = build_filter_summary(
            query=context["query"],
            category_slug=context["selected_category"],
            subcategory_slug=context["selected_subcategory"],
            tag_slug=context["selected_tag"],
        )
        return context


class PublicActorDetailView(DetailView):
    template_name = "crm/public_actor_detail.html"
    context_object_name = "actor"
    slug_field = "org_number"
    slug_url_kwarg = "org_number"

    def get_queryset(self):
        return (
            Organization.objects.filter(is_published=True)
            .prefetch_related("tags", "categories", "subcategories__category", "org_people__person__contacts")
            .order_by("name")
        )


def dedupe_tags(tags):
    unique_tags = []
    seen_names = set()
    for tag in tags:
        key = tag.name.strip().lower()
        if key in seen_names:
            continue
        seen_names.add(key)
        unique_tags.append(tag)
    return unique_tags


def build_filter_summary(*, query: str, category_slug: str, subcategory_slug: str, tag_slug: str) -> str | None:
    parts: list[str] = []
    if query:
        parts.append(f'søk "{query}"')
    if category_slug:
        parts.append(f"hovedkategori {humanize_slug(category_slug)}")
    if subcategory_slug:
        parts.append(f"underkategori {humanize_slug(subcategory_slug)}")
    if tag_slug:
        parts.append(f"tag {humanize_slug(tag_slug)}")
    if not parts:
        return None
    return "Viser filtrerte aktører basert på " + ", ".join(parts) + "."


def humanize_slug(value: str) -> str:
    return value.replace("-", " ")
