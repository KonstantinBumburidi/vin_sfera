"""Импорт каналов Майя из channels/data/kanaly_maya.md.

Создаёт (если ещё нет) страницу «Каналы Майя» (/kanaly-maya/) с введением,
группы каналов (раздел «Каналы Майя») и сами каналы.

    python3 manage.py import_maya --dry-run   # только показать, что будет
    python3 manage.py import_maya             # импорт
    python3 manage.py import_maya --replace   # удалить старые группы Майя и загрузить заново

Повторный запуск без --replace ничего не ломает: если группы уже есть, команда остановится.
"""
import re
from html import escape
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from channels.models import ChannelGroup, FChannel

SECTION = 3
SLUG = "kanaly-maya"
TITLE = "Каналы Майя"
SEO_TITLE = "Каналы Майя — Космическая Теургия | Сфера сознания"
DESCRIPTION = ("75 каналов Космической Теургии «Майя»: универсальные, чистящие, "
               "оздоровительные, исцеляющие, социальные и защитные. Направление «Сфера сознания» центра «Путь Здоровья», Алматы.")
DATA = Path(__file__).resolve().parents[2] / "data" / "kanaly_maya.md"

CHANNEL_RE = re.compile(r"^-\s*\*\*\s*\d+\.\s*«\s*(.+?)\s*»\s*\*\*\s*[–—-]\s*(.+?)\s*;?\s*$")


def parse(text):
    """Возвращает (абзацы введения, [(группа, [(канал, описание), ...]), ...])."""
    intro, groups = [], []
    in_channels = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            in_channels = True
            continue
        if not in_channels:
            if line:
                intro.append(line)
            continue
        if line.startswith("### "):
            name = line[4:].strip()
            groups.append((name[0].upper() + name[1:], []))
            continue
        m = CHANNEL_RE.match(line)
        if m:
            if not groups:
                raise CommandError(f"Канал вне группы: {line}")
            desc = m.group(2).replace("под питывания", "подпитывания")
            groups[-1][1].append((m.group(1).strip(), desc))
    return intro, groups


def md_inline(s):
    s = escape(s, quote=False)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)


class Command(BaseCommand):
    help = "Импорт каналов Майя из channels/data/kanaly_maya.md"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Только показать, ничего не менять")
        parser.add_argument("--replace", action="store_true", help="Удалить существующие группы Майя и загрузить заново")

    def handle(self, *args, dry_run=False, replace=False, **opts):
        intro, groups = parse(DATA.read_text(encoding="utf-8"))
        total = sum(len(ch) for _, ch in groups)
        for name, channels in groups:
            self.stdout.write(f"{name}: {len(channels)}")
        self.stdout.write(f"Всего групп: {len(groups)}, каналов: {total}, абзацев введения: {len(intro)}")
        if dry_run:
            return

        with transaction.atomic():
            self._import(intro, groups, replace)
        self.stdout.write(self.style.SUCCESS("Готово. Страница: /%s/" % SLUG))

    def _import(self, intro, groups, replace):
        from home.models import ChannelSectionPage, HomePage

        existing = ChannelGroup.objects.filter(section=SECTION)
        if existing.exists():
            if not replace:
                raise CommandError("Группы «Каналы Майя» уже есть. Чтобы загрузить заново: --replace")
            existing.delete()

        for i, (name, channels) in enumerate(groups, start=1):
            g = ChannelGroup.objects.create(title=name, section=SECTION, sort_order=i)
            for j, (ch_name, desc) in enumerate(channels, start=1):
                FChannel.objects.create(group=g, sort_order=j, name=ch_name, description=desc)

        if ChannelSectionPage.objects.filter(section_type=SECTION).exists():
            self.stdout.write("Страница уже есть — не трогаю.")
            return
        home = HomePage.objects.first()
        if home is None:
            raise CommandError("Не найдена главная страница")
        page = ChannelSectionPage(
            title=TITLE,
            slug=SLUG,
            section_type=SECTION,
            seo_title=SEO_TITLE,
            search_description=DESCRIPTION,
            intro="".join(f"<p>{md_inline(p)}</p>" for p in intro),
        )
        home.add_child(instance=page)
        page.save_revision().publish()
        self.stdout.write(f"Создана страница {page.url}")
