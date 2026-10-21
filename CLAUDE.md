# vin_sfera — сайт центра «Сфера Сознания» (https://al-sfera.kz)

Центр космоэнергетики в Алматы: космоэнергетика, световые частоты, кинезиология,
биорезонансная диагностика. Сайт на Wagtail, контент на русском.

## Общение
- Отвечать по-русски.
- В командах писать `python3`, не `python`.
- Владелец — не профессиональный разработчик: объяснять шаги конкретно, с готовыми командами.

## Стек
- Django 6.0, Wagtail 7.4.3 LTS, wagtailmenus 4.1.1, modelsearch 1.3.2, django-allauth
- PostgreSQL 16 на сервере (на ноутбуке 17). Раньше была MySQL — переехали в октябре 2026.
- Настройки: `vin_sfera/settings/{base,dev,production}.py`; БД берётся из `.env` (шаблон — `.env.example`, сам `.env` в git не попадает).

## Приложения
- `home` — основные страницы сайта (главная, разделы, книги, архангелы и т. п.)
- `blog`, `audio`, `videos` — материалы
- `base` — общие вещи: SEO (`seo.py`, `seo_file.py`, команды `export_seo`/`apply_seo`, тег `templatetags/seo_tags.py`)
- `channels`, `feed`, `account` — личный кабинет, каналы, лента
- `spblock`, `search`
- Шаблоны сайта: `vin_sfera/templates/` (`base.html`, `includes/seo_meta.html`)

## Где что работает
- **Ноутбук** — разработка. Код идёт ноутбук → GitHub → сервер.
- **Сервер** — Ubuntu 24.04, проект в `~/vin_sfera/vin_sfera`, venv `~/vin_sfera/sfe_envir`,
  systemd-сервис `vin_sfera`, nginx (http и www → 301 на https://al-sfera.kz).
- Свежая копия базы и media с сервера на ноутбук: `./scripts/pull_from_prod.sh` (`--no-media` — только база).
- Сервер работает на `settings.dev` (так по умолчанию в `manage.py` и `wsgi.py`). Отличия сервера задаются:
  - `vin_sfera/settings/local.py` (не в git, подключается в конце `dev.py`) — там `DEBUG = False`;
  - `.env` — БД и `WAGTAILADMIN_BASE_URL=https://al-sfera.kz`.
- static и media раздаёт nginx, страницы ошибок — `templates/404.html`, `500.html`.
  Ошибки сайта смотреть в журнале: `sudo journalctl -u vin_sfera -n 100`.
- Не сделано: `SECRET_KEY` из `dev.py` лежит в git — на сервере нужен свой ключ из `.env`;
  `ALLOWED_HOSTS = ["*"]` — лучше `["al-sfera.kz"]`. В идеале перевести сервер на `settings.production`.

## Деплой на сервер
```bash
cd ~/vin_sfera/vin_sfera
source ../sfe_envir/bin/activate
git pull
python3 manage.py migrate            # если были новые миграции
python3 manage.py collectstatic --noinput   # если менялась статика
sudo systemctl restart vin_sfera
```
- **Никогда не делать `makemigrations` на сервере** — миграции создаются только на ноутбуке и приходят через git.
- Перед пушем проверять `git status`: новые файлы (например, templatetags) легко забыть добавить,
  а без них сайт падает с ошибкой 500.

## SEO
- Мета-теги — собственные (wagtail-metadata удалён): `base/seo.py` → `SeoPageMixin` на всех моделях страниц
  (картинка для соцсетей `search_image`, флажок noindex; страницы видео/аудио всегда noindex),
  вывод — `templates/includes/seo_meta.html`.
- Картинка для соцсетей по умолчанию: `DEFAULT_SEO_IMAGE` в `base/seo.py` (имя файла в Wagtail Images).
  Сейчас `posv95.jpg` — она 769×403, лучше заменить на ≥1200×630.
- JSON-LD организации (адрес ул. Сатпаева 90/4, координаты 43.233155, 76.875867): `base/templatetags/seo_tags.py`.
- Тексты SEO (title, description, slug) хранятся в `seo/pages.yaml` — это главный источник:
  1. на ноутбуке `python3 manage.py export_seo` (по свежей копии базы с сервера);
  2. правка `seo/pages.yaml` → git push;
  3. на сервере `python3 manage.py apply_seo --dry-run`, потом `apply_seo`
     (публикует ревизии; страницы с черновиками пропускает, если нет `--force`).
- `sitemap.xml` отдаёт Wagtail динамически. Файла `vin_sfera/templates/sitemap.xml` быть не должно —
  он перекроет динамический sitemap.
- `robots.txt` закрывает `/admin/`, `/django-admin/`, `/search/`, `/documents/download/`, `/accounts/`, `/cabinet/`.
- Сайт добавлен в Google Search Console и Яндекс Вебмастер.

## Миграция данных между базами (если понадобится снова)
- dumpdata без `contenttypes`, `auth.permission`, `sessions`, `wagtailsearch.indexentry`.
- После `migrate` на пустой базе удалить созданную Wagtail страницу «Welcome» и Site
  (`Page.objects.filter(depth__gt=1).delete()`, `Site.objects.all().delete()`), потом loaddata и `update_index`.
