from django.contrib import admin
from django.urls import path, include, re_path

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from crm.public_image_views import invalid_public_image_release, public_image_release

urlpatterns = [
    re_path(
        r"^media/releases/(?P<release_id>[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})/"
        r"(?P<variant>square|landscape|share)\.(?P<extension>webp|png|jpg)$",
        public_image_release,
        name="public-image-release",
    ),
    re_path(
        r"^media/releases/.*$",
        invalid_public_image_release,
        name="invalid-public-image-release",
    ),
    path("admin/", admin.site.urls),

    path("api/public/", include("crm.urls_public")),
    path("public/", include("crm.urls_public_site")),

    path("api/", include("crm.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
