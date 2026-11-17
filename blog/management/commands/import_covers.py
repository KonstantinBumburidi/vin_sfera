"""Прикрепляет обложки к статьям блога из blog/data/covers/<slug>.jpg.

    python3 manage.py import_covers --dry-run   # показать, что будет сделано
    python3 manage.py import_covers             # записать и опубликовать

Имя файла = адрес (slug) статьи. Картинка загружается в Wagtail Images
и ставится в «Главное изображение» (main_image) и, если пусто, в картинку для соцсетей
(search_image). У статей, где главное изображение уже есть, ничего не меняется
(заменить всё равно: --force). Статьи с неопубликованным черновиком пропускаются.
"""
from pathlib import Path

from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.images import get_image_model

from blog.models import BlogPage

DATA = Path(__file__).resolve().parents[2] / "data" / "covers"
EXTS = {".jpg", ".jpeg", ".png", ".webp"}


class Command(BaseCommand):
    help = "Прикрепляет обложки из blog/data/covers/ к статьям блога"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Только показать, ничего не менять")
        parser.add_argument("--force", action="store_true", help="Заменять и уже стоящие картинки")

    def handle(self, *args, dry_run=False, force=False, **opts):
        files = sorted(p for p in DATA.glob("*") if p.suffix.lower() in EXTS)
        plan = []
        for path in files:
            page = BlogPage.objects.filter(slug=path.stem).first()
            if page is None:
                self.stdout.write(f"? нет статьи с адресом «{path.stem}» — файл {path.name} пропущен")
            elif page.has_unpublished_changes:
                self.stdout.write(f"! {page.title}: есть неопубликованный черновик — пропуск")
            elif page.main_image_id and not force:
                self.stdout.write(f"  {page.title}: картинка уже есть — не трогаю (заменить: --force)")
            else:
                self.stdout.write(f"+ {page.title}  ← {path.name}")
                plan.append((path, page))
        self.stdout.write(f"Будет прикреплено: {len(plan)}")
        if dry_run:
            self.stdout.write("Это была проверка (--dry-run). Чтобы записать: python3 manage.py import_covers")
            return

        Image = get_image_model()
        with transaction.atomic():
            for path, page in plan:
                page = page.specific
                with path.open("rb") as f:
                    image = Image(title=page.title, file=ImageFile(f, name=f"cover-{path.name}"))
                    image.save()
                page.main_image = image
                if not page.search_image_id or force:
                    page.search_image = image
                page.save_revision(log_action=True).publish()
        self.stdout.write(self.style.SUCCESS(f"Готово: прикреплено {len(plan)}"))
