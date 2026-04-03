from django.contrib.auth import authenticate, login, logout
import importlib
from django.db.models import Count
from django.db.models import Q
from django.http import FileResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Tenant,
    Tag,
    Category,
    Subcategory,
    Organization,
    Person,
    OrganizationPerson,
    PersonContact,
    ImportJob,
    ExportJob,
)
from .permissions import ImportExportAccessPermission
from .serializers import (
    TenantSerializer,
    TagSerializer,
    CategorySerializer,
    SubcategorySerializer,
    OrganizationSerializer,
    PersonSerializer,
    OrganizationPersonSerializer,
    PersonContactSerializer,
    PublicOrganizationSerializer,
    ImportJobSerializer,
    ImportJobCreateSerializer,
    ImportJobUploadSerializer,
    ImportRowSerializer,
    ExportJobSerializer,
    ImportJobDecisionsSerializer,
    ImportDecisionSerializer,
    ImportCommitRequestSerializer,
)
from .services.open_graph import refresh_organization_open_graph

import_commit_module = importlib.import_module("crm.services.import.commit")
import_preview_module = importlib.import_module("crm.services.import.preview")
import_reporting_module = importlib.import_module("crm.services.import.reporting")
ImportCommitBlocked = import_commit_module.ImportCommitBlocked
commit_import_job = import_commit_module.commit_import_job
run_import_preview = import_preview_module.run_import_preview
update_job_preview_status = import_preview_module.update_job_preview_status
save_error_report = import_reporting_module.save_error_report


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


class TagViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TagSerializer

    def get_queryset(self):
        qs = Tag.objects.all().order_by("name")
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


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer


class SubcategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SubcategorySerializer

    def get_queryset(self):
        qs = Subcategory.objects.select_related("category").all().order_by("category__name", "name")
        category_id = self.request.query_params.get("category")
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs


class OrganizationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        qs = (
            Organization.objects.all()
            .order_by("name")
            .prefetch_related("org_people__person__contacts", "tags", "subcategories__category")
        )

        tenant_id = self.kwargs.get("tenant_id")
        if tenant_id is not None:
            qs = qs.filter(tenant_id=tenant_id)
        return qs

    def perform_create(self, serializer):
        tenant_id = self.kwargs.get("tenant_id")
        if tenant_id is not None:
            organization = serializer.save(tenant_id=tenant_id)
        else:
            organization = serializer.save()
        refresh_organization_open_graph(organization, force=True)

    def perform_update(self, serializer):
        organization = serializer.save()
        refresh_organization_open_graph(organization, force=True)

    @action(detail=True, methods=["post"], url_path="refresh-preview")
    def refresh_preview(self, request, tenant_id=None, pk=None):
        organization = self.get_object()
        refresh_organization_open_graph(organization, force=True)
        organization.refresh_from_db()
        serializer = self.get_serializer(organization)
        return Response(serializer.data)


class PersonViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PersonSerializer

    def get_queryset(self):
        qs = Person.objects.all().order_by("full_name").prefetch_related("tags", "subcategories__category")
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
            .prefetch_related("org_people__person__contacts", "tags", "subcategories__category")
        )


class ImportRowPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class TenantScopedImportExportViewSet(viewsets.GenericViewSet):
    permission_classes = [ImportExportAccessPermission]

    def get_tenant(self):
        return get_object_or_404(Tenant, pk=self.kwargs["tenant_id"])


class ImportJobViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    TenantScopedImportExportViewSet,
):
    pagination_class = None

    def get_queryset(self):
        return (
            ImportJob.objects.filter(tenant_id=self.kwargs["tenant_id"])
            .select_related("tenant", "created_by")
            .annotate(rows_count=Count("rows"))
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return ImportJobCreateSerializer
        if self.action == "upload":
            return ImportJobUploadSerializer
        if self.action == "rows":
            return ImportRowSerializer
        return ImportJobSerializer

    def perform_create(self, serializer):
        serializer.save(tenant=self.get_tenant(), created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="upload")
    def upload(self, request, tenant_id=None, pk=None):
        job = self.get_object()
        serializer = self.get_serializer(job, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        job.file = uploaded_file
        job.filename = uploaded_file.name
        job.status = ImportJob.Status.UPLOADED
        job.save(update_fields=["file", "filename", "status", "updated_at"])

        response_serializer = ImportJobSerializer(job, context=self.get_serializer_context())
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="rows")
    def rows(self, request, tenant_id=None, pk=None):
        job = self.get_object()
        queryset = job.rows.all().prefetch_related("decisions")
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(row_status=status_filter)
        action_filter = request.query_params.get("action")
        if action_filter:
            queryset = queryset.filter(proposed_action=action_filter)
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(raw_payload_json__icontains=search)
                | Q(normalized_payload_json__icontains=search)
                | Q(validation_errors_json__icontains=search)
                | Q(warnings_json__icontains=search)
            )
        paginator = ImportRowPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ImportRowSerializer(page if page is not None else queryset, many=True)
        if page is not None:
            return paginator.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="preview")
    def preview(self, request, tenant_id=None, pk=None):
        job = self.get_object()
        try:
            run_import_preview(job)
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})
        serializer = ImportJobSerializer(job, context=self.get_serializer_context())
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="decisions")
    def decisions(self, request, tenant_id=None, pk=None):
        job = self.get_object()
        payload = request.data if isinstance(request.data, list) else request.data.get("rows", [])
        serializer = ImportJobDecisionsSerializer(data=payload, many=True)
        serializer.is_valid(raise_exception=True)

        rows_by_id = {row.id: row for row in job.rows.all()}
        results = []
        for row_payload in serializer.validated_data:
            row = rows_by_id.get(row_payload["row_id"])
            if row is None:
                raise ValidationError({"row_id": f"Row {row_payload['row_id']} does not belong to this import job."})
            row.decisions.all().delete()
            created = []
            skip_row = False
            for decision_payload in row_payload["decisions"]:
                decision = row.decisions.create(
                    decided_by=request.user,
                    decision_type=decision_payload["decision_type"],
                    payload_json=decision_payload.get("payload_json") or {},
                )
                created.append(decision)
                if decision.decision_type == decision.DecisionType.SKIP_ROW:
                    skip_row = True
            row.decision_json = {"decisions": [decision.payload_json | {"decision_type": decision.decision_type} for decision in created]}
            if skip_row:
                row.row_status = row.RowStatus.SKIPPED
                row.proposed_action = row.ProposedAction.SKIP
            else:
                row.row_status = row.RowStatus.VALID
            row.save(update_fields=["decision_json", "row_status", "proposed_action", "updated_at"])
            results.append({"row_id": row.id, "decisions": ImportDecisionSerializer(created, many=True).data})

        update_job_preview_status(job)
        return Response({"results": results}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="commit")
    def commit(self, request, tenant_id=None, pk=None):
        job = self.get_object()
        serializer = ImportCommitRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            commit_import_job(job, skip_unresolved=serializer.validated_data["skip_unresolved"])
        except ImportCommitBlocked as exc:
            raise ValidationError({"detail": str(exc)})
        response_serializer = ImportJobSerializer(job, context=self.get_serializer_context())
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="error-report")
    def error_report(self, request, tenant_id=None, pk=None):
        job = self.get_object()
        save_error_report(job)
        file_handle = job.error_report_file.open("rb")
        return FileResponse(file_handle, as_attachment=True, filename=job.error_report_file.name.rsplit("/", 1)[-1])


class ExportJobViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    TenantScopedImportExportViewSet,
):
    pagination_class = None
    serializer_class = ExportJobSerializer

    def get_queryset(self):
        return (
            ExportJob.objects.filter(tenant_id=self.kwargs["tenant_id"])
            .select_related("tenant", "created_by")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(tenant=self.get_tenant(), created_by=self.request.user)
