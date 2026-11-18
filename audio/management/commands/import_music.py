"""Загрузка треков на страницу «Музыка» по списку audio/data/music.yaml.

    python3 manage.py import_music --source ~/music_upload --dry-run
    python3 manage.py import_music --source ~/music_upload
    python3 manage.py import_music --source ~/music_upload --remove-test   # и убрать «Пробный трек …»

--source — папка с mp3 (сами mp3 в git не хранятся, их копируют на сервер через scp).
Каждый mp3 загружается в Wagtail «Документы» (файл ляжет в media/documents/),
для него создаётся и публикуется страница трека. Трек, который уже есть на странице
(по названию), не трогается. После загрузки папку --source можно удалить.
"""
import datetime
import re
from html import escape
from pathlib import Path

import yaml
from anyascii import anyascii
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from wagtail.documents import get_document_model

from audio.models import MusicIndexPage, MusicPage

DATA = Path(__file__).resolve().parents[2] / "data" / "music.yaml"
TEST_PREFIX = "пробный трек"


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", anyascii(text.replace("ь", "").replace("ъ", "")).lower()).strip("-")


def norm(s):
    return " ".join(s.lower().replace("ё", "е").split())


class Command(BaseCommand):
    help = "Загружает треки из audio/data/music.yaml на страницу «Музыка»"

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True, help="Папка с mp3-файлами")
        parser.add_argument("--dry-run", action="store_true", help="Только показать, ничего не менять")
        parser.add_argument("--remove-test", action="store_true",
                            help="Удалить страницы «Пробный трек …» (сами аудиофайлы в «Документах» остаются)")

    def handle(self, *args, source, dry_run=False, remove_test=False, **opts):
        tracks = (yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}).get("tracks") or []
        src = Path(source).expanduser()
        index = MusicIndexPage.objects.first()
        if index is None:
            raise CommandError("На сайте нет страницы «Музыка» (MusicIndexPage)")

        existing = {norm(p.title) for p in MusicPage.objects.child_of(index)}
        slugs = set(index.get_children().values_list("slug", flat=True))
        new, errors = [], 0
        for t in tracks:
            title = str(t["title"]).strip()
            if norm(title) in existing:
                self.stdout.write(f"  есть      {title}")
                continue
            path = src / t["file"]
            if not path.is_file():
                self.stdout.write(self.style.ERROR(f"  нет файла {path}"))
                errors += 1
                continue
            slug = slugify(title) or "track"
            base, n = slug, 2
            while slug in slugs:
                slug, n = f"{base}-{n}", n + 1
            slugs.add(slug)
            new.append((t, title, slug, path))
            self.stdout.write(f"+ новый     {title}  ({index.url}{slug}/, {t.get('duration', '')}, "
                              f"{path.stat().st_size / 1e6:.0f} МБ)")

        tests = MusicPage.objects.child_of(index).filter(title__istartswith=TEST_PREFIX) if remove_test else []
        for p in tests:
            self.stdout.write(f"- удалить   {p.title}  ({p.url})")

        self.stdout.write(f"Новых треков: {len(new)}, удалить пробных: {len(tests)}, ошибок: {errors}")
        if errors:
            raise CommandError("Не все файлы найдены — проверьте папку --source")
        if dry_run:
            self.stdout.write("Это была проверка (--dry-run). Чтобы записать: уберите --dry-run")
            return

        saved_files = []
        try:
            self.write(tests, new, index, saved_files)
        except Exception:
            # база откатилась — убираем уже скопированные mp3, чтобы не остались лишние файлы
            for doc_file in saved_files:
                doc_file.storage.delete(doc_file.name)
            raise
        self.stdout.write(self.style.SUCCESS(f"Готово: добавлено {len(new)}, удалено пробных {len(tests)}"))

    def write(self, tests, new, index, saved_files):
        Document = get_document_model()
        today = datetime.date.today()
        with transaction.atomic():
            for p in tests:
                p.delete()
            index = MusicIndexPage.objects.get(pk=index.pk)  # после удаления — свежие данные дерева страниц
            # новые треки получают одну дату; порядок на странице — по названию
            for t, title, slug, path in new:
                with path.open("rb") as f:
                    doc = Document(title=title, file=File(f, name=f"{slug}.mp3"))
                    doc.save()
                saved_files.append(doc.file)
                intro = str(t.get("intro") or "").strip()
                page = MusicPage(
                    title=title, slug=slug, date=today,
                    duration=str(t.get("duration") or ""),
                    intro=f"<p>{escape(intro, quote=False)}</p>" if intro else "",
                    audio_file=doc,
                )
                index.add_child(instance=page)
                page.save_revision(log_action=True).publish()
                self.stdout.write(f"  ✓ {title}")
