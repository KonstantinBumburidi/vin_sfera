
from django.http import HttpResponse
from django.template import loader

def robots_txt(request):
    template = loader.get_template("robots.txt")
    return HttpResponse(template.render(), content_type="text/plain")
    # return HttpResponse("OK", content_type="text/plain")