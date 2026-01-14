from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel
from wagtail.images.models import Image
# from wagtail.images.edit_handlers import FieldPanel as ImageFieldPanel  # не обязательно, FieldPanel работает
from blog.models import Category  # импортируем общую категорию
import datetime

class VideoIndexPage(Page):
    intro = RichTextField(blank=True, verbose_name="Введение")

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    def get_context(self, request):
        context = super().get_context(request)

        # Категории только для видео
        categories = Category.objects.filter(section=2).annotate(
            video_count=models.Count('video_pages')
        ).order_by('title')
        context['categories'] = categories

        # Все видео
        videos = VideoPage.objects.child_of(self).live().order_by('-date')

        category_id = request.GET.get('category')
        if category_id:
            try:
                videos = videos.filter(category__id=int(category_id), category__section=2)
            except ValueError:
                pass

        context['videos'] = videos
        return context

    class Meta:
        verbose_name = "Индекс видео"


class VideoPage(Page):
    date = models.DateField(
        verbose_name="Дата публикации",
        default = datetime.date(2025, 12, 25)  # ← значение по умолчанию 25 декабря 2025
    )
    intro = models.CharField(max_length=300, blank=True, verbose_name="Краткое описание (под видео)")
    boomstream_code = models.CharField(
        max_length=50,
        default='D6K46zjA',
        verbose_name="Код Boomstream"
    )
    embed_type = models.PositiveSmallIntegerField(
        choices=[
            (1, "Простой iframe в div (рекомендуется)"),
            (2, "Script + span"),
            (3, "Iframe с ?color=false"),
        ],
        default=1,
        verbose_name="Тип эмбеда"
    )
    main_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Превью-изображение"
    )
    views = models.PositiveIntegerField(default=0, editable=False, verbose_name="Просмотры")
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='video_pages',  # для annotate в индексе
        limit_choices_to={'section': 2},  # только видео-категории в админке
        verbose_name="Категория"
    )

    content_panels = Page.content_panels + [
        FieldPanel('date'),
        FieldPanel('category'),
        FieldPanel('main_image'),
        FieldPanel('intro'),
        FieldPanel('boomstream_code'),
        FieldPanel('embed_type'),
    ]

    def serve(self, request):
        # Считаем просмотр один раз за сессию
        session_key = f"viewed_video_{self.id}"
        if not request.session.get(session_key):
            self.views += 1
            self.save(update_fields=['views'])
            request.session[session_key] = True
        return super().serve(request)

    class Meta:
        verbose_name = "Видео"
        ordering = ['-date']