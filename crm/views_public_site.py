import random

from django.views.generic import DetailView, ListView

from .models import Category, Organization, Subcategory, Tag


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
    "Produksjon",
    "Arenaer",
    "Visuell kunst",
    "Grafisk design",
    "Klesdesign",
    "Teater",
    "Dans",
]


class PublicActorListView(ListView):
    template_name = "crm/public_actor_list.html"
    context_object_name = "actors"

    def get_queryset(self):
        qs = (
            Organization.objects.filter(is_published=True)
            .prefetch_related("tags", "subcategories__category", "org_people__person__contacts")
            .order_by("name")
        )

        query = (self.request.GET.get("q") or "").strip()
        tag_slug = (self.request.GET.get("tag") or "").strip()
        category_slug = (self.request.GET.get("category") or "").strip()
        subcategory_slug = (self.request.GET.get("subcategory") or "").strip()

        if query:
            qs = qs.filter(name__icontains=query)
        if tag_slug:
            qs = qs.filter(tags__slug=tag_slug)
        if category_slug:
            qs = qs.filter(subcategories__category__slug=category_slug)
        if subcategory_slug:
            qs = qs.filter(subcategories__slug=subcategory_slug)

        return qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = (self.request.GET.get("q") or "").strip()
        context["selected_tag"] = (self.request.GET.get("tag") or "").strip()
        context["selected_category"] = (self.request.GET.get("category") or "").strip()
        context["selected_subcategory"] = (self.request.GET.get("subcategory") or "").strip()
        categories = list(Category.objects.all())
        subcategories = list(Subcategory.objects.select_related("category"))
        tags = list(Tag.objects.order_by("name"))

        category_positions = {name: index for index, name in enumerate(CATEGORY_ORDER)}
        subcategory_positions = {name: index for index, name in enumerate(SUBCATEGORY_ORDER)}

        categories.sort(
            key=lambda category: (
                category_positions.get(category.name, len(CATEGORY_ORDER)),
                category.name.lower(),
            )
        )
        subcategories = [
            subcategory
            for subcategory in subcategories
            if subcategory.name in subcategory_positions
        ]
        subcategories.sort(
            key=lambda subcategory: (
                subcategory_positions.get(subcategory.name, len(SUBCATEGORY_ORDER)),
                subcategory.name.lower(),
            )
        )
        random.shuffle(tags)

        context["available_tags"] = tags
        context["available_categories"] = categories
        context["available_subcategories"] = subcategories
        return context


class PublicActorDetailView(DetailView):
    template_name = "crm/public_actor_detail.html"
    context_object_name = "actor"
    slug_field = "org_number"
    slug_url_kwarg = "org_number"

    def get_queryset(self):
        return (
            Organization.objects.filter(is_published=True)
            .prefetch_related("tags", "subcategories__category", "org_people__person__contacts")
            .order_by("name")
        )
