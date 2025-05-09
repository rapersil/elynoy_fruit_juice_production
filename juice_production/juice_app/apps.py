from django.apps import AppConfig

class JuiceAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'juice_app'

    def ready(self):
        """Import signal  when the app is ready."""
        import juice_app.signals
