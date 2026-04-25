#!/usr/bin/env python3
import argparse
import json
import os
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import django
from django.contrib.auth import get_user_model
from django.test import Client

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from crm.models import Organization, Tenant  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test for editor API auth + CRUD flows")
    parser.add_argument("--tenant-id", type=int, default=1)
    parser.add_argument("--username", default=os.getenv("SMOKE_USERNAME", "frefor"))
    parser.add_argument("--password", default=os.getenv("SMOKE_PASSWORD", "Test1234!"))
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--referer", default="https://localhost/")
    parser.add_argument("--bootstrap-user", action="store_true", default=True)
    parser.add_argument("--no-bootstrap-user", dest="bootstrap_user", action="store_false")
    parser.add_argument("--bootstrap-tenant", action="store_true", default=True)
    parser.add_argument("--no-bootstrap-tenant", dest="bootstrap_tenant", action="store_false")
    return parser.parse_args()


def decode(response) -> str:
    return response.content.decode("utf-8") if response.content else ""


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        body = decode(response)
        raise AssertionError(f"{label}: expected {expected}, got {response.status_code}. Body: {body[:500]}")


def parse_json(response, label: str):
    try:
        return json.loads(decode(response))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{label}: invalid JSON response") from exc


def request_kwargs(args: argparse.Namespace, client: Client) -> dict:
    return {
        "secure": True,
        "HTTP_HOST": args.host,
        "HTTP_REFERER": args.referer,
        "HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value,
    }


def log(label: str, response) -> None:
    print(f"{label}: {response.status_code}")


def bootstrap_prerequisites(args: argparse.Namespace) -> None:
    if args.bootstrap_tenant:
        tenant, created = Tenant.objects.get_or_create(
            id=args.tenant_id,
            defaults={
                "name": f"Smoke Tenant {args.tenant_id}",
                "slug": f"smoke-{args.tenant_id}",
            },
        )
        print(f"bootstrap.tenant: {'created' if created else 'exists'} ({tenant.id})")

    if args.bootstrap_user:
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=args.username,
            defaults={"is_staff": True, "is_superuser": True},
        )
        user.set_password(args.password)
        user.save(update_fields=["password", "is_staff", "is_superuser"])
        print(f"bootstrap.user: {'created' if created else 'updated'} ({user.username})")


