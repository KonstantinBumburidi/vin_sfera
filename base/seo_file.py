"""Общий код для команд export_seo / apply_seo: файл seo/pages.yaml и поиск страниц."""
from pathlib import Path

import yaml
from django.conf import settings
from wagtail.images import get_image_model
from wagtail.models import Page, Site

SEO_FILE = Path(settings.BASE_DIR) / "seo" / "pages.yaml"

# Ключ в файле -> поле страницы
FIELDS = {
    "seo_title": "seo_title",
    "description": "search_description",
    "image": "search_image",
    "noindex": "noindex",
}

# Рекомендуемые длины (символов), дальше поисковики обрезают
TITLE_MAX = 60
DESCRIPTION_MAX = 160

HEADER = """\
# SEO страниц al-sfera.kz — главный источник SEO-данных.
# Правится на ноутбуке, отправляется через git, на сервере применяется:
#   python3 manage.py apply_seo --dry-run   (показать, что изменится)
#   python3 manage.py apply_seo             (записать и опубликовать)
#
# Ключ — адрес страницы. Поля:
#   page:        название страницы, только для справки (не применяется)
#   seo_title:   <title> и заголовок в поиске, до ~60 символов. Пусто — «Название | Сфера Сознания»
#   description: описание в поиске, до ~160 символов
#   image:       картинка для соцсетей — имя файла из «Изображений» (например posv95.jpg) или пусто
#   noindex:     true — скрыть страницу от поисковиков
# Поле, которого нет в записи, не меняется. Страницы, которых нет в файле, не трогаются.
# Правки SEO в админке будут перезаписаны при следующем apply_seo.

"""


def get_site():
    return Site.objects.select_related("root_page").get(is_default_site=True)


def page_key(page, site):
    """Адрес страницы относительно сайта: «/», «/kineziolog/»."""
    root_path = site.root_page.url_path
    return "/" + page.url_path[len(root_path):]


def find_page(key, site):
    root_path = site.root_page.url_path
    url_path = root_path + key.strip("/") + "/" if key.strip("/") else root_path
    return Page.objects.filter(url_path=url_path).first()


def image_key(image):
    return Path(image.file.name).name if image else ""


def find_image(name):
    """Картинка по имени файла (posv95.jpg) или по id."""
    Image = get_image_model()
    if isinstance(name, int) or str(name).isdigit():
        return Image.objects.filter(pk=int(name)).first()
    matches = list(Image.objects.filter(file__endswith=f"/{name}"))
    if len(matches) > 1:
        raise ValueError(f"несколько картинок с именем {name}: id {[i.pk for i in matches]}, укажите id")
    return matches[0] if matches else None


def read_file(path=SEO_FILE):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_file(data, path=SEO_FILE):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(HEADER)
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=1000)
