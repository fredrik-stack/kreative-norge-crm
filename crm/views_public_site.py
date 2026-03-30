from django.views.generic import DetailView, ListView

from .models import Category, Organization, Subcategory, Tag


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
        context["available_tags"] = Tag.objects.filter(
            organizations__is_published=True
        ).distinct().order_by("name")
        context["available_categories"] = Category.objects.filter(
            subcategories__organizations__is_published=True
        ).distinct().order_by("name")
        context["available_subcategories"] = Subcategory.objects.filter(
            organizations__is_published=True
        ).select_related("category").distinct().order_by("category__name", "name")
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
