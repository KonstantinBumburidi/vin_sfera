# channels/views.py (если нет, создайте)
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from .models import FChannel, ChannelGroup, ChannelType, UserSavedChannel
import django_filters

class ChannelFilter(django_filters.FilterSet):
    group = django_filters.ModelChoiceFilter(
        queryset=ChannelGroup.objects.all(),
        label="Группа (Матрица / Блок)",
        empty_label="Все группы"
    )
    chtype = django_filters.ModelChoiceFilter(
        queryset=ChannelType.objects.all(),
        label="Тип канала",
        empty_label="Все типы"
    )

    class Meta:
        model = FChannel
        fields = ['group', 'chtype']

def browse_channels(request):
    filter_set = ChannelFilter(request.GET, queryset=FChannel.objects.all().order_by('group__sort_order', 'sort_order'))
    channels = filter_set.qs
    groups = ChannelGroup.objects.all().order_by('sort_order')
    types = ChannelType.objects.all().order_by('sort_order')

    # Для авторизованных: получить сохранённые
    saved_channels = set()
    if request.user.is_authenticated:
        saved_channels = set(request.user.saved_channels.values_list('channel_id', flat=True))

    context = {
        'filter': filter_set,
        'channels': channels,
        'groups': groups,
        'types': types,
        'saved_channels': saved_channels,
    }
    return render(request, 'channels/browse_chan.html', context)

@login_required
def my_channels(request):
    saved = request.user.saved_channels.all().order_by('-created_at')
    context = {
        'saved_channels': saved,
    }
    return render(request, 'channels/my_channels.html', context)

@login_required
def toggle_save_channel(request, channel_id):
    if request.method != 'POST':
        return HttpResponse(status=405)

    channel = get_object_or_404(FChannel, id=channel_id)

    if 'update_notes' in request.POST:
        saved = get_object_or_404(UserSavedChannel, user=request.user, channel=channel)
        saved.notes = request.POST.get('notes', '')
        saved.save()
        return redirect('channels:my_channels')

    saved, created = UserSavedChannel.objects.get_or_create(user=request.user, channel=channel)
    if not created:
        saved.delete()
        action = 'removed'
    else:
        action = 'added'

    # Для HTMX: возвращаем обновлённый HTML кнопки
    if request.headers.get('HX-Request'):
        saved_channels = set(request.user.saved_channels.values_list('channel_id', flat=True))
        html = render_to_string('channels/_toggle_button.html', {
            'channel': channel,
            'is_saved': channel.id in saved_channels,
        }, request=request)
        return HttpResponse(html)

    return redirect('channels:browse_channels')
