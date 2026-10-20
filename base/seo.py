from django.db import models

from wagtail.admin.panels import FieldPanel
from wagtailmetadata.models import MetadataPageMixin

SITE_NAME = "Сфера Сознания"
DEFAULT_DESCRIPTION = "Центр Сфера Сознания — космоэнергетика, кинезиология, биорезонанс в Алматы"


class SeoPageMixin(MetadataPageMixin):
    """Мета-теги страницы + флажок «скрыть от поисковиков»."""

    # True у типов страниц, которые всегда скрыты от поисковиков (видео, аудио)
    always_noindex = False

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

    @property
    def robots_noindex(self):
        return self.noindex or self.always_noindex

    def get_sitemap_urls(self, request=None):
        if self.robots_noindex:
            return []
        return super().get_sitemap_urls(request)

    class Meta:
        abstract = True
