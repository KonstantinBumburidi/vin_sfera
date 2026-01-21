
from django.http import HttpResponse
from django.conf import settings
from django.template.loader import render_to_string

def robots_txt(request):
    content = render_to_string(
        "robots.txt",
        {
            "debug": settings.DEBUG,
            "sitemap_url": request.build_absolute_uri("/sitemap.xml"),
            # "host": request.get_host().split(":")[0],
        },
    )
    return HttpResponse(content, content_type="text/plain")