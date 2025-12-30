from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Livraison, NotificationLivreur, Livreur
from clients.models import Commande


@receiver(post_save, sender=Commande)
def creer_livraison_automatiquement(sender, instance, created, **kwargs):
    """
    Crée automatiquement une livraison lorsqu'une commande est validée
    """
    if instance.statut == 'validee' and not hasattr(instance, 'livraison'):
        # Créer une livraison automatiquement
        livraison = Livraison.objects.create(
            commande=instance,
            statut='attribuee',
            date_attribution=timezone.now(),
            cout_livraison=500.00,  # Coût par défaut
            instructions_speciales=instance.instructions_livraison
        )
        
        # Calculer les coordonnées si disponibles
        if instance.latitude_livraison and instance.longitude_livraison:
            from django.contrib.gis.geos import Point
            livraison.adresse_livraison_point = Point(
                instance.longitude_livraison,
                instance.latitude_livraison
            )
        
        if instance.commercant and instance.commercant.latitude and instance.commercant.longitude:
            from django.contrib.gis.geos import Point
            livraison.boutique_point = Point(
                instance.commercant.longitude,
                instance.commercant.latitude
            )
        
        livraison.save()
        
        # Notifier les livreurs disponibles à proximité
        notifier_livreurs_proches(livraison)


@receiver(post_save, sender=Livraison)
def notifier_changement_statut_livraison(sender, instance, created, **kwargs):
    """
    Notifie les changements de statut de livraison
    """
    if not created and instance.livreur:
        # Créer une notification pour le livreur
        type_notification = {
            'acceptee': 'livraison_acceptee',
            'en_cours': 'livraison_en_cours',
            'terminee': 'livraison_terminee',
            'annulee': 'livraison_annulee'
        }.get(instance.statut)
        
        if type_notification:
            titre = {
                'acceptee': 'Livraison acceptée',
                'en_cours': 'Livraison en cours',
                'terminee': 'Livraison terminée',
                'annulee': 'Livraison annulée'
            }.get(instance.statut)
            
            message = f"La livraison {instance.id} - Commande {instance.commande.reference} est {instance.get_statut_display()}."
            
            NotificationLivreur.objects.create(
                livreur=instance.livreur,
                type_notification=type_notification,
                titre=titre,
                message=message,
                donnees_supplementaires={
                    'livraison_id': instance.id,
                    'commande_id': instance.commande.id
                }
            )


def notifier_livreurs_proches(livraison):
    """
    Notifie les livreurs disponibles à proximité d'une nouvelle livraison
    """
    if not livraison.boutique_point:
        return
    
    # Chercher les livreurs disponibles et en ligne à proximité
    livreurs_proches = Livreur.objects.filter(
        est_disponible=True,
        est_en_ligne=True,
        position_actuelle__isnull=False
    ).filter(
        position_actuelle__distance_lte=(livraison.boutique_point, 10000)  # 10km
    ).annotate(
        distance=models.functions.Distance('position_actuelle', livraison.boutique_point)
    ).order_by('distance')[:5]  # Limiter aux 5 plus proches
    
    for livreur in livreurs_proches:
        NotificationLivreur.objects.create(
            livreur=livreur,
            type_notification='nouvelle_livraison',
            titre='Nouvelle livraison disponible',
            message=f"Une nouvelle livraison est disponible près de votre position: {livraison.commande.reference}",
            donnees_supplementaires={
                'livraison_id': livraison.id,
                'commande_id': livraison.commande.id,
                'distance_km': round(livreur.distance.m / 1000, 1)
            }
        )