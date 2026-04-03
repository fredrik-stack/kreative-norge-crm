from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CsrfTokenView,
    SessionView,
    LoginView,
    LogoutView,
    TenantViewSet,
    TagViewSet,
    CategoryViewSet,
    SubcategoryViewSet,
    OrganizationViewSet,
    PersonViewSet,
    OrganizationPersonViewSet,
    PersonContactViewSet,
    PublicActorViewSet,
    ImportJobViewSet,
    ExportJobViewSet,
)

router = DefaultRouter()
router.register(r"tenants", TenantViewSet, basename="tenant")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"subcategories", SubcategoryViewSet, basename="subcategory")

tenant_router = DefaultRouter()
tenant_router.register(r"tags", TagViewSet, basename="tenant-tags")
tenant_router.register(r"organizations", OrganizationViewSet, basename="tenant-organizations")
tenant_router.register(r"persons", PersonViewSet, basename="tenant-persons")
tenant_router.register(r"organization-people", OrganizationPersonViewSet, basename="tenant-organization-people")
tenant_router.register(r"person-contacts", PersonContactViewSet, basename="tenant-person-contacts")
tenant_router.register(r"import-jobs", ImportJobViewSet, basename="tenant-import-jobs")
tenant_router.register(r"export-jobs", ExportJobViewSet, basename="tenant-export-jobs")

public_router = DefaultRouter()
public_router.register(r"actors", PublicActorViewSet, basename="public-actors")

urlpatterns = [
    path("auth/csrf/", CsrfTokenView.as_view(), name="auth-csrf"),
    path("auth/session/", SessionView.as_view(), name="auth-session"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("", include(router.urls)),
    path("tenants/<int:tenant_id>/", include(tenant_router.urls)),
    path("public/", include(public_router.urls)),
]
