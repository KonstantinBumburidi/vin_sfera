from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericRelation
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.images.models import Image
from wagtail.documents.models import Document

from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel
# from .models import Post  # уже есть импорт выше
from wagtailmetadata.models import MetadataPageMixin

User = get_user_model()

# Расширение профиля пользователя (WhatsApp понадобится позже)
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='feed_profile')
    whatsapp_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="В международном формате, например +77001234567"
    )
    whatsapp_notifications = models.BooleanField(default=False)

    def __str__(self):
        return f"Профиль {self.user.username}"

    class Meta:
        verbose_name = "Профиль пользователя для ленты"
        verbose_name_plural = "Профили пользователей для ленты"


# Пост в ленте
class Post(ClusterableModel):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feed_posts')
    content = models.TextField(verbose_name="Текст поста")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    # Закреплённый пост (только админы/модераторы смогут ставить)
    pinned = models.BooleanField(default=False, verbose_name="Закреплённый")

    # Видимость: если группы не указаны — видно всем залогиненным пользователям
    # Если указаны группы — видно только членам этих групп
    visibility_groups = models.ManyToManyField(
        Group,
        blank=True,
        verbose_name="Видно только для групп",
        help_text="Если не выбрано — видно всем авторизованным пользователям"
    )

    # Счётчики (лайки и комментарии добавим позже, пока заглушки)
    views_count = models.PositiveIntegerField(default=0, verbose_name="Просмотры")
    likes_count = models.PositiveIntegerField(default=0, editable=False)
    comments_count = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ['-pinned', '-created_at']
        verbose_name = "Пост в ленте"
        verbose_name_plural = "Посты в ленте"

    def __str__(self):
        return f"Пост {self.author} от {self.created_at.date()}"

    # Проверка видимости для конкретного пользователя
    def is_visible_to(self, user):
        if not user.is_authenticated:
            return False
        if not self.visibility_groups.exists():
            return True
        return self.visibility_groups.filter(user=user).exists()


# Изображения к посту (через Wagtail)
class PostImage(models.Model):
    post = ParentalKey(Post, on_delete=models.CASCADE, related_name='images')
    image = models.ForeignKey(Image, on_delete=models.PROTECT, related_name='+')

    class Meta:
        verbose_name = "Изображение поста"
        verbose_name_plural = "Изображения поста"


# Документы к посту (через Wagtail)
class PostDocument(models.Model):
    post = ParentalKey(Post, on_delete=models.CASCADE, related_name='documents')
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name='+')

    class Meta:
        verbose_name = "Документ поста"
        verbose_name_plural = "Документы поста"



class FeedPage(MetadataPageMixin, Page):
    intro = RichTextField(blank=True, verbose_name="Вступительный текст (над лентой)")

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    subpage_types = []  # если не планируем дочерние страницы внутри ленты

    # Фильтрация постов по видимости
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)

        # Все посты, отсортированные (закреплённые сверху)
        posts = Post.objects.all().order_by('-pinned', '-created_at')

        if request.user.is_authenticated:
            # Фильтруем только видимые для текущего пользователя
            visible_posts = [post for post in posts if post.is_visible_to(request.user)]

            # Увеличиваем счётчик просмотров для каждого видимого поста
            for post in visible_posts:
                post.views_count += 1
                post.save(update_fields=['views_count'])
        else:
            visible_posts = []

        context["posts"] = visible_posts
        context["feed_page"] = self  # если понадобится в шаблоне
        return context