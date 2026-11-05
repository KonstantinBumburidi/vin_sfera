import json

from django.db import models
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from wagtail.search import index

from wagtail.models import Page, Orderable
from wagtail.fields import StreamField, RichTextField
from wagtail.blocks import CharBlock, RichTextBlock, StructBlock, BooleanBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail.admin.panels import FieldPanel, InlinePanel
from channels.models import ChannelGroup
from wagtail.blocks import StructBlock, CharBlock, PageChooserBlock
from modelcluster.fields import ParentalKey
from wagtail.documents.models import Document
from base.seo import SeoPageMixin
from django.http import HttpResponse
from django.template import loader

from spblock.blocks import (
    HeroBlock,
    TextImageBlock,
    TextOnlyBlock,
    WidthButtonBlock,
)

#-----------------------------------------------------------------------------------
class HomePage(SeoPageMixin, Page):
    content_blocks = StreamField([
        ('hero', HeroBlock()),
        ('section', TextImageBlock()),
        ('text_only', TextOnlyBlock()),
        ('width_button', WidthButtonBlock()),
    ], use_json_field=True, blank=True, collapsed=True, verbose_name="Контент (блоки)")

    content_panels = Page.content_panels + [
        FieldPanel('content_blocks'),   # новое поле
    ]

class SectionPage(SeoPageMixin, Page):
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

class ChannelSectionPage(SeoPageMixin, Page):
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
class BooksIndexPage(SeoPageMixin, Page):
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
class ArchangelsPage(SeoPageMixin, Page):  # ← если хочешь ArchangelsPage — просто переименуй
    intro = RichTextField(blank=True, verbose_name="Введение ")

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        InlinePanel('table_rows', label="Строки таблицы"),  # ← теперь InlinePanel импортирован
    ]

    parent_page_types = ['home.HomePage']  # или где нужно размещать
    subpage_types = []

    class Meta:
        verbose_name = "Блок энергий 95 Архангелов"


#-----------------------------------------------------------
# База знаний: словарь терминов от А до Я
#-----------------------------------------------------------
GLOSSARY_ALPHABET = "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЭЮЯ"  # без Ъ, Ы, Ь — с них слова не начинаются


def glossary_sort_key(text):
    # Ё сортируем вместе с Е, регистр не важен
    return text.strip().lower().replace("ё", "е")


class GlossaryTerm(Orderable):
    page = ParentalKey('home.GlossaryPage', on_delete=models.CASCADE, related_name='terms')
    term = models.CharField(max_length=255, verbose_name="Термин")
    definition = RichTextField(
        verbose_name="Определение",
        features=['bold', 'italic', 'link', 'ol', 'ul'],
    )
    anchor = models.SlugField(
        max_length=255, blank=True, allow_unicode=True,
        verbose_name="Якорь (необязательно)",
        help_text="Часть адреса после #, например «kanal». Пусто — сделается из термина сам.",
    )

    panels = [
        FieldPanel('term'),
        FieldPanel('definition'),
        FieldPanel('anchor'),
    ]

    def get_anchor(self):
        return self.anchor or slugify(self.term, allow_unicode=True)

    @property
    def letter(self):
        first = self.term.strip()[:1].upper()
        return "Е" if first == "Ё" else first

    def __str__(self):
        return self.term


class GlossaryPage(SeoPageMixin, Page):
    intro = RichTextField(blank=True, verbose_name="Введение (текст сверху)")

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        InlinePanel('terms', label="Термины", help_text="Порядок не важен — на сайте термины сортируются по алфавиту"),
    ]

    parent_page_types = ['home.HomePage']
    subpage_types = []

    search_fields = Page.search_fields + [
        index.SearchField('intro'),
        index.RelatedFields('terms', [
            index.SearchField('term'),
            index.SearchField('definition'),
        ]),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        terms = sorted(self.terms.all(), key=lambda t: glossary_sort_key(t.term))

        groups = {}
        for t in terms:
            groups.setdefault(t.letter, []).append(t)
        # Сначала русские буквы по алфавиту, потом всё остальное (латиница, цифры)
        letters = [l for l in GLOSSARY_ALPHABET if l in groups]
        letters += sorted(l for l in groups if l not in GLOSSARY_ALPHABET)

        context['term_groups'] = [(l, groups[l]) for l in letters]
        context['alphabet'] = [(l, l in groups) for l in GLOSSARY_ALPHABET]
        context['extra_letters'] = [l for l in letters if l not in GLOSSARY_ALPHABET]
        context['terms_count'] = len(terms)
        context['glossary_jsonld'] = self.get_jsonld(request, terms)
        return context

    def get_jsonld(self, request, terms):
        # Разметка schema.org DefinedTermSet — поисковики понимают, что это словарь
        page_url = self.get_full_url(request)
        data = {
            "@context": "https://schema.org",
            "@type": "DefinedTermSet",
            "name": self.title,
            "url": page_url,
            "hasDefinedTerm": [
                {
                    "@type": "DefinedTerm",
                    "name": t.term,
                    "description": " ".join(strip_tags(t.definition).split()),
                    "url": f"{page_url}#{t.get_anchor()}",
                }
                for t in terms
            ],
        }
        text = json.dumps(data, ensure_ascii=False, indent=2).replace("<", "\\u003c")
        return mark_safe(f'<script type="application/ld+json">\n{text}\n</script>')

    class Meta:
        verbose_name = "База знаний (словарь терминов)"
