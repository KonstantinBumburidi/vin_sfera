"""Загрузка терминов в «Базу знаний» из home/data/glossary.yaml.

    python3 manage.py import_glossary --dry-run   # показать, что будет добавлено
    python3 manage.py import_glossary             # добавить и опубликовать

Добавляет только термины, которых ещё нет на странице (сравнение по названию без
учёта регистра). Существующие термины не меняет и не удаляет.
Введение заменяется, только если оно пустое или осталось заготовкой.
"""
import re
from html import escape
from pathlib import Path

import yaml
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.html import strip_tags

from home.models import GlossaryPage, GlossaryTerm

DATA = Path(__file__).resolve().parents[2] / "data" / "glossary.yaml"
PLACEHOLDER_INTROS = {"", "основные понятия"}
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def to_html(text):
    """Простой текст с [ссылками](/адрес/) → абзац HTML."""
    text = " ".join(str(text).split())
    parts, pos = [], 0
    for m in LINK_RE.finditer(text):
        parts.append(escape(text[pos:m.start()], quote=False))
        parts.append(f'<a href="{escape(m.group(2))}">{escape(m.group(1), quote=False)}</a>')
        pos = m.end()
    parts.append(escape(text[pos:], quote=False))
    return f"<p>{''.join(parts)}</p>"


def norm(s):
    return " ".join(s.lower().replace("ё", "е").split())


class Command(BaseCommand):
    help = "Добавляет термины из home/data/glossary.yaml на страницу «База знаний»"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Только показать, ничего не менять")

    def handle(self, *args, dry_run=False, **opts):
        data = yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}
        terms = data.get("terms") or []
        page = GlossaryPage.objects.first()
        if page is None:
            raise CommandError("Страница «База знаний» не найдена")
        if page.has_unpublished_changes:
            raise CommandError("У страницы «База знаний» есть неопубликованный черновик — опубликуйте или удалите его в админке")

        existing = {norm(t.term) for t in page.terms.all()}
        new = [t for t in terms if norm(t["term"]) not in existing]
        skipped = len(terms) - len(new)
        update_intro = data.get("intro") and norm(strip_tags(page.intro or "")).rstrip(".") in PLACEHOLDER_INTROS

        for t in new:
            self.stdout.write(f"  + {t['term']}")
        self.stdout.write(f"Новых терминов: {len(new)}, уже есть: {skipped}, всего будет: {len(existing) + len(new)}")
        if update_intro:
            self.stdout.write("Введение будет заменено (сейчас пустое или заготовка)")
        if dry_run or not (new or update_intro):
            if dry_run:
                self.stdout.write("Это была проверка (--dry-run). Чтобы записать: python3 manage.py import_glossary")
            return

        with transaction.atomic():
            for t in new:
                page.terms.add(GlossaryTerm(term=t["term"].strip(), definition=to_html(t["definition"])))
            if update_intro:
                page.intro = to_html(data["intro"])
            page.save_revision(log_action=True).publish()
        self.stdout.write(self.style.SUCCESS(f"Готово, страница опубликована: {page.url}"))
