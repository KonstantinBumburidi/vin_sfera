from django.core.management.base import BaseCommand, CommandError

from base.seo import SeoPageMixin
from base.seo_file import SEO_FILE, get_site, image_key, page_key, write_file


class Command(BaseCommand):
    help = "Выгружает SEO-поля опубликованных страниц в seo/pages.yaml"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all", action="store_true",
            help="Включить и страницы, всегда скрытые от поисковиков (видео, аудио)",
        )
        parser.add_argument(
            "--force", action="store_true",
            help="Перезаписать существующий seo/pages.yaml",
        )

    def handle(self, *args, **options):
        if SEO_FILE.exists() and not options["force"]:
            raise CommandError(f"{SEO_FILE} уже есть. Чтобы перезаписать, добавьте --force")

        site = get_site()
        pages = site.root_page.get_descendants(inclusive=True).live().specific().order_by("path")

        data = {}
        for page in pages:
            if not isinstance(page, SeoPageMixin):
                continue
            if page.always_noindex and not options["all"]:
                continue
            data[page_key(page, site)] = {
                "page": page.title,
                "seo_title": page.seo_title,
                "description": " ".join(page.search_description.split()),
                "image": image_key(page.search_image),
                "noindex": page.noindex,
            }

        write_file(data)
        self.stdout.write(self.style.SUCCESS(f"Выгружено страниц: {len(data)} -> {SEO_FILE}"))
