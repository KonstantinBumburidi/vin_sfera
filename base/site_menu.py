"""Главное меню сайта (шапка в base.html).

Меню задано здесь, в коде, а не в админке. Чтобы поменять пункт —
правьте списки ниже, потом git push и деплой (миграции не нужны).

  item(название, ссылка, [подпункты])
  ссылка=None — раздела ещё нет: на сайте пункт НЕ показывается.
                Группа с подпунктами показывается, если в ней есть хоть один готовый пункт.

ВАЖНО: ссылки записаны текстом. Если поменяли адрес (slug) страницы
в админке или через seo/pages.yaml — поменяйте ссылку и здесь.
"""


def item(title, url=None, children=None):
    return {"title": title, "url": url, "children": children or []}


# Строка 1 — центр и практики (крупно)
ROW_1 = [
    item("О нас", "/about_/"),
    item("Космоэнергетика", None, [
        item("Матрицы Архангелов", "/svet_freq/"),
        item("Классические каналы", "/kosmoenergy/"),
        item("Каналы Мая"),                      # планируется
    ]),
    item("Кинезиология", "/kineziolog/"),
    item("Биорезонанс", "/biorezonans/"),
]

# Строка 2 — материалы (мельче, на более тёмной полосе)
ROW_2 = [
    item("Обучение", None, [
        item("Видеоуроки", "/videos/"),
        item("Аудиоуроки", "/materials/audio/"),
    ]),
    item("Шпаргалки", None, [
        item("Поля", "/materials/obolochka/"),
        item("Эмоциональные точки"),             # планируется
    ]),
    item("База знаний", "/baza-znaniy/"),
    item("Библиотека", None, [
        item("Книги", "/materials/books/"),
        item("Статьи", "/materials/blogs/"),
    ]),
    item("Музыка", "/materials/music/"),
    item("Новости", "/novosty/"),
]


def _is_active(url, path):
    return bool(url) and (path == url or path.startswith(url))


def build_row(row, path):
    """Убирает неготовые пункты и отмечает раздел, в котором находится посетитель."""
    result = []
    for it in row:
        children = [
            {**ch, "active": _is_active(ch["url"], path)}
            for ch in it["children"] if ch["url"]
        ]
        if not it["url"] and not children:
            continue
        result.append({
            "title": it["title"],
            "url": it["url"],
            "children": children,
            "active": _is_active(it["url"], path) or any(ch["active"] for ch in children),
        })
    return result


def all_urls():
    """Все ссылки меню — для проверки, что страницы существуют."""
    for it in ROW_1 + ROW_2:
        for x in [it] + it["children"]:
            if x["url"]:
                yield x["title"], x["url"]
