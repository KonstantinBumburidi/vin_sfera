from django.db import models
from django.contrib.auth import get_user_model
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel

from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.snippets.models import register_snippet
from wagtail.fields import RichTextField

User = get_user_model()

# === НОВАЯ МОДЕЛЬ: типы каналов (справочник) ===
@register_snippet
class ChannelType(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название типа канала")
    sort_order = models.IntegerField(default=0, verbose_name="Порядковый номер (для сортировки)")

    panels = [
        FieldPanel('name'),
        FieldPanel('sort_order'),
    ]

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = "Тип канала"
        verbose_name_plural = "Типы каналов"


@register_snippet
class ChannelGroup(ClusterableModel):
    SECTION_CHOICES = [
        (1, "Световые частоты"),
        (2, "Космоэнергетика"),
    ]

    title = models.CharField(max_length=200, verbose_name="Название группы (Матрица / Блок)")
    description = models.TextField(blank=True, verbose_name="Короткое описание группы")
    image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Изображение (значок группы)"
    )
    section = models.PositiveSmallIntegerField(
        choices=SECTION_CHOICES,
        verbose_name="Раздел"
    )
    sort_order = models.IntegerField(default=0, verbose_name="Порядковый номер группы")

    panels = [
        FieldPanel('title'),
        FieldPanel('description'),
        FieldPanel('image'),
        FieldPanel('section'),
        FieldPanel('sort_order'),
        InlinePanel('channels', label="Каналы / Частоты"),
    ]

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['sort_order', 'title']


class FChannel(models.Model):
    group = ParentalKey(
        'channels.ChannelGroup',
        on_delete=models.CASCADE,
        related_name='channels'
    )
    sort_order = models.IntegerField(default=0, verbose_name="Порядковый номер")
    name = models.CharField(max_length=200, verbose_name="Название канала / частоты")
    description = models.TextField(blank=True, verbose_name="Короткое описание (для таблицы)")
    content = RichTextField(blank=True, verbose_name="Полное содержание (раскрываемый текст)")

    # === НОВОЕ ПОЛЕ: тип канала ===
    chtype = models.ForeignKey(
        'channels.ChannelType',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Тип канала"
    )

    panels = [
        FieldPanel('sort_order'),
        FieldPanel('name'),
        FieldPanel('description'),
        FieldPanel('content'),
        FieldPanel('chtype'),  # ← добавили в панели
    ]

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['sort_order']
        verbose_name = "Канал / Частота"
        verbose_name_plural = "Каналы / Частоты"

class UserSavedChannel(models.Model):
    """
    Сохранённые (избранные) каналы пользователя.
    Позволяет пользователю создавать свой список каналов для быстрого доступа.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_channels',
        verbose_name="Пользователь"
    )
    channel = models.ForeignKey(
        'channels.FChannel',
        on_delete=models.CASCADE,
        related_name='saved_by_users',
        verbose_name="Канал"
    )
    notes = models.TextField(blank=True, verbose_name="Заметки пользователя")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Добавлено")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Сохранённый канал"
        verbose_name_plural = "Сохранённые каналы"
        ordering = ['-created_at']
        unique_together = ['user', 'channel']  # Один канал - одна запись на пользователя

    def __str__(self):
        return f"{self.user} → {self.channel}"