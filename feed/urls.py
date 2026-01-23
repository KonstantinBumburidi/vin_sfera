from django.urls import path
from . import views


app_name = 'feed'

urlpatterns = [
    path('post/create/', views.PostCreateView.as_view(), name='post_create'),
    path('post/<int:pk>/update/', views.PostUpdateView.as_view(), name='post_update'),
    path('post/<int:pk>/delete/', views.PostDeleteView.as_view(), name='post_delete'),
    path('image/<int:pk>/delete/', views.PostImageDeleteView.as_view(), name='image_delete'),
    path('document/<int:pk>/delete/', views.PostDocumentDeleteView.as_view(), name='document_delete'),
]