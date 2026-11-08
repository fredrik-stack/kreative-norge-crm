"""Opt-in legacy tenant authority; never a grant for shared access.

The HTTP boundary holds authorization rows until the tenant operation finishes.
Actor-less legacy services/operators are deliberately unavailable outside it.
"""
from contextvars import ContextVar

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction, OperationalError
from django.http import HttpResponseForbidden
from django.urls import resolve, Resolver404
from rest_framework.exceptions import APIException

from .models import Tenant, TenantMembership


_NO_ACTOR = object()
_request_scope = ContextVar("strict_tenant_request", default=None)


def strict_tenant_access():
    return settings.STRICT_TENANT_ACCESS_ENABLED


def active_memberships(user):
    return TenantMembership.objects.filter(
        user_id=getattr(user, "pk", None), user__is_active=True,
        is_active=True, role__in=TenantMembership.Role.values,
    )


class TenantAccessUnavailable(APIException):
    status_code = 503
    default_detail = "Tilgangskontrollen er opptatt. Prøv på nytt."
    default_code = "tenant_access_unavailable"


def strict_role(user, tenant_id):
    if not user or not user.is_authenticated or tenant_id is None:
        return None
    scope = _request_scope.get()
    if scope is None:
        return active_memberships(user).filter(tenant_id=tenant_id).values_list("role", flat=True).first()
    key = (user.pk, int(tenant_id))
    if scope["key"] != (None, int(tenant_id)) and scope["key"] != key:
        return None
    if scope["key"] == key:
        return scope["role"]
    # Same order as access_management: domain -> user -> tenant -> membership.
    # SHARE allows concurrent requests, but fences revocation/deactivation/deletion.
    try:
        domain_id = Tenant.objects.filter(pk=tenant_id).values_list("sharing_domain_id", flat=True).first()
        with connection.cursor() as cursor:
            if domain_id is not None:
                cursor.execute("SELECT id FROM crm_sharingdomain WHERE id=%s FOR SHARE", [domain_id])
                if cursor.fetchone() is None:
                    return None
            user_table = connection.ops.quote_name(get_user_model()._meta.db_table)
            cursor.execute(f"SELECT is_active FROM {user_table} WHERE id=%s FOR SHARE", [user.pk])
            row = cursor.fetchone()
            if row is None or not row[0]:
                return None
            cursor.execute("SELECT sharing_domain_id FROM crm_tenant WHERE id=%s FOR SHARE", [tenant_id])
            row = cursor.fetchone()
            if row is None or row[0] != domain_id:
                return None
            cursor.execute(
                "SELECT role FROM crm_tenantmembership WHERE user_id=%s AND tenant_id=%s AND is_active FOR SHARE",
                [user.pk, tenant_id],
            )
            row = cursor.fetchone()
        role = row[0] if row and row[0] in TenantMembership.Role.values else None
        scope.update(key=key, role=role)
        return role
    except OperationalError as error:
        raise TenantAccessUnavailable() from error


def require_tenant_operation(tenant_id, roles, *, actor=_NO_ACTOR):
    """No implicit grant from a job creator, superuser or caller-supplied actor."""
    if not strict_tenant_access():
        return
    scope = _request_scope.get()
    if (scope is None or scope["key"][1] != tenant_id
            or scope["role"] not in roles
            or (actor is not _NO_ACTOR and scope["key"][0] != getattr(actor, "pk", None))):
        raise PermissionDenied("Streng tenanttilgang krever en autorisert tenantoperasjon.")


def block_legacy_operator():
    if strict_tenant_access():
        from django.core.management.base import CommandError
        raise CommandError("Legacy operator route is disabled in strict tenant mode; a separate scoped operator contract is required.")


class StrictTenantAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not strict_tenant_access():
            return self.get_response(request)
        try:
            match = resolve(request.path_info)
        except Resolver404:
            return self.get_response(request)
        # The current Admin has global model permissions, not tenant scoping.
        # Block the entire namespace, including auth.User/Group and admin actions.
        if "admin" in match.app_names:
            return HttpResponseForbidden("Django Admin er sperret i streng tenantmodus.")
        cls = getattr(match.func, "cls", None)
        tenant_id = match.kwargs.get("tenant_id")
        if tenant_id is None or cls is None or cls.__module__ != "crm.views":
            return self.get_response(request)
        token = _request_scope.set({"key": (None, int(tenant_id)), "role": None})
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL lock_timeout = '2s'")
                    cursor.execute("SET LOCAL statement_timeout = '30s'")
                response = self.get_response(request)
                if response.status_code >= 400:
                    transaction.set_rollback(True)
                return response
        finally:
            _request_scope.reset(token)
