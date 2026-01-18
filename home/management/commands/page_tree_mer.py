# home/management/commands/show_page_tree.py
from django.core.management.base import BaseCommand
from wagtail.models import Page
from django.apps import apps

class Command(BaseCommand):
    help = "Выводит дерево страниц Wagtail в текстовом виде (ASCII-tree)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--root',
            type=str,
            default=None,
            help='Slug корневой страницы (по умолчанию — корень сайта)'
        )
        parser.add_argument(
            '--mermaid',
            action='store_true',
            help='Вывести в формате Mermaid вместо ASCII'
        )

    def handle(self, *args, **options):
        root_slug = options['root']
        if root_slug:
            root = Page.objects.get(slug=root_slug, depth=2)  # обычно depth=2 — дети Home
        else:
            root = Page.objects.get(title="Root")  # или Site.objects.first().root_page

        if options['mermaid']:
            self.print_mermaid(root)
        else:
            self.print_ascii_tree(root)

    def print_ascii_tree(self, root, prefix=""):
        pages = root.get_children().live().in_menu().specific()
        for i, page in enumerate(pages):
            is_last = i == len(pages) - 1
            marker = "└── " if is_last else "├── "
            self.stdout.write(f"{prefix}{marker}{page.title} ({page.get_url()}) [{page.specific.__class__.__name__}]")
            if not is_last:
                new_prefix = prefix + "│   "
            else:
                new_prefix = prefix + "    "
            self.print_ascii_tree(page, new_prefix)

        # Если нет детей — просто выводим корень
        if not pages.exists():
            self.stdout.write(f"{prefix}└── (нет дочерних страниц)")

    def print_mermaid(self, root, parent_id=None, graph_lines=None):
        if graph_lines is None:
            graph_lines = ["graph TD"]
            node_id = 0
            graph_lines.append(f"    node{node_id}[\"{root.title} ({root.get_url()})\\n[{root.specific.__class__.__name__}]\"]")
            parent_id = node_id

        pages = root.get_children().live().specific()
        for page in pages:
            node_id = len(graph_lines)
            graph_lines.append(f"    node{node_id}[\"{page.title} ({page.get_url()})\\n[{page.specific.__class__.__name__}]\"]")
            graph_lines.append(f"    node{parent_id} --> node{node_id}")
            self.print_mermaid(page, node_id, graph_lines)

        if parent_id is not None:
            for line in graph_lines:
                self.stdout.write(line)