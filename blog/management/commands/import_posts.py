"""Загрузка статей блога из blog/data/posts/*.md.

    python3 manage.py import_posts --dry-run   # показать, что будет сделано
    python3 manage.py import_posts             # записать и опубликовать

Каждый файл — заметка Obsidian с шапкой:
    ---
    title: "Название"
    slug: adres-stranitsy
    date: 2025-02-10
    ---
    текст...

Статья ищется на сайте по названию (без учёта регистра и «ё»):
- нет такой — создаётся в разделе «Статьи» в категории «Общая» (--category) и публикуется;
- есть, но текст пустой или почти пустой (меньше 200 символов) — текст заменяется;
- есть с текстом — не трогается (заменить всё равно: --update).
Адрес и дата существующих статей не меняются. Статьи с неопубликованным черновиком пропускаются.
"""
import datetime
import re
from html import escape
from pathlib import Path

import yaml
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.html import strip_tags

from blog.models import BlogIndexPage, BlogPage, Category

DATA = Path(__file__).resolve().parents[2] / "data" / "posts"
SHORT_BODY = 200
INTRO_MAX = 250

TAGS_LINE = re.compile(r"^\s*(#[\w-]+\s*)+$")
EMBED = re.compile(r"\.?!\[\[[^\]]*\]\]")
WIKILINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
BOLD = re.compile(r"\*\*(.+?)\*\*")
ITALIC = re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])")
LIST_ITEM = re.compile(r"^\s*[-*•]\s+")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def norm(s):
    return " ".join(s.lower().replace("ё", "е").split())


def inline(text):
    text = escape(text, quote=False)
    text = BOLD.sub(r"<b>\1</b>", text)
    return ITALIC.sub(r"<i>\1</i>", text)


def plain(text):
    return " ".join(BOLD.sub(r"\1", text).replace("*", "").split())


def parse(path):
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        raise CommandError(f"{path.name}: нет шапки --- title/slug/date ---")
    meta = yaml.safe_load(m.group(1)) or {}
    for key in ("title", "slug", "date"):
        if not meta.get(key):
            raise CommandError(f"{path.name}: в шапке нет поля {key}")
    date = meta["date"]
    if not isinstance(date, datetime.date):
        date = datetime.date.fromisoformat(str(date))
    body, intro = to_html(m.group(2))
    return {"file": path.name, "title": str(meta["title"]).strip(), "slug": str(meta["slug"]).strip(),
            "date": date, "body": body, "intro": meta.get("intro") or intro}


def to_html(text):
    """Markdown из Obsidian → HTML для RichTextField. Возвращает (html, текст для intro)."""
    lines = []
    for line in text.split("\n"):
        line = WIKILINK.sub(r"\1", EMBED.sub("", line)).rstrip()
        if TAGS_LINE.match(line):
            continue
        lines.append(line)

    # блоки, разделённые пустыми строками
    blocks, cur = [], []
    for line in lines:
        if line.strip():
            cur.append(line.strip())
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)

    html, intro = [], ""
    for block in blocks:
        # первая строка блока — заголовок: «# …», целиком **жирная** или ЗАГЛАВНЫМИ (короткая)
        line = block[0]
        h = HEADING.match(line)
        letters = re.sub(r"[^A-Za-zА-Яа-яЁё]", "", line)
        if h:
            level = min(max(len(h.group(1)), 2), 4)
            html.append(f"<h{level}>{inline(h.group(2))}</h{level}>")
            block = block[1:]
        elif (BOLD.fullmatch(line) or (letters.isupper() and len(letters) > 3)) and len(line) <= 120:
            html.append(f"<h2>{escape(plain(line), quote=False)}</h2>")
            block = block[1:]
        if not block:
            continue
        # внутри блока: подряд идущие пункты «- » → список, остальное → абзац
        para, items = [], []

        def flush_para():
            if para:
                # строка без знака препинания в конце — это перенос внутри фразы, склеиваем пробелом
                out = inline(para[0])
                for prev, cur in zip(para, para[1:]):
                    out += ("<br/>" if prev[-1] in ".!?:;…»\")" else " ") + inline(cur)
                html.append(f"<p>{out}</p>")
                para.clear()

        def flush_list():
            if items:
                html.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
                items.clear()

        for line in block:
            if LIST_ITEM.match(line):
                flush_para()
                items.append(LIST_ITEM.sub("", line).rstrip(",;"))
            else:
                flush_list()
                para.append(line)
        flush_para()
        flush_list()
        if not intro and not all(LIST_ITEM.match(x) for x in block):
            candidate = plain(" ".join(block))
            if len(candidate) >= 40:
                intro = candidate

    if len(intro) > INTRO_MAX:
        intro = intro[:INTRO_MAX - 1].rsplit(" ", 1)[0].rstrip(",.;:—-– ") + "…"
    return "".join(html), intro


