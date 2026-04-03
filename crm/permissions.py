from rest_framework.permissions import BasePermission


class ImportExportAccessPermission(BasePermission):
    message = "Du har ikke tilgang til import og eksport."

    allowed_group_names = {"superadmin", "gruppeadmin", "redigerer"}

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        group_names = {name.lower() for name in user.groups.values_list("name", flat=True)}
        return bool(group_names & self.allowed_group_names)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
