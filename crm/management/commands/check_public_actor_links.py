from __future__ import annotations

from html.parser import HTMLParser

from django.core.management.base import BaseCommand
from django.test import Client

from crm.models import Organization


class PublicActorCardParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.card_links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        href = attributes.get("href")
        if "card" in classes and href:
            self.card_links.append(href)


class Command(BaseCommand):
    help = "Read-only smoke test for all PUBLIC actor card links."

    def add_arguments(self, parser):
        parser.add_argument(
            "--host",
            default="staging.northernsound.no",
            help="HTTP host used by the Django test client.",
        )

    def handle(self, *args, **options):
        host = options["host"]
        client = Client(HTTP_HOST=host, HTTP_X_FORWARDED_PROTO="https")

        list_response = client.get("/public/actors/")
        parser = PublicActorCardParser()
        parser.feed(list_response.content.decode(list_response.charset or "utf-8", errors="replace"))

        broken_links = []
        for href in parser.card_links:
            response = client.get(href, follow=True)
            final_status = response.status_code
            if final_status >= 400:
                broken_links.append((href, final_status, response.redirect_chain))

        self.stdout.write("check_public_actor_links")
        self.stdout.write(f"list_status={list_response.status_code}")
        self.stdout.write(f"public_actors_total={Organization.objects.filter(is_published=True).count()}")
        self.stdout.write(f"card_links_total={len(parser.card_links)}")
        self.stdout.write(f"broken_links={len(broken_links)}")
        for href, status, chain in broken_links:
            self.stdout.write(f"- href={href} status={status} redirects={chain}")
