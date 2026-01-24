from django.apps import AppConfig


class FeedConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'feed'

    def ready(self):
        # Все импорты только здесь — внутри ready()
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group
        from django.db.models.signals import post_save
        from django.dispatch import receiver

        from .models import Profile

        User = get_user_model()

        @receiver(post_save, sender=User)
        def create_user_profile(sender, instance, created, **kwargs):
            if created:
                # Создаём профиль
                Profile.objects.get_or_create(user=instance)  # get_or_create на всякий случай

                # Автоматически добавляем в группу "COSMO"
                try:
                    cosmo_group = Group.objects.get(name="COSMO")
                    instance.groups.add(cosmo_group)
                except Group.DoesNotExist:
                    pass  # если группы нет — просто пропускаем

        @receiver(post_save, sender=User)
        def save_user_profile(sender, instance, **kwargs):
            try:
                instance.feed_profile.save()
            except AttributeError:
                pass  # если профиля ещё нет — ничего не делаем