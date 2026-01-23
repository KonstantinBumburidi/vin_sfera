from django.conf import settings
from django.urls import include, path
from django.contrib import admin
from django.views.generic import TemplateView  # ← добавить

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail.contrib.sitemaps.views import sitemap
from home.views import robots_txt
from search import views as search_views

# from django.contrib.sitemaps.views import sitemap as django_sitemap_view
# from home.sitemaps import sitemaps as custom_sitemaps  # ← импорт твоего

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),
    # path('sitemap.xml', django_sitemap_view, {'sitemaps': custom_sitemaps}, name='wagtail_sitemap'),
    path('sitemap.xml', sitemap, name='wagtail_sitemap'),
    path('accounts/', include('allauth.urls')),  # регистрация, логин, логаут и т.д.
    path('feed/', include('feed.urls')),
    path("robots.txt", robots_txt),
    path('yandex_6da6814435e0cb91.html', TemplateView.as_view(
        template_name='yandex_6da6814435e0cb91.html',
        content_type='text/html'
    )),

]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns = urlpatterns + [
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    path("", include(wagtail_urls)),
    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    #    path("pages/", include(wagtail_urls)),
]
