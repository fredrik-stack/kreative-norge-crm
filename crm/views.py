from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Tenant, Organization, Person, OrganizationPerson, PersonContact
from .serializers import (
    TenantSerializer,
    OrganizationSerializer,
    PersonSerializer,
    OrganizationPersonSerializer,
    PersonContactSerializer,
    PublicOrganizationSerializer,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class SessionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if request.user.is_authenticated:
            return Response(
                {
                    "authenticated": True,
                    "user": {
                        "id": request.user.id,
                        "username": request.user.get_username(),
                    },
                }
            )
        return Response({"authenticated": False, "user": None})


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""

        if not username or not password:
            return Response(
                {"non_field_errors": ["Brukernavn og passord er påkrevd."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {"non_field_errors": ["Ugyldig brukernavn eller passord."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        login(request, user)
        return Response(
            {
                "authenticated": True,
                "user": {"id": user.id, "username": user.get_username()},
            }
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"authenticated": False, "user": None})


class TenantViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Tenant.objects.all().order_by("name")
    serializer_class = TenantSerializer


class OrganizationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        qs = (
            Organization.objects.all()
            .order_by("name")
            .prefetch_related("org_people__person__contacts")
        )

        tenant_id = self.kwargs.get("tenant_id")
        if tenant_id is not None:
            qs = qs.filter(tenant_id=tenant_id)
        return qs

    def perform_create(self, serializer):
        tenant_id = self.kwargs.get("tenant_id")
        if tenant_id is not None:
            serializer.save(tenant_id=tenant_id)
        else:
            serializer.save()


class PersonViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PersonSerializer

    def get_queryset(self):
        qs = Person.objects.all().order_by("full_name")
        tenant_id = self.kwargs.get("tenant_id")
        if tenant_id is not None:
            qs = qs.filter(tenant_id=tenant_id)
        return qs

    def perform_create(self, serializer):
        tenant_id = self.kwargs.get("tenant_id")
        if tenant_id is not None:
            serializer.save(tenant_id=tenant_id)
        else:
            serializer.save()


class OrganizationPersonViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationPersonSerializer

    def get_queryset(self):
        qs = OrganizationPerson.objects.all().order_by("-created_at")
        tenant_id = self.kwargs.get("tenant_id")
        if tenant_id is not None:
            qs = qs.filter(tenant_id=tenant_id)
        return qs

    def perform_create(self, serializer):
        tenant_id = self.kwargs.get("tenant_id")
        if tenant_id is not None:
            serializer.save(tenant_id=tenant_id)
        else:
            serializer.save()


class PersonContactViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PersonContactSerializer

    def get_queryset(self):
        qs = PersonContact.objects.all().order_by("-is_primary", "type", "value")
        tenant_id = self.kwargs.get("tenant_id")
        if tenant_id is not None:
            qs = qs.filter(tenant_id=tenant_id)

        person_id = self.request.query_params.get("person")
        if person_id:
            qs = qs.filter(person_id=person_id)
        return qs

    def perform_create(self, serializer):
        tenant_id = self.kwargs.get("tenant_id")
        if tenant_id is not None:
            serializer.save(tenant_id=tenant_id)
        else:
            serializer.save()


class PublicActorViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = PublicOrganizationSerializer

    def get_queryset(self):
        return (
            Organization.objects.filter(is_published=True)
            .order_by("name")
            .prefetch_related("org_people__person__contacts")
        )
