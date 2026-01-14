from django.db import models
from django.db.models import Count
from wagtail.models import Page
from wagtail.snippets.models import  register_snippet
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.images.api.fields import ImageRenditionField
from wagtail.images.models import Image  # Для main_image
from wagtail.search import index
from django.utils.text import slugify

from modelcluster.fields import ParentalKey
# from modelcluster.models import Orderable  # Если галерея нужна позже, но пока нет

SECTION_CHOICES = [
    (1, "Блог"),
    (2, "Видео"),
    (3, "Аудио"),        # запас на будущее
    (4, "Курсы/Учеба"),
]

@register_snippet  # Д
class Category(models.Model):  #
    title = models.CharField(verbose_name="Название", max_length=100)
    section = models.PositiveSmallIntegerField(
        choices=SECTION_CHOICES,
        default=1,
        verbose_name="Раздел контента"
    )

    panels = [
        FieldPanel('title'),
        FieldPanel('section'),
    ]

    def __str__(self):
        return f"{self.title.ljust(35, '\xa0')} : {self.get_section_display().ljust(12, '\xa0')}"

# Новый метод — красивое отображение section в списке
    # def section_display(self):
        # return self.get_section_display()  # возвращает текст из choices ("Блог", "Видео" и т.д.)

    # section_display.short_description = "Раздел"  # заголовок колонки в админке

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['title']


# ------------------------------------------------------------
# Индекс блога (список статей, с фильтром)
class BlogIndexPage(Page):
    intro = RichTextField(blank=True, verbose_name="Введение")

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    # Кастомный контекст: фильтр по категории из GET
    def get_context(self, request):
        context = super().get_context(request)

        # Все категории для меню
        categories = Category.objects.filter(section=1).annotate(
            article_count=Count('articles')
        ).order_by('title')
        context['categories'] = categories

        # Прямой запрос к BlogPage — ключевой фикс!
        articles = BlogPage.objects.child_of(self).live().order_by('-date')

        category_id = request.GET.get('category')
        if category_id:
            try:
                category_id = int(category_id)
                articles = articles.filter(category__id=category_id, category__section=1)
            except (ValueError, TypeError):
                pass  # Если мусор в GET — игнорируем фильтр

        # Сортировка по дате (новые сверху)
        articles = articles.order_by('-date')

        context['articles'] = articles
        return context

    # Поиск (опционально)
    search_fields = Page.search_fields + [
        index.SearchField('intro'),
    ]

    class Meta:
        verbose_name = "Индекс блога"

# Страница статьи (как Article, но Page)
class BlogPage(Page):
    date = models.DateField(verbose_name="Дата поста")
    intro = models.CharField(verbose_name="Краткое описание (preview)", max_length=250, blank=True)
    body = RichTextField(verbose_name="Содержание", blank=True)
    author = models.CharField(verbose_name="Автор", max_length=80, default='Бумбуриди')
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='articles'
    )
    main_image = models.ForeignKey(
        'wagtailimages.Image', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name="Главное изображение"
    )

        # Контекст для детальной страницы (дети, если нужно)
    def get_context(self, request):
        context = super().get_context(request)
        # Похожие статьи: из той же категории, кроме текущей, новые сверху
        related_articles = BlogPage.objects.live().exclude(id=self.id)

        if self.category:
            related_articles = related_articles.filter(category=self.category)

        related_articles = related_articles.order_by('-date')[:4]  # 4 штуки — оптимально
        context['related_articles'] = related_articles

        # Опционально: родительский индекс блога (для breadcrumbs или ссылок)
        context['blog_index'] = self.get_parent().specific
        return context


    content_panels = Page.content_panels + [
        FieldPanel('date'),
        FieldPanel('intro'),
        FieldPanel('body'),
        FieldPanel('author'),
        FieldPanel('category'),
        FieldPanel('main_image'),
    ]

    # Поиск
    search_fields = Page.search_fields + [
        index.SearchField('intro'),
        index.SearchField('body'),
        index.SearchField('author'),
    ]

    # Slug автогенерация (как раньше)
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Статья блога"
