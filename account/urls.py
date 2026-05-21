from django.urls import path
from . import views

app_name = 'account'

urlpatterns = [
    path('', views.cabinet, name='cabinet'),
    path('remove/<int:channel_id>/', views.remove_saved_channel, name='remove_channel'),
    path('notes/<int:channel_id>/', views.update_channel_notes, name='update_notes'),
]