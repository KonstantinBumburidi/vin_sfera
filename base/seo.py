from django.db import models

from wagtail.admin.panels import FieldPanel
from wagtailmetadata.models import MetadataPageMixin

SITE_NAME = "Сфера Сознания"
DEFAULT_DESCRIPTION = "Центр Сфера Сознания — космоэнергетика, кинезиология, биорезонанс в Алматы"

# Ветки, которые не попадают в sitemap (как раньше в generate_sitemap)
SITEMAP_EXCLUDED_PREFIXES = ("/videos/", "/materials/audio/")


class SeoPageMixin(MetadataPageMixin):
    """Мета-теги страницы + флажок «скрыть от поисковиков»."""

    noindex = models.BooleanField(
        default=False,
        verbose_name="Скрыть от поисковиков",
        help_text="noindex: страница видна посетителям, но не попадает в поиск и sitemap",
    )

    promote_panels = MetadataPageMixin.promote_panels + [
        FieldPanel("noindex"),
    ]

    def get_meta_title(self):
        # Без SEO-заголовка добавляем название сайта, чтобы title не был просто «Статьи»
        return self.seo_title or f"{self.title} | {SITE_NAME}"

    def get_meta_description(self):
        # Убираем переносы строк из описания
        return " ".join((self.search_description or DEFAULT_DESCRIPTION).split())

    def get_sitemap_urls(self, request=None):
        if self.noindex or (self.url or "").startswith(SITEMAP_EXCLUDED_PREFIXES):
            return []
        return super().get_sitemap_urls(request)

    class Meta:
        abstract = True