def main() -> int:
    args = parse_args()
    tenant_id = args.tenant_id

    bootstrap_prerequisites(args)

    client = Client(enforce_csrf_checks=True)

    # Auth bootstrap
    r = client.get("/api/auth/csrf/", secure=True, HTTP_HOST=args.host)
    assert_status(r, 200, "csrf")
    log("csrf", r)

    r = client.post(
        "/api/auth/login/",
        data=json.dumps({"username": args.username, "password": args.password}),
        content_type="application/json",
        **request_kwargs(args, client),
    )
    assert_status(r, 200, "login")
    log("login", r)

    r = client.get("/api/auth/session/", secure=True, HTTP_HOST=args.host)
    assert_status(r, 200, "session")
    session = parse_json(r, "session")
    if not session.get("authenticated"):
        raise AssertionError("session: expected authenticated=true after login")
    log("session", r)

    suffix = uuid.uuid4().hex[:8]

    # Organization CRUD
    org_payload = {
        "tenant": tenant_id,
        "name": f"Smoke Org {suffix}",
        "org_number": f"9{suffix}",
        "email": f"smoke-org-{suffix}@example.com",
        "phone": "+47 900 00 000",
        "municipalities": "Bodø",
        "note": "Smoke test organization",
        "is_published": False,
        "publish_phone": False,
    }
    r = client.post(
        f"/api/tenants/{tenant_id}/organizations/",
        data=json.dumps(org_payload),
        content_type="application/json",
        **request_kwargs(args, client),
    )
    assert_status(r, 201, "organization.create")
    org_id = parse_json(r, "organization.create")["id"]
    log("organization.create", r)

    r = client.get(f"/api/tenants/{tenant_id}/organizations/{org_id}/", secure=True, HTTP_HOST=args.host)
    assert_status(r, 200, "organization.read")
    log("organization.read", r)

    r = client.patch(
        f"/api/tenants/{tenant_id}/organizations/{org_id}/",
        data=json.dumps({"name": f"Smoke Org Updated {suffix}", "is_published": True}),
        content_type="application/json",
        **request_kwargs(args, client),
    )
    assert_status(r, 200, "organization.patch")
    log("organization.patch", r)

    # Person CRUD
    person_payload = {
        "tenant": tenant_id,
        "full_name": f"Smoke Person {suffix}",
        "email": f"smoke-person-{suffix}@example.com",
        "phone": "+47 911 11 111",
        "municipality": "Bodø",
        "note": "Smoke test person",
    }
    r = client.post(
        f"/api/tenants/{tenant_id}/persons/",
        data=json.dumps(person_payload),
        content_type="application/json",
        **request_kwargs(args, client),
    )
    assert_status(r, 201, "person.create")
    person_id = parse_json(r, "person.create")["id"]
    log("person.create", r)

    r = client.get(f"/api/tenants/{tenant_id}/persons/{person_id}/", secure=True, HTTP_HOST=args.host)
    assert_status(r, 200, "person.read")
    log("person.read", r)

    r = client.patch(
        f"/api/tenants/{tenant_id}/persons/{person_id}/",
        data=json.dumps({"full_name": f"Smoke Person Updated {suffix}"}),
        content_type="application/json",
        **request_kwargs(args, client),
    )
    assert_status(r, 200, "person.patch")
    log("person.patch", r)

    # Organization-person CRUD
    r = client.post(
        f"/api/tenants/{tenant_id}/organization-people/",
        data=json.dumps(
            {
                "tenant": tenant_id,
                "organization": org_id,
                "person": person_id,
                "status": "ACTIVE",
                "publish_person": False,
            }
        ),
        content_type="application/json",
        **request_kwargs(args, client),
    )
    assert_status(r, 201, "organization_person.create")
    org_person_id = parse_json(r, "organization_person.create")["id"]
    log("organization_person.create", r)

    r = client.get(
        f"/api/tenants/{tenant_id}/organization-people/{org_person_id}/",
        secure=True,
        HTTP_HOST=args.host,
    )
    assert_status(r, 200, "organization_person.read")
    log("organization_person.read", r)

    r = client.patch(
        f"/api/tenants/{tenant_id}/organization-people/{org_person_id}/",
        data=json.dumps({"status": "INACTIVE", "publish_person": True}),
        content_type="application/json",
        **request_kwargs(args, client),
    )
    assert_status(r, 200, "organization_person.patch")
    log("organization_person.patch", r)

    # Person-contact CRUD
    r = client.post(
        f"/api/tenants/{tenant_id}/person-contacts/",
        data=json.dumps(
            {
                "tenant": tenant_id,
                "person": person_id,
                "type": "EMAIL",
                "value": f"contact-{suffix}@example.com",
                "is_primary": True,
                "is_public": False,
            }
        ),
        content_type="application/json",
        **request_kwargs(args, client),
    )
    assert_status(r, 201, "person_contact.create")
    contact_id = parse_json(r, "person_contact.create")["id"]
    log("person_contact.create", r)

    r = client.get(
        f"/api/tenants/{tenant_id}/person-contacts/{contact_id}/",
        secure=True,
        HTTP_HOST=args.host,
    )
    assert_status(r, 200, "person_contact.read")
    log("person_contact.read", r)

    r = client.get(
        f"/api/tenants/{tenant_id}/person-contacts/?person={person_id}",
        secure=True,
        HTTP_HOST=args.host,
    )
    assert_status(r, 200, "person_contact.list_by_person")
    items = parse_json(r, "person_contact.list_by_person")
    if not any(item.get("id") == contact_id for item in items):
        raise AssertionError("person_contact.list_by_person: created contact not found in filtered list")
    log("person_contact.list_by_person", r)

    r = client.patch(
        f"/api/tenants/{tenant_id}/person-contacts/{contact_id}/",
        data=json.dumps({"type": "PHONE", "value": "+47 922 22 222", "is_public": True}),
        content_type="application/json",
        **request_kwargs(args, client),
    )
    assert_status(r, 200, "person_contact.patch")
    log("person_contact.patch", r)

    # Cleanup + delete verification
    r = client.delete(
        f"/api/tenants/{tenant_id}/person-contacts/{contact_id}/",
        **request_kwargs(args, client),
    )
    assert_status(r, 204, "person_contact.delete")
    log("person_contact.delete", r)

    r = client.get(
        f"/api/tenants/{tenant_id}/person-contacts/{contact_id}/",
        secure=True,
        HTTP_HOST=args.host,
    )
    assert_status(r, 404, "person_contact.verify_deleted")
    log("person_contact.verify_deleted", r)

    r = client.delete(
        f"/api/tenants/{tenant_id}/organization-people/{org_person_id}/",
        **request_kwargs(args, client),
    )
    assert_status(r, 204, "organization_person.delete")
    log("organization_person.delete", r)

    r = client.get(
        f"/api/tenants/{tenant_id}/organization-people/{org_person_id}/",
        secure=True,
        HTTP_HOST=args.host,
    )
    assert_status(r, 404, "organization_person.verify_deleted")
    log("organization_person.verify_deleted", r)

    r = client.delete(
        f"/api/tenants/{tenant_id}/persons/{person_id}/",
        **request_kwargs(args, client),
    )
    assert_status(r, 204, "person.delete")
    log("person.delete", r)

    r = client.get(f"/api/tenants/{tenant_id}/persons/{person_id}/", secure=True, HTTP_HOST=args.host)
    assert_status(r, 404, "person.verify_deleted")
    log("person.verify_deleted", r)

    r = client.delete(
        f"/api/tenants/{tenant_id}/organizations/{org_id}/",
        **request_kwargs(args, client),
    )
    assert_status(r, 204, "organization.delete")
    log("organization.delete", r)

    r = client.get(f"/api/tenants/{tenant_id}/organizations/{org_id}/", secure=True, HTTP_HOST=args.host)
    assert_status(r, 404, "organization.verify_deleted")
    log("organization.verify_deleted", r)

    if not Organization.objects.filter(tenant_id=tenant_id).exists():
        print(f"warning: tenant {tenant_id} has no organizations after smoke cleanup")

    print("SMOKE OK: auth + organizations + persons + organization-people + person-contacts")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"SMOKE FAILED: {exc}", file=sys.stderr)
        raise
