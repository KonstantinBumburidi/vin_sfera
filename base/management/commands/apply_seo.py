from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from base.seo import SeoPageMixin
from base.seo_file import (
    DESCRIPTION_MAX, FIELDS, SEO_FILE, TITLE_MAX,
    find_image, find_page, get_site, image_key, read_file,
)


class Command(BaseCommand):
    help = "Записывает SEO-поля из seo/pages.yaml в страницы и публикует их"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Только показать изменения, ничего не записывать",
        )
        parser.add_argument(
            "--force", action="store_true",
            help="Применять и к страницам с неопубликованным черновиком (черновик будет заменён)",
        )

    def handle(self, *args, **options):
        if not SEO_FILE.exists():
            raise CommandError(f"Нет файла {SEO_FILE}")
        data = read_file()
        site = get_site()
        dry_run = options["dry_run"]
        stats = {"changed": 0, "same": 0, "skipped": 0, "errors": 0}

        for key, entry in data.items():
            entry = entry or {}
            page = find_page(key, site)
            if page is None:
                self.stdout.write(self.style.ERROR(f"{key}: страница не найдена"))
                stats["errors"] += 1
                continue
            page = page.specific
            if not isinstance(page, SeoPageMixin):
                self.stdout.write(self.style.ERROR(f"{key}: у этого типа страницы нет SEO-полей"))
                stats["errors"] += 1
                continue

            try:
                changes = self.get_changes(page, entry)
            except ValueError as e:
                self.stdout.write(self.style.ERROR(f"{key}: {e}"))
                stats["errors"] += 1
                continue

            self.warn_lengths(key, page, changes)
            if not changes:
                stats["same"] += 1
                continue

            self.stdout.write(f"{key}  ({page.title})")
            for field, (old, new) in changes.items():
                self.stdout.write(f"    {field}: {self.show(old)}  ->  {self.show(new)}")

            if page.has_unpublished_changes and not options["force"]:
                self.stdout.write(self.style.WARNING(
                    f"    пропущено: у страницы есть неопубликованный черновик (опубликуйте его или добавьте --force)"
                ))
                stats["skipped"] += 1
                continue

            if not dry_run:
                try:
                    self.save(page, changes)
                except ValidationError as e:
                    self.stdout.write(self.style.ERROR(f"    ошибка сохранения: {e}"))
                    stats["errors"] += 1
                    continue
            stats["changed"] += 1

        verb = "будет изменено" if dry_run else "изменено и опубликовано"
        self.stdout.write(self.style.SUCCESS(
            f"Страниц {verb}: {stats['changed']}, без изменений: {stats['same']}, "
            f"пропущено: {stats['skipped']}, ошибок: {stats['errors']}"
        ))
        if dry_run and stats["changed"]:
            self.stdout.write("Это была проверка (--dry-run). Чтобы записать: python3 manage.py apply_seo")

    def get_changes(self, page, entry):
        """{поле страницы: (старое, новое)} только для отличающихся значений."""
        changes = {}
        for key, field in FIELDS.items():
            if key not in entry:
                continue
            value = entry[key]
            old = getattr(page, field)
            if key == "image":
                new = find_image(value) if value not in (None, "") else None
                if value not in (None, "") and new is None:
                    raise ValueError(f"картинка «{value}» не найдена в «Изображениях»")
                if (old.pk if old else None) != (new.pk if new else None):
                    changes[field] = (old, new)
            elif key == "noindex":
                new = bool(value)
                if old != new:
                    changes[field] = (old, new)
            else:
                new = " ".join(str(value or "").split())
                if " ".join((old or "").split()) != new:
                    changes[field] = (old, new)
        return changes

    def warn_lengths(self, key, page, changes):
        title = changes["seo_title"][1] if "seo_title" in changes else page.seo_title
        desc = changes["search_description"][1] if "search_description" in changes else page.search_description
        if title and len(title) > TITLE_MAX:
            self.stdout.write(self.style.WARNING(f"{key}: seo_title {len(title)} символов (рекомендуется до {TITLE_MAX})"))
        if desc and len(desc) > DESCRIPTION_MAX:
            self.stdout.write(self.style.WARNING(f"{key}: description {len(desc)} символов (рекомендуется до {DESCRIPTION_MAX})"))

    @transaction.atomic
    def save(self, page, changes):
        for field, (_old, new) in changes.items():
            setattr(page, field, new)
        # Новая ревизия + публикация: в админке и истории страницы будет видно изменение
        page.save_revision(log_action=True).publish()

    def show(self, value):
        if value is None or value == "":
            return "(пусто)"
        if hasattr(value, "file"):
            return image_key(value)
        return repr(value) if isinstance(value, str) else str(value)
