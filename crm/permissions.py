from __future__ import annotations

from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import TenantMembership


READ_ROLES = {
    TenantMembership.Role.SUPERADMIN,
    TenantMembership.Role.GRUPPEADMIN,
    TenantMembership.Role.REDIGERER,
    TenantMembership.Role.LESER,
}
WRITE_ROLES = {
    TenantMembership.Role.SUPERADMIN,
    TenantMembership.Role.GRUPPEADMIN,
    TenantMembership.Role.REDIGERER,
}
DELETE_ROLES = {
    TenantMembership.Role.SUPERADMIN,
    TenantMembership.Role.GRUPPEADMIN,
}
IMPORT_EXPORT_ROLES = {
    TenantMembership.Role.SUPERADMIN,
    TenantMembership.Role.GRUPPEADMIN,
    TenantMembership.Role.REDIGERER,
}


def get_user_global_role(user) -> str | None:
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return TenantMembership.Role.SUPERADMIN
    group_names = {name.lower() for name in user.groups.values_list("name", flat=True)}
    for role in (
        TenantMembership.Role.GRUPPEADMIN,
        TenantMembership.Role.REDIGERER,
        TenantMembership.Role.LESER,
    ):
        if role in group_names:
            return role
    return None


def get_user_tenant_role(user, tenant_id: int | None) -> str | None:
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return TenantMembership.Role.SUPERADMIN
    if tenant_id is None:
        return None
    membership_role = (
        TenantMembership.objects.filter(user=user, tenant_id=tenant_id)
        .values_list("role", flat=True)
        .first()
    )
    return membership_role or get_user_global_role(user)


def user_can_access_tenant(user, tenant_id: int | None) -> bool:
    return get_user_tenant_role(user, tenant_id) in READ_ROLES


class TenantScopedPermission(BasePermission):
    message = "Du har ikke tilgang til denne tenant-en."

    def get_tenant_id(self, request, view, obj=None) -> int | None:
        if obj is not None:
            if hasattr(obj, "tenant_id"):
                return obj.tenant_id
            if hasattr(obj, "import_job") and hasattr(obj.import_job, "tenant_id"):
                return obj.import_job.tenant_id
        tenant_id = view.kwargs.get("tenant_id")
        return int(tenant_id) if tenant_id is not None else None

    def required_roles(self, request, view) -> set[str]:
        if request.method in SAFE_METHODS:
            return READ_ROLES
        if request.method == "DELETE":
            return DELETE_ROLES
        return WRITE_ROLES

    def has_permission(self, request, view):
        tenant_id = self.get_tenant_id(request, view)
        role = get_user_tenant_role(request.user, tenant_id)
        if role is None:
            return False
        return role in self.required_roles(request, view)

    def has_object_permission(self, request, view, obj):
        tenant_id = self.get_tenant_id(request, view, obj=obj)
        role = get_user_tenant_role(request.user, tenant_id)
        if role is None:
            return False
        return role in self.required_roles(request, view)


class TenantAccessPermission(BasePermission):
    message = "Du har ikke tilgang til denne tenant-en."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        return user_can_access_tenant(request.user, obj.id)


class ImportExportAccessPermission(TenantScopedPermission):
    message = "Du har ikke tilgang til import og eksport."

    def required_roles(self, request, view) -> set[str]:
        return IMPORT_EXPORT_ROLES
