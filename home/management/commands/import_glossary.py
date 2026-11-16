"""Загрузка терминов в «Базу знаний» из home/data/glossary.yaml.

    python3 manage.py import_glossary --dry-run   # показать, что будет добавлено
    python3 manage.py import_glossary             # добавить и опубликовать

Добавляет только термины, которых ещё нет на странице (сравнение по названию без
учёта регистра). Существующие термины не меняет и не удаляет.
Введение заменяется, только если оно пустое или осталось заготовкой.

Если страницы-словаря на сайте ещё нет, добавьте --create-page: команда создаст её
по адресу /baza-znaniy/. Если этот адрес занят другой страницей, та будет снята
с публикации и переименована в /baza-znaniy-old/ (не удаляется).
"""
import re
from html import escape
from pathlib import Path

import yaml
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.html import strip_tags

from base.seo_file import find_page, get_site
from home.models import GlossaryPage, GlossaryTerm, HomePage

SLUG = "baza-znaniy"
OLD_SLUG = "baza-znaniy-old"
TITLE = "База знаний"
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
        parser.add_argument("--create-page", action="store_true",
                            help="Создать страницу-словарь /baza-znaniy/, если её ещё нет")

    def handle(self, *args, dry_run=False, create_page=False, **opts):
        data = yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}
        terms = data.get("terms") or []
        page = GlossaryPage.objects.first()
        if page is None:
            if not create_page:
                raise CommandError(
                    "Страницы-словаря «База знаний» на сайте нет. "
                    "Чтобы создать её, добавьте --create-page (сначала с --dry-run)"
                )
            page = self.create_page(dry_run)
            if dry_run:
                self.report(terms, set(), True, dry_run)
                return
        if page.has_unpublished_changes:
            raise CommandError("У страницы «База знаний» есть неопубликованный черновик — опубликуйте или удалите его в админке")

        existing = {norm(t.term) for t in page.terms.all()}
        new = [t for t in terms if norm(t["term"]) not in existing]
        skipped = len(terms) - len(new)
        update_intro = data.get("intro") and norm(strip_tags(page.intro or "")).rstrip(".") in PLACEHOLDER_INTROS

        self.report(terms, existing, update_intro, dry_run)
        if dry_run or not (new or update_intro):
            return

        with transaction.atomic():
            for t in new:
                page.terms.add(GlossaryTerm(term=t["term"].strip(), definition=to_html(t["definition"])))
            if update_intro:
                page.intro = to_html(data["intro"])
            page.save_revision(log_action=True).publish()
        self.stdout.write(self.style.SUCCESS(f"Готово, страница опубликована: {page.url}"))

    def report(self, terms, existing, update_intro, dry_run):
        new = [t for t in terms if norm(t["term"]) not in existing]
        for t in new:
            self.stdout.write(f"  + {t['term']}")
        self.stdout.write(f"Новых терминов: {len(new)}, уже есть: {len(terms) - len(new)}, "
                          f"всего будет: {len(existing) + len(new)}")
        if update_intro:
            self.stdout.write("Введение будет заменено (сейчас пустое или заготовка)")
        if dry_run:
            flags = " --create-page" if not GlossaryPage.objects.exists() else ""
            self.stdout.write(f"Это была проверка (--dry-run). Чтобы записать: python3 manage.py import_glossary{flags}")

    def create_page(self, dry_run):
        """Создаёт пустую страницу-словарь на месте /baza-znaniy/."""
        site = get_site()
        old = find_page(f"/{SLUG}/", site)
        parent = old.get_parent().specific if old else site.root_page.specific
        if not isinstance(parent, HomePage):
            parent = HomePage.objects.first()
        if old:
            self.stdout.write(f"Адрес /{SLUG}/ занят страницей «{old.title}» ({old.specific_class.__name__}): "
                              f"она будет снята с публикации и переименована в /{OLD_SLUG}/")
        self.stdout.write(f"Будет создана страница-словарь «{TITLE}» по адресу /{SLUG}/")
        if dry_run:
            return None
        with transaction.atomic():
            seo = {}
            if old:
                old = old.specific
                seo = {"seo_title": old.seo_title, "search_description": old.search_description}
                if old.live:
                    old.unpublish(log_action=True)
                old.slug = OLD_SLUG
                old.save()
                self.drop_redirects()
            page = GlossaryPage(title=TITLE, slug=SLUG, intro="", **seo)
            parent.add_child(instance=page)
            page.save_revision(log_action=True).publish()
            self.drop_redirects()
        self.stdout.write(self.style.SUCCESS(f"Создана страница {page.url}"))
        return GlossaryPage.objects.get(pk=page.pk)  # свежая копия из базы, после публикации

    def drop_redirects(self):
        """Wagtail мог сам создать переадресацию со старого адреса — она не нужна."""
        try:
            from wagtail.contrib.redirects.models import Redirect
        except ImportError:
            return
        Redirect.objects.filter(old_path__in=[f"/{SLUG}", f"/{SLUG}/"]).delete()
