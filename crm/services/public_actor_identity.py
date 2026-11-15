"""ADR-011 identity compatibility boundary, before canonical PUBLIC cutover.

Publication and legacy tag/contact/image semantics stay unchanged. Assignments
never multiply the base Organization rows or authorize publication here.
"""
from django.http import Http404

from crm.models import Organization


def public_actors():
    return Organization.objects.filter(is_published=True)


def public_actor_by_org_number(queryset, org_number):
    # Resolve at most two distinct published identities in one statement.
    # Missing, private-only and ambiguous aliases have the same public result.
    matches = list(queryset.filter(is_published=True, org_number=org_number)
                   .order_by("pk").distinct()[:2])
    if len(matches) != 1:
        raise Http404("No unique published actor matches this organization number.")
    return matches[0]
