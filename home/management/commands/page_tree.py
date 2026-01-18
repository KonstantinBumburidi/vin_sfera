# home/management/commands/show_page_tree.py
from django.core.management.base import BaseCommand
from wagtail.models import Page, Site
from anytree import Node, RenderTree

class Command(BaseCommand):
    help = "Выводит дерево страниц Wagtail с помощью anytree (красивое ASCII-дерево)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--root-slug',
            type=str,
            default=None,
            help='Slug корневой страницы (по умолчанию — домашняя страница сайта)'
        )
        parser.add_argument(
            '--show-draft',
            action='store_true',
            help='Показывать также черновики (не только live)'
        )

    def handle(self, *args, **options):
        # Определяем корневую страницу
        if options['root_slug']:
            root_page = Page.objects.get(slug=options['root_slug']).specific
        else:
            # Стандартно берём домашнюю страницу текущего сайта
            site = Site.objects.get(is_default_site=True)  # или Site.objects.first()
            root_page = site.root_page.specific

        self.stdout.write(f"Строим дерево от: {root_page.title} ({root_page.get_url()})\n")

        # Рекурсивная функция построения дерева
        def build_anytree(page, parent=None):
            node_text = f"{page.title} ({page.get_url() or 'no url'}) [{page.__class__.__name__}]"
            node = Node(node_text, parent=parent)
            # Фильтр детей
            queryset = page.get_children().specific()
            if not options['show_draft']:
                queryset = queryset.live()
            for child in queryset:
                build_anytree(child, node)
            return node

        root_node = build_anytree(root_page)

        # Красивый вывод
        for pre, _, node in RenderTree(root_node):
            self.stdout.write(f"{pre}{node.name}")

        self.stdout.write("\nГотово!")