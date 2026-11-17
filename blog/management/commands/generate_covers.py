"""Генерация обложек для статей блога нейросетью OpenAI — запускать НА НОУТБУКЕ.

    python3 manage.py generate_covers --dry-run          # какие статьи и с каким описанием
    python3 manage.py generate_covers                    # сгенерировать всем статьям без обложки
    python3 manage.py generate_covers --slug intuitsiya  # только одну статью (можно несколько --slug)
    python3 manage.py generate_covers --slug um --force  # перерисовать, даже если обложка уже есть
    python3 manage.py generate_covers --slug um --idea "человек в лабиринте из мыслей, выход к свету"

Картинки сохраняются в blog/data/covers/<адрес-статьи>.jpg (1200×630).
Посмотрите их, неудачные удалите или перегенерируйте, затем git push и на сервере:
    python3 manage.py import_covers

Обложка нужна статьям, у которых нет «Главного изображения» и ещё нет файла в blog/data/covers/.
Перед запуском лучше подтянуть свежую базу: ./scripts/pull_from_prod.sh --no-media
Ключ берётся из .env: OPENAI_API_KEY=sk-proj-...
"""
import base64
import io
import os
import re
import time

import requests
from django.core.management.base import BaseCommand, CommandError
from PIL import Image

from blog.management.commands.import_covers import DATA
from blog.models import BlogPage

API_URL = "https://api.openai.com/v1/images/generations"
MODEL = "gpt-image-2"
GEN_SIZE = (1216, 640)      # стороны должны делиться на 16
OUT_SIZE = (1200, 630)      # стандарт превью для соцсетей
QUALITY = "low"
TEXT_LIMIT = 700            # сколько символов текста статьи показать нейросети

STYLE = (
    "Wide cover illustration for an esoteric spiritual blog. Living, warm and luminous light, "
    "a hint of sacred geometry, jewel colours (violet, turquoise, gold, rose). "
    "Simple clean composition with one clear subject in the centre, few details, soft painterly style, "
    "large calm areas, readable even as a small thumbnail. "
    "No text, no letters, no words, no logos, no watermark."
)


def build_prompt(page, idea=None):
    if idea:
        subject = idea
    else:
        text = " ".join(re.sub(r"<[^>]+>", " ", page.body or "").split())[:TEXT_LIMIT]
        subject = (
            f"Illustrate the meaning of an article titled «{page.title}». "
            + (f"Summary: {page.intro.rstrip('.…')}. " if page.intro else "")
            + (f"Beginning of the article: {text}. " if text else "")
            + "Show it through a symbolic scene (people, nature, light, cosmos), not literally."
        )
    return f"{subject}\n\nStyle: {STYLE}"


class Command(BaseCommand):
    help = "Генерирует обложки статей нейросетью OpenAI в blog/data/covers/ (запуск на ноутбуке)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Только показать, что будет сгенерировано")
        parser.add_argument("--slug", action="append", default=[], help="Только эта статья (адрес); можно несколько")
        parser.add_argument("--force", action="store_true",
                            help="Генерировать, даже если обложка уже есть (на сайте или в папке)")
        parser.add_argument("--idea", help="Своё описание картинки (для одной статьи, вместе с --slug)")
        parser.add_argument("--limit", type=int, default=0, help="Не больше N картинок за запуск")
        parser.add_argument("--quality", default=QUALITY, choices=["low", "medium", "high"],
                            help=f"Качество (по умолчанию {QUALITY})")

    def handle(self, *args, dry_run=False, slug=(), force=False, idea=None, limit=0, quality=QUALITY, **opts):
        if idea and len(slug) != 1:
            raise CommandError("--idea указывается вместе с одним --slug")

        pages = BlogPage.objects.live().order_by("-date")
        if slug:
            pages = pages.filter(slug__in=slug)
            missing = set(slug) - set(pages.values_list("slug", flat=True))
            if missing:
                raise CommandError(f"Нет опубликованных статей с адресом: {', '.join(sorted(missing))}")

        todo = []
        for page in pages:
            path = DATA / f"{page.slug}.jpg"
            if not force and (page.main_image_id or path.exists()):
                continue
            todo.append((page, path))
        if limit:
            todo = todo[:limit]

        if not todo:
            self.stdout.write("Всем статьям обложки уже есть. Перерисовать: --slug <адрес> --force")
            return

        for page, path in todo:
            self.stdout.write(f"• {page.title}  →  blog/data/covers/{path.name}")
            if dry_run:
                self.stdout.write("    " + build_prompt(page, idea).split("\n\nStyle:")[0][:400] + "\n")
        self.stdout.write(f"Картинок: {len(todo)} (качество {quality}, {GEN_SIZE[0]}×{GEN_SIZE[1]})")
        if dry_run:
            self.stdout.write("Это была проверка (--dry-run). Чтобы сгенерировать: уберите --dry-run")
            return

        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            raise CommandError("В .env нет OPENAI_API_KEY")
        if key.startswith("sk-ant"):
            raise CommandError("В OPENAI_API_KEY записан ключ Anthropic (sk-ant-…), нужен ключ OpenAI")

        DATA.mkdir(parents=True, exist_ok=True)
        done = 0
        for page, path in todo:
            started = time.time()
            try:
                img = self.generate(key, build_prompt(page, idea), quality)
            except CommandError as e:
                self.stderr.write(self.style.ERROR(f"  {page.title}: {e}"))
                if "баланс" in str(e) or "ключ" in str(e):
                    break
                continue
            img = img.resize((OUT_SIZE[0], round(img.height * OUT_SIZE[0] / img.width)), Image.LANCZOS)
            top = (img.height - OUT_SIZE[1]) // 2
            img.crop((0, top, OUT_SIZE[0], top + OUT_SIZE[1])).save(path, quality=88, optimize=True)
            done += 1
            self.stdout.write(self.style.SUCCESS(f"  ✓ {page.title} ({time.time() - started:.0f} с)"))

        self.stdout.write(f"Готово: {done} из {len(todo)}. Посмотрите картинки в blog/data/covers/, "
                          f"затем git add/commit/push и на сервере: python3 manage.py import_covers")
        if force:
            self.stdout.write("Если у статьи на сайте обложка уже стоит, на сервере нужен "
                              "import_covers --force (заменит у всех статей, чьи файлы лежат в папке)")

    def generate(self, key, prompt, quality):
        try:
            r = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {key}"},
                json={"model": MODEL, "prompt": prompt, "size": f"{GEN_SIZE[0]}x{GEN_SIZE[1]}",
                      "quality": quality, "n": 1},
                timeout=300,
            )
        except requests.RequestException as e:
            raise CommandError(f"нет связи с OpenAI: {e}")
        if r.status_code != 200:
            try:
                err = r.json()["error"]
            except Exception:
                err = {"message": r.text[:300]}
            code = err.get("code") or ""
            if r.status_code == 401:
                raise CommandError("OpenAI не принял ключ — проверьте OPENAI_API_KEY в .env")
            if "credit" in code or "quota" in code or err.get("type") == "insufficient_quota":
                raise CommandError("на балансе OpenAI нет денег — пополните: "
                                   "https://platform.openai.com/settings/organization/billing/")
            if "moderation" in code or "safety" in code:
                raise CommandError("нейросеть отказалась рисовать по этому описанию — задайте своё через --idea")
            raise CommandError(f"ошибка OpenAI {r.status_code}: {err.get('message', '')[:300]}")
        data = r.json()["data"][0]["b64_json"]
        return Image.open(io.BytesIO(base64.b64decode(data))).convert("RGB")
