from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.template.loader import render_to_string

from channels.models import FChannel, UserSavedChannel


@login_required
def cabinet(request):
    tab = request.GET.get('tab', 'frequencies')
    saved_channels = request.user.saved_channels.select_related(
        'channel', 'channel__group', 'channel__chtype'
    ).order_by('channel__group__sort_order', 'channel__sort_order')

    context = {
        'tab': tab,
        'saved_channels': saved_channels,
    }
    return render(request, 'account/cabinet.html', context)


@login_required
def remove_saved_channel(request, channel_id):
    if request.method != 'POST':
        return HttpResponse(status=405)
    channel = get_object_or_404(FChannel, id=channel_id)
    UserSavedChannel.objects.filter(user=request.user, channel=channel).delete()

    if request.headers.get('HX-Request'):
        return HttpResponse('')

    return redirect('account:cabinet')


@login_required
def update_channel_notes(request, channel_id):
    if request.method != 'POST':
        return HttpResponse(status=405)
    saved = get_object_or_404(UserSavedChannel, user=request.user, channel_id=channel_id)
    saved.notes = request.POST.get('notes', '')
    saved.save()

    if request.headers.get('HX-Request'):
        return HttpResponse('<span class="text-green-600 text-sm">Сохранено</span>')

    return redirect('account:cabinet')