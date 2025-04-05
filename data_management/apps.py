from django.apps import AppConfig


class DataManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'data_management'

    def ready(self):
        # Implicitly connect signal handlers decorated with @receiver.
        import data_management.signals # noqa
