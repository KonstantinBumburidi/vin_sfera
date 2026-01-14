from django.db import models

from wagtail.admin.panels import (
    FieldPanel,
    MultiFieldPanel,
)
from wagtail.contrib.settings.models import (
    BaseGenericSetting,
    register_setting,
)
from wagtail.images.models import Image

@register_setting
class NavigationSettings(BaseGenericSetting):
    # Ссылки
    vk_url = models.URLField(blank=True, verbose_name="VK")
    facebook_url = models.URLField(blank=True, verbose_name="Facebook")
    instagram_url = models.URLField(blank=True, verbose_name="Instagram")

    # Иконки (из медиа-галереи Wagtail)
    vk_icon = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Иконка VK (PNG)"
    )
    facebook_icon = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Иконка Facebook (PNG)"
    )
    instagram_icon = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Иконка Instagram (PNG)"
    )

    # Остальные поля (телефон, email)
    phone = models.CharField(max_length=30, blank=True, verbose_name="Телефон")
    email = models.EmailField(blank=True, verbose_name="Email")

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("vk_url"),
                FieldPanel("vk_icon"),
                FieldPanel("facebook_url"),
                FieldPanel("facebook_icon"),
                FieldPanel("instagram_url"),
                FieldPanel("instagram_icon"),
            ],
            heading="Социальные сети",
        ),
        MultiFieldPanel(
            [
                FieldPanel("phone"),
                FieldPanel("email"),
            ],
            heading="Контакты",
        ),
    ]

