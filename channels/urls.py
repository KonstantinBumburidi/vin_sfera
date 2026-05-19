from django.urls import path
from . import views

app_name = 'channels'

urlpatterns = [
    path('browse_chan/', views.browse_channels, name='browse_channels'),
    path('my_channels/', views.my_channels, name='my_channels'),
    path('toggle_save_channel/<int:channel_id>/', views.toggle_save_channel, name='toggle_save_channel'),
]