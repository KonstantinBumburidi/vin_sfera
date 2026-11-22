from django.db import models

from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.admin.widgets.slug import SlugInput
from wagtail.images import get_image_model

SITE_NAME = "Путь Здоровья"
DEFAULT_DESCRIPTION = ("Центр кинезиологии «Путь Здоровья» в Алматы: кинезиология, остеопатия, P-DTR, "
                       "энергопсихология, биорезонанс")
# Размер картинки для соцсетей (рекомендация Facebook/Telegram/WhatsApp)
SEO_IMAGE_FILTER = "fill-1200x630"
# Картинка для соцсетей у страниц без своей — имена файлов из «Изображений»,
# берётся первая найденная (posv95.jpg — запасная, пока новую не загрузили)
DEFAULT_SEO_IMAGES = ("sfera-social.jpg", "posv95.jpg")


def default_seo_image():
    Image = get_image_model()
    for name in DEFAULT_SEO_IMAGES:
        image = Image.objects.filter(file__endswith=f"/{name}").first()
        if image:
            return image
    return None


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
        image = self.search_image or default_seo_image()
        if image:
            return image.get_rendition(SEO_IMAGE_FILTER)
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
