from django.db import models

from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.admin.widgets.slug import SlugInput

SITE_NAME = "Сфера Сознания"
DEFAULT_DESCRIPTION = "Центр Сфера Сознания — космоэнергетика, кинезиология, биорезонанс в Алматы"
# Размер картинки для соцсетей (рекомендация Facebook/Telegram/WhatsApp)
SEO_IMAGE_FILTER = "fill-1200x630"


class SeoPageMixin(models.Model):
    """SEO-поля страницы: картинка для соцсетей, флажок «скрыть от поисковиков».

    Мета-теги выводит шаблон includes/seo_meta.html.
    """

    # True у типов страниц, которые всегда скрыты от поисковиков (видео, аудио)
    always_noindex = False

    search_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        related_name="+",
        on_delete=models.SET_NULL,
        verbose_name="Картинка для соцсетей",
        help_text="Показывается при отправке ссылки в WhatsApp, Telegram, соцсетях. Обрезается до 1200×630",
    )
    noindex = models.BooleanField(
        default=False,
        verbose_name="Скрыть от поисковиков",
        help_text="noindex: страница видна посетителям, но не попадает в поиск и sitemap",
    )

    promote_panels = [
        MultiFieldPanel(
            [
                FieldPanel("slug", widget=SlugInput),
                FieldPanel("seo_title"),
                FieldPanel("search_description"),
                FieldPanel("search_image"),
                FieldPanel("noindex"),
                FieldPanel("show_in_menus"),
            ],
            "SEO и продвижение",
        ),
    ]

    def get_meta_title(self):
        # Без SEO-заголовка добавляем название сайта, чтобы title не был просто «Статьи»
        return self.seo_title or f"{self.title} | {SITE_NAME}"

    def get_meta_description(self):
        # Убираем переносы строк из описания
        return " ".join((self.search_description or DEFAULT_DESCRIPTION).split())

    def get_meta_image(self):
        if self.search_image:
            return self.search_image.get_rendition(SEO_IMAGE_FILTER)
        return None

    @property
    def robots_noindex(self):
        return self.noindex or self.always_noindex

    def get_sitemap_urls(self, request=None):
        if self.robots_noindex:
            return []
        return super().get_sitemap_urls(request)

    class Meta:
        abstract = True
