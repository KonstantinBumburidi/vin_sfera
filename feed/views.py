from django.shortcuts import render
from django.views.generic import CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.http import HttpResponse
from wagtail.images import get_image_model
from wagtail.documents import get_document_model

from .models import Post, PostImage, PostDocument
from .forms import PostForm

Image = get_image_model()
Document = get_document_model()


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'feed/post_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['post'] = None  # для шаблона — это создание
        context['title'] = 'Новый пост'
        return context

    def form_valid(self, form):
        form.instance.author = self.request.user
        self.object = form.save()

        # Новые изображения
        for f in self.request.FILES.getlist('images'):
            img = Image(title=f.name, file=f)
            img.save()
            PostImage.objects.create(post=self.object, image=img)

        # Новые документы
        for f in self.request.FILES.getlist('documents'):
            doc = Document(title=f.name, file=f)
            doc.save()
            PostDocument.objects.create(post=self.object, document=doc)

        messages.success(self.request, 'Пост создан!')

        if self.request.headers.get('HX-Request'):
            # Обновляем только список постов
            visible_posts = self.get_visible_posts()
            return render(self.request, 'feed/posts_list.html', {'posts': visible_posts})

        return redirect('feed_page')  # замени на реверс или page.get_url() если нужно

    def get_visible_posts(self):
        posts = Post.objects.all().order_by('-pinned', '-created_at')
        return [p for p in posts if p.is_visible_to(self.request.user)]


class PostUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'feed/post_form.html'

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(author=self.request.user)
        return qs

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['post'] = self.object
        context['title'] = 'Редактировать пост'
        return context

    def form_valid(self, form):
        self.object = form.save()

        # Добавляем новые файлы (аналогично create)
        for f in self.request.FILES.getlist('images'):
            img = Image(title=f.name, file=f)
            img.save()
            PostImage.objects.create(post=self.object, image=img)

        for f in self.request.FILES.getlist('documents'):
            doc = Document(title=f.name, file=f)
            doc.save()
            PostDocument.objects.create(post=self.object, document=doc)

        messages.success(self.request, 'Пост обновлён!')

        if self.request.headers.get('HX-Request'):
            visible_posts = self.get_visible_posts()
            return render(self.request, 'feed/posts_list.html', {'posts': visible_posts})

        return redirect('feed_page')

    def get_visible_posts(self):
        # Тот же метод, что в create
        posts = Post.objects.all().order_by('-pinned', '-created_at')
        return [p for p in posts if p.is_visible_to(self.request.user)]


class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(author=self.request.user)
        return qs

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, 'Пост удалён!')

        if request.headers.get('HX-Request'):
            visible_posts = [p for p in Post.objects.all().order_by('-pinned', '-created_at') if
                             p.is_visible_to(request.user)]
            return render(request, 'feed/posts_list.html', {'posts': visible_posts})

        return redirect('feed_page')


class FileDeleteView(LoginRequiredMixin, View):  # общий для изображений и документов
    model = None  # переопределять в подклассах
    related_model = None  # PostImage или PostDocument

    def post(self, request, pk):
        obj = get_object_or_404(self.related_model, pk=pk, post__author=request.user)
        if self.model:  # Image или Document
            obj.image_or_doc.delete(False)  # удаляем файл
        obj.delete()

        if request.headers.get('HX-Request'):
            return HttpResponse('')  # удаляем блок

        return redirect('feed_page')


class PostImageDeleteView(FileDeleteView):
    model = Image
    related_model = PostImage


class PostDocumentDeleteView(FileDeleteView):
    model = Document
    related_model = PostDocument