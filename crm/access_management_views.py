"""Authenticated control-plane routes only; no CRM profiles or shared data queries."""
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from crm.services import access_management as service


class ExactFields(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError({"non_field_errors": ["INVALID_FIELDS"]})
        return super().to_internal_value(data)


class MembershipInput(ExactFields):
    username = serializers.CharField(max_length=150, trim_whitespace=False)
    role = serializers.ChoiceField(choices=service.TenantMembership.Role.values)
    is_active = serializers.BooleanField()
    expected_updated_at = serializers.CharField(allow_null=True)


class PublicationInput(ExactFields):
    approved = serializers.BooleanField()
    version = serializers.IntegerField(min_value=1)
    text = serializers.CharField(trim_whitespace=False)
    effective_at = serializers.DateTimeField()
    legal_approval_reference = serializers.CharField(max_length=200, trim_whitespace=False)


class AcceptanceInput(ExactFields):
    tenant_id = serializers.IntegerField(min_value=1)
    agreement_id = serializers.IntegerField(min_value=1)
    confirmed = serializers.BooleanField()


class ManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def handle_exception(self, exc):
        if isinstance(exc, service.ManagementError):
            code = str(exc)
            status = 409 if code in {"STALE_MEMBERSHIP", "STALE_AGREEMENT", "ALREADY_ACCEPTED", "OUTCOME_REQUIRES_READBACK"} else 403
            return Response({"code": code}, status=status)
        return super().handle_exception(exc)

    def payload(self, request, serializer):
        parsed = serializer(data=request.data)
        parsed.is_valid(raise_exception=True)
        return parsed.validated_data


class ManagementContextView(ManagementView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(service.context(actor_id=request.user.pk))


class MembershipManagementView(ManagementView):
    @extend_schema(responses=MembershipInput(many=True))
    def get(self, request, domain_id, tenant_id):
        return Response(service.list_memberships(actor_id=request.user.pk, domain_id=domain_id, tenant_id=tenant_id))

    @extend_schema(request=MembershipInput, responses=MembershipInput)
    def post(self, request, domain_id, tenant_id):
        return Response(service.set_membership(actor_id=request.user.pk, domain_id=domain_id, tenant_id=tenant_id,
            **self.payload(request, MembershipInput)))


class AgreementPublicationView(ManagementView):
    @extend_schema(request=PublicationInput, responses=OpenApiTypes.OBJECT)
    def post(self, request, domain_id):
        return Response(service.publish_agreement(actor_id=request.user.pk, domain_id=domain_id,
            **self.payload(request, PublicationInput)), status=201)


class OwnAcceptanceView(ManagementView):
    @extend_schema(request=AcceptanceInput, responses=OpenApiTypes.OBJECT)
    def post(self, request, domain_id):
        return Response(service.accept_agreement(actor_id=request.user.pk, domain_id=domain_id,
            **self.payload(request, AcceptanceInput)), status=201)


class OwnRevocationView(ManagementView):
    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def post(self, request, acceptance_id):
        if request.data:
            raise serializers.ValidationError({"non_field_errors": ["INVALID_FIELDS"]})
        return Response(service.revoke_acceptance(actor_id=request.user.pk, acceptance_id=acceptance_id))