class Command(BaseCommand):
    help = "Загружает статьи блога из blog/data/posts/*.md"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Только показать, ничего не менять")
        parser.add_argument("--update", action="store_true",
                            help="Заменять текст и у тех статей, где он уже есть")
        parser.add_argument("--category", default="Общая", help="Категория для новых статей (по умолчанию «Общая»)")

    def handle(self, *args, dry_run=False, update=False, category="Общая", **opts):
        files = sorted(p for p in DATA.glob("*.md") if not p.name.startswith("_"))
        if not files:
            raise CommandError(f"Нет файлов в {DATA}")
        posts = [parse(p) for p in files]

        index = BlogIndexPage.objects.first()
        if index is None:
            raise CommandError("На сайте нет страницы-списка статей (BlogIndexPage)")
        cat = Category.objects.filter(title__iexact=category, section=1).first()
        if cat is None:
            raise CommandError(f"Нет категории «{category}» в разделе «Блог» — создайте её в админке (Сниппеты → Категории)")

        existing = {norm(p.title): p for p in BlogPage.objects.child_of(index)}
        slugs = set(index.get_children().values_list("slug", flat=True))
        plan = []  # (действие, post, page)
        for post in posts:
            page = existing.get(norm(post["title"]))
            if page is None:
                slug, n = post["slug"], 2
                while slug in slugs:
                    slug, n = f"{post['slug']}-{n}", n + 1
                slugs.add(slug)
                post["slug"] = slug
                plan.append(("new", post, None))
            elif page.has_unpublished_changes:
                plan.append(("draft", post, page))
            elif update or len(strip_tags(page.body or "").strip()) < SHORT_BODY:
                plan.append(("update", post, page))
            else:
                plan.append(("skip", post, page))

        labels = {"new": "+ новая   ", "update": "~ обновить", "skip": "  есть    ", "draft": "! черновик"}
        for action, post, page in plan:
            where = f"{index.url}{post['slug']}/" if action == "new" else page.url
            self.stdout.write(f"{labels[action]} {post['title']}  ({where})")
        counts = {a: sum(1 for x in plan if x[0] == a) for a in labels}
        self.stdout.write(f"Новых: {counts['new']}, обновить текст: {counts['update']}, "
                          f"не трогать: {counts['skip']}, с черновиком (пропуск): {counts['draft']}")
        if counts["skip"] and not update:
            self.stdout.write("Чтобы заменить текст и у статей, где он уже есть: --update")
        if dry_run:
            self.stdout.write("Это была проверка (--dry-run). Чтобы записать: python3 manage.py import_posts")
            return

        with transaction.atomic():
            for action, post, page in plan:
                if action == "new":
                    page = BlogPage(title=post["title"], slug=post["slug"], date=post["date"],
                                    intro=post["intro"], body=post["body"], category=cat)
                    index.add_child(instance=page)
                elif action == "update":
                    page = page.specific
                    page.body = post["body"]
                    if not page.intro:
                        page.intro = post["intro"]
                    if page.category_id is None:
                        page.category = cat
                else:
                    continue
                page.save_revision(log_action=True).publish()
        self.stdout.write(self.style.SUCCESS(f"Готово: создано {counts['new']}, обновлено {counts['update']}"))
