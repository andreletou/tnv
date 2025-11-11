from django.apps import AppConfig


class LivraisonsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'livraisons'
    verbose_name = 'Gestion des livraisons'
    
    def ready(self):
        import livraisons.signals