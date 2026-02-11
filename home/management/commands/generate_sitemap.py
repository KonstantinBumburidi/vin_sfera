# home/management/commands/generate_sitemap.py

from django.core.management.base import BaseCommand
from wagtail.models import Page, Site
from django.utils.timezone import localtime
from xml.etree.ElementTree import Element, SubElement, ElementTree
from django.conf import settings
import os


class Command(BaseCommand):
    help = "Генерирует sitemap.xml на основе дерева страниц Wagtail"

    # Больше никаких аргументов — путь фиксированный
    EXCLUDED_PREFIXES = ('/videos/', '/materials/audio/')
    OUTPUT_FILENAME = 'vin_sfera/templates/sitemap.xml'

    def handle(self, *args, **options):
        site = Site.objects.get(is_default_site=True)
        root_page = site.root_page.specific

        self.stdout.write(f"Генерация sitemap от корня: {root_page.title}")

        urlset = Element(
            "urlset",
            xmlns="http://www.sitemaps.org/schemas/sitemap/0.9",
        )

        def walk(page: Page):
            # Получаем относительный URL страницы (начинается с /)
            relative_url = page.url  # например: "/", "/about/", "/videos/player/"

            # Исключаем целые ветки по префиксам
            if relative_url.startswith(self.EXCLUDED_PREFIXES):
                return  # не добавляем страницу и не идём в её дочерние

            # Добавляем только живые публичные страницы
            if page.live:
                full_url = page.get_full_url()
                if full_url:
                    url = SubElement(urlset, "url")

                    loc = SubElement(url, "loc")
                    loc.text = full_url

                    if page.last_published_at:
                        lastmod = SubElement(url, "lastmod")
                        lastmod.text = localtime(page.last_published_at).date().isoformat()

            # Рекурсивно обходим дочерние страницы
            for child in page.get_children().specific().live().public():
                walk(child)

        # Начинаем обход с корневой страницы сайта
        walk(root_page)

        # Фиксированный путь — корень проекта
        output_path = os.path.join(settings.BASE_DIR, self.OUTPUT_FILENAME)

        tree = ElementTree(urlset)
        tree.write(
            output_path,
            encoding="utf-8",
            xml_declaration=True,
        )

        self.stdout.write(
            self.style.SUCCESS(f"sitemap.xml успешно создан: {output_path}")
        )