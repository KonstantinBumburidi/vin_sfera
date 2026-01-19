from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel
from wagtail.documents.models import Document
# Если аудио-файлы будем хранить в Wagtail Documents
from wagtailmetadata.models import MetadataPageMixin

from blog.models import Category  # общие категории (в твоём файле blog_models.py)

class AudioIndexPage(MetadataPageMixin, Page):
    intro = RichTextField(blank=True, verbose_name="Введение")

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    def get_context(self, request):
        context = super().get_context(request)

        # Категории только для аудио + счётчик
        categories = Category.objects.filter(section=3).annotate(
            audio_count=models.Count('audio_pages')
        ).order_by('title')
        context['categories'] = categories

        audios = AudioPage.objects.child_of(self).live().order_by('-date')

        category_id = request.GET.get('category')
        if category_id:
            try:
                audios = audios.filter(category__id=int(category_id), category__section=3)
            except ValueError:
                pass

        context['audios'] = audios
        return context

    class Meta:
        verbose_name = "Индекс аудио уроков"


class AudioPage(MetadataPageMixin, Page):
    date = models.DateField(verbose_name="Дата публикации")
    duration = models.CharField(max_length=20, blank=True, verbose_name="Длительность (например, 15:34)")
    intro = RichTextField(blank=True, verbose_name="Описание урока")
    audio_file = models.ForeignKey(
        'wagtaildocs.Document',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Аудио-файл (mp3)"
    )
    external_url = models.URLField(blank=True, verbose_name="Внешняя ссылка на аудио ")
    main_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Обложка"
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audio_pages',
        limit_choices_to={'section': 3},
        verbose_name="Категория",
        default=7
    )

    content_panels = Page.content_panels + [
        FieldPanel('date'),
        FieldPanel('duration'),
        FieldPanel('category'),
        FieldPanel('main_image'),
        FieldPanel('intro'),
        FieldPanel('audio_file'),
        FieldPanel('external_url'),
    ]

    class Meta:
        verbose_name = "Аудио урок"

