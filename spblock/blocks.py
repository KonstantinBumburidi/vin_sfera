from wagtail.blocks import (
    StructBlock, CharBlock, RichTextBlock, BooleanBlock
)
from wagtail.images.blocks import ImageChooserBlock
from wagtail.blocks import PageChooserBlock


# -----------------------------------------------------------------------------------
# структурные блоки
class HeroBlock(StructBlock):
    title = CharBlock(required=True, label="Заголовок")
    image = ImageChooserBlock(required=True, label="Фоновое изображение")

    class Meta:
        template = "home/blocks/hero.html"
        icon = "image"
        label = "Герой-блок"

# теккст и изображение
class TextImageBlock(StructBlock):
    anchor = CharBlock(
        required=False,
        max_length=54,
        label="Якорь (ID для ссылок)",
        help_text="Уникальный идентификатор только из латиницы, цифр, дефисов и подчёркиваний."
    )
    title = CharBlock(required=True, label="Заголовок раздела")
    text = RichTextBlock(required=True, label="Текст (слева)")
    image = ImageChooserBlock(required=True, label="Изображение (справа)")
    show_button = BooleanBlock(required=False, default=False, label="Показывать кнопку «Подробнее»")
    button_text = CharBlock(default="Подробнее", required=False, label="Текст кнопки")
    button_page = PageChooserBlock(required=False, label="Ссылка на страницу")

    class Meta:
        template = "home/blocks/text_image.html"
        icon = "grip"
        label = "Текст + изображение"

# только текст
class TextOnlyBlock(StructBlock):
    anchor = CharBlock(
        required=False,
        max_length=54,
        label="Якорь (ID для ссылок)",
        help_text="Уникальный идентификатор только из латиницы, цифр, дефисов и подчёркиваний."
    )
    title = CharBlock(required=False, label="Заголовок")
    description = RichTextBlock(required=False, label="Короткое описание (подзаголовок)")
    content = RichTextBlock(required=True, label="Основной текст")

    class Meta:
        template = "home/blocks/text_only.html"
        icon = "doc-full"
        label = "Текст (без изображения)"

# полноширинная кнопка
class WidthButtonBlock(StructBlock):
    button_text = CharBlock(required=True, label="Текст кнопки")
    link_page = PageChooserBlock(required=True, label="Ссылка на страницу")

    class Meta:
        template = "home/blocks/width_button.html"
        icon = "arrow-right"
        label = "Полноширинная кнопка"
