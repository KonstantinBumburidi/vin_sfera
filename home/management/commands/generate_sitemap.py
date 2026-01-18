# home/management/commands/generate_sitemap.py

from django.core.management.base import BaseCommand
from wagtail.models import Page, Site
from django.utils.timezone import localtime
from xml.etree.ElementTree import Element, SubElement, ElementTree


class Command(BaseCommand):
    help = "Генерирует sitemap.xml на основе дерева страниц Wagtail"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="sitemap.xml",
            help="Путь для сохранения sitemap.xml (по умолчанию: sitemap.xml в корне проекта)",
        )

    def handle(self, *args, **options):
        site = Site.objects.get(is_default_site=True)
        root_page = site.root_page.specific

        self.stdout.write(f"Генерация sitemap от корня: {root_page.title}")

        urlset = Element(
            "urlset",
            xmlns="http://www.sitemaps.org/schemas/sitemap/0.9",
        )

        def walk(page):
            if page.live:
                full_url = page.get_full_url()
                if full_url:
                    url = SubElement(urlset, "url")

                    loc = SubElement(url, "loc")
                    loc.text = full_url

                    if page.last_published_at:
                        lastmod = SubElement(url, "lastmod")
                        lastmod.text = localtime(
                            page.last_published_at
                        ).date().isoformat()

            for child in page.get_children().specific().live().public():
                walk(child)

        walk(root_page)

        output_path = options["output"]
        tree = ElementTree(urlset)
        tree.write(
            output_path,
            encoding="utf-8",
            xml_declaration=True,
        )

        self.stdout.write(
            self.style.SUCCESS(f"sitemap.xml успешно создан: {output_path}")
        )
