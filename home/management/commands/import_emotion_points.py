"""Шпаргалка «Эмоции и точки» из home/data/emotion_points.yaml.

    python3 manage.py import_emotion_points --dry-run   # показать, что будет сделано
    python3 manage.py import_emotion_points             # записать и опубликовать

Если страницы ещё нет — создаёт её внутри «Материалов» (/materials/emocii-i-tochki/).
Таблицу и техники ЗАМЕНЯЕТ содержимым файла. Схемы из home/data/emotion_points/
загружает в «Изображения» (один раз; потом находит их по названию).
"""
from html import escape
from pathlib import Path

import yaml
from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from wagtail.images import get_image_model

from base.seo_file import find_page, get_site
from home.models import EmotionPointRow, EmotionPointsPage, EmotionTechnique, HomePage

DATA = Path(__file__).resolve().parents[2] / "data" / "emotion_points.yaml"
IMAGES_DIR = DATA.parent / "emotion_points"
PARENT_URL = "/materials/"
IMAGE_TITLES = {
    "points_image": "Эмоции и точки — точки 1–14 на теле",
    "meridians_image": "Эмоции и точки — точки меридианов",
}


def paragraphs_html(items):
    return "".join(f"<p>{escape(' '.join(str(p).split()), quote=False)}</p>" for p in items)


class Command(BaseCommand):
    help = "Создаёт/обновляет шпаргалку «Эмоции и точки» из home/data/emotion_points.yaml"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Только показать, ничего не менять")

    def handle(self, *args, dry_run=False, **opts):
        data = yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}
        rows = data.get("rows") or []
        techniques = data.get("techniques") or []
        site = get_site()

        page = EmotionPointsPage.objects.first()
        if page is None:
            parent = find_page(PARENT_URL, site)
            if parent is None or not isinstance(parent.specific, HomePage):
                raise CommandError(f"Не найдена страница {PARENT_URL} («Материалы»)")
            busy = find_page(f"{PARENT_URL}{data['slug']}/", site)
            if busy:
                raise CommandError(f"Адрес {PARENT_URL}{data['slug']}/ уже занят страницей «{busy.title}»")
            self.stdout.write(f"Будет создана страница «{data['title']}»: {PARENT_URL}{data['slug']}/")
        else:
            if page.has_unpublished_changes:
                raise CommandError("У страницы «Эмоции и точки» есть неопубликованный черновик — "
                                   "опубликуйте или удалите его в админке")
            self.stdout.write(f"Будет обновлена страница {page.url}")

        for field, title in IMAGE_TITLES.items():
            name = data.get(field)
            state = "уже есть" if self.find_image(title) else "будет загружена"
            self.stdout.write(f"  схема {name}: {state}")
        self.stdout.write(f"  строк таблицы: {len(rows)}, техник: {len(techniques)}")

        if dry_run:
            self.stdout.write("Это была проверка (--dry-run). Чтобы записать: python3 manage.py import_emotion_points")
            return

        with transaction.atomic():
            images = {field: self.get_or_upload(title, data[field]) for field, title in IMAGE_TITLES.items()}
            if page is None:
                page = EmotionPointsPage(title=data["title"], slug=data["slug"])
                find_page(PARENT_URL, site).specific.add_child(instance=page)
                page = EmotionPointsPage.objects.get(pk=page.pk)

            page.seo_title = data.get("seo_title") or ""
            page.search_description = " ".join((data.get("description") or "").split())
            page.intro = paragraphs_html([data["intro"]]) if data.get("intro") else ""
            page.instruction = " ".join((data.get("instruction") or "").split())
            page.points_image = images["points_image"]
            page.meridians_image = images["meridians_image"]

            page.rows.clear()
            for number, emotions, meridian, hours, muscle in rows:
                page.rows.add(EmotionPointRow(number=number, emotions=emotions, meridian=meridian,
                                              hours=str(hours), muscle=muscle))
            page.techniques.clear()
            for t in techniques:
                page.techniques.add(EmotionTechnique(title=t["title"], text=paragraphs_html(t["paragraphs"])))

            page.save_revision(log_action=True).publish()
        self.stdout.write(self.style.SUCCESS(f"Готово, страница опубликована: {page.url}"))

    def find_image(self, title):
        return get_image_model().objects.filter(title=title).first()

    def get_or_upload(self, title, filename):
        image = self.find_image(title)
        if image:
            return image
        path = IMAGES_DIR / filename
        if not path.exists():
            raise CommandError(f"Нет файла схемы {path}")
        with path.open("rb") as f:
            image = get_image_model()(title=title, file=ImageFile(f, name=filename))
            image.save()
        self.stdout.write(f"  загружена схема {filename}")
        return image
