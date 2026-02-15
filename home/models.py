from django.db import models

from wagtail.models import Page, Orderable
from wagtail.fields import StreamField, RichTextField
from wagtail.blocks import CharBlock, RichTextBlock, StructBlock, BooleanBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail.admin.panels import FieldPanel, InlinePanel
from channels.models import ChannelGroup
from wagtail.blocks import StructBlock, CharBlock, PageChooserBlock
from modelcluster.fields import ParentalKey
from wagtail.documents.models import Document
from wagtailmetadata.models import MetadataPageMixin
from django.http import HttpResponse
from django.template import loader

from spblock.blocks import (
    HeroBlock,
    TextImageBlock,
    TextOnlyBlock,
    WidthButtonBlock,
)

#-----------------------------------------------------------------------------------
class HomePage(MetadataPageMixin, Page):
    content_blocks = StreamField([
        ('hero', HeroBlock()),
        ('section', TextImageBlock()),
        ('text_only', TextOnlyBlock()),
        ('width_button', WidthButtonBlock()),
    ], use_json_field=True, blank=True, collapsed=True, verbose_name="Контент (блоки)")

    content_panels = Page.content_panels + [
        FieldPanel('content_blocks'),   # новое поле
    ]

class SectionPage(MetadataPageMixin, Page):
    # Можно добавить свои поля, например описание, изображения и т.д.
    intro = RichTextField(blank=True, verbose_name="Краткое введение")
    body = StreamField([
        ('section', TextImageBlock()),
        ('text_only', TextOnlyBlock()),
        ('width_button', WidthButtonBlock()),
    ], use_json_field=True, blank=True, verbose_name="Контент раздела")

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body'),
    ]

    # Ограничиваем, чтобы эти страницы были только дочерними главной
    parent_page_types = ['home.HomePage']

class ChannelSectionPage(MetadataPageMixin, Page):
    intro = RichTextField(blank=True, verbose_name="Введение ")
    body = StreamField([
        ('section', TextImageBlock()),
        ('text_only', TextOnlyBlock()),
        ('width_button', WidthButtonBlock()),
    ], use_json_field=True, blank=True, verbose_name="Контент раздела")

    section_type = models.PositiveSmallIntegerField(
        choices=ChannelGroup.SECTION_CHOICES,
        verbose_name="Тип раздела частот",
        help_text="Выберите группы"
    )

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body'),
        FieldPanel('section_type'),
    ]

    parent_page_types = ['home.HomePage']
    subpage_types = []

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context['groups'] = ChannelGroup.objects.filter(
            section=self.section_type
        ).prefetch_related('channels').order_by('sort_order')
        return context

#-----------------------------------------------------------
class BooksIndexPage(MetadataPageMixin, Page):
    intro = RichTextField(blank=True, verbose_name="Введение (текст сверху)")

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    parent_page_types = ['home.HomePage']  # или где хотите размещать
    subpage_types = []  # чтобы не было дочерних страниц

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)

        # Все документы с тегом "book", сортируем по названию или дате
        books = Document.objects.filter(tags__name="book").order_by('title')

        context['books'] = books
        return context

    class Meta:
        verbose_name = "Страница книг (скачивание)"

#-----------------------------------------------------------
class TableRow(Orderable):  # ← Orderable для сортировки в админке
    page = ParentalKey('home.ArchangelsPage', on_delete=models.CASCADE, related_name='table_rows')
    number = models.PositiveIntegerField(verbose_name="ID (порядковый номер)", default=0)
    name = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(verbose_name="Описание", blank=True)

    panels = [
        FieldPanel('number'),
        FieldPanel('name'),
        FieldPanel('description'),
    ]

    class Meta:
        ordering = ['number']  # по умолчанию сортируем по номеру

    def __str__(self):
        return f"{self.number} — {self.name}"

#-----------------------------------------------------------
class ArchangelsPage(MetadataPageMixin, Page):  # ← если хочешь ArchangelsPage — просто переименуй
    intro = RichTextField(blank=True, verbose_name="Введение ")

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        InlinePanel('table_rows', label="Строки таблицы"),  # ← теперь InlinePanel импортирован
    ]

    parent_page_types = ['home.HomePage']  # или где нужно размещать
    subpage_types = []

    class Meta:
        verbose_name = "Блок энергий 95 Архангелов"

