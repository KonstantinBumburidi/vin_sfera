import json

from django import template
from django.utils.safestring import mark_safe

from base.models import NavigationSettings

register = template.Library()

SITE_URL = "https://al-sfera.kz/"


@register.simple_tag
def organization_jsonld():
    """JSON-LD организации для поисковиков (карточка «организация в Алматы»).

    Адрес и телефон — как в подвале base.html, соцсети — из настроек «Навигация».
    """
    nav = NavigationSettings.load()
    data = {
        "@context": "https://schema.org",
        "@type": "HealthAndBeautyBusiness",
        "@id": SITE_URL + "#organization",
        "name": "Сфера Сознания",
        "description": "Центр космоэнергетики в Алматы: обучение космоэнергетике и световым частотам, "
                       "кинезиология, биорезонансная диагностика.",
        "url": SITE_URL,
        "telephone": "+77776869975",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "ул. Сатпаева, 90/4",
            "addressLocality": "Алматы",
            "addressCountry": "KZ",
        },
        "geo": {
            "@type": "GeoCoordinates",
            "latitude": 43.233155,
            "longitude": 76.875867,
        },
        "sameAs": [
            url for url in (nav.instagram_url, nav.vk_url, nav.facebook_url, nav.telegram_channel_url) if url
        ],
    }
    # Экранируем «<», чтобы текст не мог закрыть тег <script>
    text = json.dumps(data, ensure_ascii=False, indent=2).replace("<", "\\u003c")
    return mark_safe(f'<script type="application/ld+json">\n{text}\n</script>')
