import json
from django.core.management.base import BaseCommand
from django.db import transaction
from channels.models import FChannel, ChannelGroup

class Command(BaseCommand):
    help = 'Импорт каналов из старой таблицы alsfera_canal в FChannel'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Путь к JSON-файлу с данными')

    @transaction.atomic
    def handle(self, *args, **options):
        json_file = options['json_file']

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Ошибка чтения JSON: {e}'))
            return

        created = 0

        for item in data:
            group_id = item.get('group_id')
            group = ChannelGroup.objects.get(id=group_id)

            # Обработка content: чистый текст → оборачиваем в <p>
            raw_content = item.get('content', '').strip()
            if raw_content:
                paragraphs = [p.strip() for p in raw_content.split('\n') if p.strip()]
                clean_content = ''.join(f'<p>{p}</p>' for p in paragraphs)
            else:
                clean_content = ''

            FChannel.objects.create(
                group=group,
                sort_order=item.get('sort_order', 0),
                name=item['name'],
                description=item.get('description', ''),
                content=clean_content
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f'Импортировано: {created} каналов'))