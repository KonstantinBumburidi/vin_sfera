from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, InlinePanel
from django.forms.widgets import CheckboxSelectMultiple

from .models import Post

class PostViewSet(ModelViewSet):
    model = Post
    # Автоматически добавит пункт в боковое меню админки
    menu_label = "Лента новостей"  # название пункта
    menu_icon = "comment"  # иконка (из встроенных Wagtail)
    menu_order = 300  # порядок в меню (после стандартных пунктов)

    icon = "comment"
    list_display = ("author", "created_at", "pinned", "views_count", "likes_count", "comments_count")
    list_per_page = 50
    search_fields = ("content", "author__username", "author__first_name", "author__last_name")

    inspect_view_enabled = True
    inspect_view_fields = ("author", "content", "created_at", "updated_at", "pinned", "visibility_groups")

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("author"),
                FieldPanel("content"),
                FieldPanel("pinned"),
                FieldPanel(
                    "visibility_groups",
                    widget=CheckboxSelectMultiple,
                ),
            ],
            heading="Основное",
        ),
        InlinePanel("images", label="Изображения"),
        InlinePanel("documents", label="Документы"),
    ]

@hooks.register("register_admin_viewset")
def register_post_viewset():
    return PostViewSet("feed_posts", url_prefix="feed/post")