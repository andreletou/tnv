from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Portefeuille

User = get_user_model()

@receiver(post_save, sender=User)
def creer_portefeuille(sender, instance, created, **kwargs):
    """Créer automatiquement un portefeuille pour chaque nouvel utilisateur"""
    if created:
        Portefeuille.objects.create(user=instance)