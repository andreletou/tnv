# models.py
from django.db import models
from django.db.models import Avg
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from decimal import Decimal
import json
import requests

User = get_user_model()

class ZoneLivraison(models.Model):
    """Zones de livraison géographiques"""
    nom = models.CharField(max_length=100)
    polygone = gis_models.PolygonField()
    tarif_base = models.DecimalField(max_digits=8, decimal_places=2, default=500.00)
    delai_estime = models.PositiveIntegerField(default=30)
    est_actif = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Zone de livraison"
        verbose_name_plural = "Zones de livraison"
    
    def __str__(self):
        return self.nom

    def to_geojson(self):
        """Convertir la zone en GeoJSON"""
        return {
            "type": "Feature",
            "geometry": json.loads(self.polygone.geojson),
            "properties": {
                "id": self.id,
                "nom": self.nom,
                "tarif_base": float(self.tarif_base),
                "delai_estime": self.delai_estime
            }
        }


class TypeVehicule(models.Model):
    """Configuration des types de véhicules"""
    nom = models.CharField(max_length=50)
    icone = models.CharField(max_length=50, default='moto')
    vitesse_moyenne = models.FloatField(default=25.0)  # km/h
    capacite_chargement = models.DecimalField(max_digits=8, decimal_places=2, default=10.0)  # kg
    consommation = models.FloatField(default=0.05)  # L/km
    tarif_multipliateur = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    
    def __str__(self):
        return self.nom


class Livreur(models.Model):
    TYPE_VEHICULE_CHOICES = [
        ('moto', 'Moto'),
        ('voiture', 'Voiture'),
        ('velo', 'Vélo'),
        ('scooter', 'Scooter'),
    ]
    
    # Champs spécifiques au livreur
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="livreur")
    permis_conduire = models.ImageField(upload_to='permis/')
    carte_grise = models.ImageField(upload_to='cartes_grises/')
    type_vehicule = models.CharField(
        max_length=50,
        choices=TYPE_VEHICULE_CHOICES,
        default='moto'
    )
    immatriculation = models.CharField(max_length=20)
    est_disponible = models.BooleanField(default=True)
    est_actif = models.BooleanField(default=True)
    est_en_ligne = models.BooleanField(default=False)
    position_actuelle = gis_models.PointField(null=True, blank=True)
    derniere_position_mise_a_jour = models.DateTimeField(null=True, blank=True)
    note_moyenne = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    nombre_livraisons = models.PositiveIntegerField(default=0)
    date_inscription = models.DateTimeField(auto_now_add=True)
    type_vehicule_obj = models.ForeignKey(
        TypeVehicule, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    zone_affectee = models.ForeignKey(
        ZoneLivraison, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    niveau_batterie = models.IntegerField(default=100)  # Pour véhicules électriques
    kilometrage_vehicule = models.FloatField(default=0.0)
    date_dernier_entretien = models.DateField(null=True, blank=True)
    competences_speciales = models.JSONField(default=list, blank=True)
    
    def __str__(self):
        return f"Livreur {self.user.username}"

    @property
    def username(self):
        return self.user.username
    
    @property
    def first_name(self):
        return self.user.first_name
    
    @property
    def last_name(self):
        return self.user.last_name
    
    @property
    def email(self):
        return self.user.email
    
    @property
    def telephone(self):
        return self.user.telephone

    def to_geojson(self):
        """Convertir le livreur en GeoJSON"""
        if not self.position_actuelle:
            return None
            
        return {
            "type": "Feature",
            "geometry": json.loads(self.position_actuelle.geojson),
            "properties": {
                "id": self.id,
                "nom": f"{self.first_name} {self.last_name}",
                "type_vehicule": self.type_vehicule,
                "est_disponible": self.est_disponible,
                "est_en_ligne": self.est_en_ligne,
                "note_moyenne": float(self.note_moyenne),
                "telephone": self.telephone
            }
        }

    def mettre_a_jour_position(self, latitude, longitude):
        """Met à jour la position actuelle du livreur"""
        try:
            if latitude and longitude:
                self.position_actuelle = Point(float(longitude), float(latitude))
                self.derniere_position_mise_a_jour = timezone.now()
                self.save()
                
                PositionLivreur.objects.create(
                    livreur=self,
                    position=self.position_actuelle
                )
                return True
        except (ValueError, TypeError) as e:
            print(f"Erreur lors de la mise à jour de la position: {e}")
            return False


class Livraison(models.Model):
    STATUT_CHOICES = [
        ('attribuee', 'Attribuée'),
        ('acceptee', 'Acceptée'),
        ('en_cours', 'En cours de livraison'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
        ('echec', 'Échec'),
    ]
    
    commande = models.OneToOneField(
        'clients.Commande',
        on_delete=models.CASCADE,
        related_name='livraison',
        verbose_name="Commande associée"
    )
    livreur = models.ForeignKey(
        Livreur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='livraisons',
        verbose_name="Livreur assigné"
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='attribuee',
        verbose_name="Statut de la livraison"
    )
    date_attribution = models.DateTimeField(null=True, blank=True)
    date_acceptation = models.DateTimeField(null=True, blank=True)
    date_debut_livraison = models.DateTimeField(null=True, blank=True)
    date_fin_livraison = models.DateTimeField(null=True, blank=True)
    cout_livraison = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('500.00'))
    distance_estimee = models.FloatField(null=True, blank=True)
    duree_estimee = models.PositiveIntegerField(null=True, blank=True)
    adresse_livraison_point = gis_models.PointField(null=True, blank=True)
    boutique_point = gis_models.PointField(null=True, blank=True)
    instructions_speciales = models.TextField(blank=True)
    preuve_livraison = models.ImageField(upload_to='preuves_livraison/', null=True, blank=True)
    signature_client = models.ImageField(upload_to='signatures/', null=True, blank=True)
    
    # Nouveaux champs pour Google Maps
    donnees_google_maps = models.JSONField(default=dict, blank=True)
    polyline_itineraire = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Livraison"
        verbose_name_plural = "Livraisons"
        ordering = ['-date_attribution']
    
    def __str__(self):
        return f"Livraison {self.id} - Commande {self.commande.reference}"

    def to_geojson(self):
        """Convertir la livraison en GeoJSON"""
        features = []
        
        # Point de boutique
        if self.boutique_point:
            features.append({
                "type": "Feature",
                "geometry": json.loads(self.boutique_point.geojson),
                "properties": {
                    "type": "boutique",
                    "livraison_id": self.id,
                    "statut": self.statut,
                    "reference": self.commande.reference
                }
            })
        
        # Point de livraison
        if self.adresse_livraison_point:
            features.append({
                "type": "Feature",
                "geometry": json.loads(self.adresse_livraison_point.geojson),
                "properties": {
                    "type": "livraison",
                    "livraison_id": self.id,
                    "statut": self.statut,
                    "client": f"{self.commande.client.first_name} {self.commande.client.last_name}",
                    "instructions": self.instructions_speciales,
                    "cout": float(self.cout_livraison)
                }
            })
        
        return {
            "type": "FeatureCollection",
            "features": features
        }

    def calculer_cout_google_maps(self, donnees_itineraire):
        """Calculer le coût basé sur les données Google Maps"""
        if not donnees_itineraire:
            return Decimal('500.00')
        
        try:
            distance_km = donnees_itineraire.get('distance', {}).get('value', 0) / 1000
            duree_minutes = donnees_itineraire.get('duration', {}).get('value', 0) / 60
            
            # Tarif de base
            tarif_base = Decimal('500.00')
            
            # Majoration distance (100 FCFA par km au-delà de 5km)
            if distance_km > 5:
                tarif_base += Decimal(str((distance_km - 5) * 100))
            
            # Majoration durée (50 FCFA par 15 minutes au-delà de 30min)
            if duree_minutes > 30:
                tarif_base += Decimal(str(((duree_minutes - 30) // 15) * 50))
            
            # Arrondir à la centaine supérieure
            tarif_base = (tarif_base // 100 + 1) * 100
            
            return max(tarif_base, Decimal('500.00'))
            
        except Exception as e:
            print(f"Erreur calcul coût: {e}")
            return Decimal('500.00')
    
    def assigner_livreur(self, livreur):
        """Assigner un livreur à la livraison"""
        self.livreur = livreur
        self.date_attribution = timezone.now()
        self.save()
        
        # Créer une notification
        if hasattr(self, 'livreur') and self.livreur:
            NotificationLivreur.objects.create(
                livreur=self.livreur,
                type_notification='nouvelle_livraison',
                titre='Nouvelle livraison assignée',
                message=f'Livraison #{self.id} - {self.commande.reference}',
                donnees_supplementaires={'livraison_id': self.id}
            )

    def accepter_livraison(self):
        """Accepter une livraison"""
        self.statut = 'acceptee'
        self.date_acceptation = timezone.now()
        self.save()
        
        # Mettre à jour les statistiques du livreur
        if self.livreur:
            self.livreur.nombre_livraisons = Livraison.objects.filter(
                livreur=self.livreur, 
                statut__in=['acceptee', 'en_cours', 'terminee']
            ).count()
            self.livreur.save()

    def commencer_livraison(self):
        """Commencer la livraison"""
        self.statut = 'en_cours'
        self.date_debut_livraison = timezone.now()
        self.save()

    def terminer_livraison(self):
        """Terminer la livraison"""
        self.statut = 'terminee'
        self.date_fin_livraison = timezone.now()
        self.save()
        
        # Mettre à jour la note moyenne du livreur
        if self.livreur:
            from django.db.models import Avg
            evaluations = EvaluationLivreur.objects.filter(
                livraison__livreur=self.livreur
            ).aggregate(moyenne=Avg('note'))
            
            if evaluations['moyenne']:
                self.livreur.note_moyenne = evaluations['moyenne']
                self.livreur.save()

    def annuler_livraison(self):
        """Annuler la livraison"""
        ancien_statut = self.statut
        self.statut = 'annulee'
        self.save()
        
        # Si la livraison était acceptée ou en cours, la remettre en disponibilité
        if ancien_statut in ['acceptee', 'en_cours']:
            self.livreur = None
            self.statut = 'attribuee'
            self.date_attribution = None
            self.date_acceptation = None
            self.date_debut_livraison = None
            self.save()

    # Méthodes utilitaires pour vérifier les permissions
    def peut_etre_acceptee_par(self, livreur):
        """Vérifier si la livraison peut être acceptée par ce livreur"""
        return (self.statut == 'attribuee' and 
                self.livreur is None and 
                livreur.est_disponible and 
                livreur.est_actif)

    def peut_etre_commencee_par(self, livreur):
        """Vérifier si la livraison peut être commencée par ce livreur"""
        return (self.statut == 'acceptee' and 
                self.livreur == livreur and 
                livreur.est_actif)

    def peut_etre_terminee_par(self, livreur):
        """Vérifier si la livraison peut être terminée par ce livreur"""
        return (self.statut == 'en_cours' and 
                self.livreur == livreur and 
                livreur.est_actif)

    def peut_etre_annulee_par(self, livreur):
        """Vérifier si la livraison peut être annulée par ce livreur"""
        return (self.statut in ['acceptee', 'en_cours'] and 
                self.livreur == livreur)


class GoogleMapsService:
    """Service pour interagir avec Google Maps API"""
    
    def __init__(self, api_key=None):
        from django.conf import settings
        self.api_key = api_key or settings.GOOGLE_MAPS_API_KEY
        self.base_url = "https://maps.googleapis.com/maps/api"
    
    def calculer_itineraire(self, origine, destination, mode='driving'):
        """Calculer l'itinéraire entre deux points"""
        try:
            url = f"{self.base_url}/directions/json"
            params = {
                'origin': f"{origine[0]},{origine[1]}",
                'destination': f"{destination[0]},{destination[1]}",
                'mode': mode,
                'key': self.api_key,
                'alternatives': True
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == 'OK':
                return data['routes'][0]  # Prendre le premier itinéraire
            else:
                print(f"Erreur Google Maps: {data['status']}")
                return None
                
        except Exception as e:
            print(f"Erreur API Google Maps: {e}")
            return None
    
    def geocoder_adresse(self, adresse):
        """Géocoder une adresse en coordonnées"""
        try:
            url = f"{self.base_url}/geocode/json"
            params = {
                'address': adresse,
                'key': self.api_key
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == 'OK':
                location = data['results'][0]['geometry']['location']
                return (location['lat'], location['lng'])
            else:
                print(f"Erreur géocodage: {data['status']}")
                return None
                
        except Exception as e:
            print(f"Erreur géocodage Google Maps: {e}")
            return None
    
    def optimiser_tournee(self, waypoints, origine=None, mode='driving'):
        """Optimiser une tournée avec Google Maps"""
        try:
            url = f"{self.base_url}/directions/json"
            
            waypoints_str = '|'.join([f"optimize:true|{lat},{lng}" for lat, lng in waypoints])
            
            params = {
                'origin': f"{origine[0]},{origine[1]}" if origine else f"{waypoints[0][0]},{waypoints[0][1]}",
                'destination': f"{origine[0]},{origine[1]}" if origine else f"{waypoints[0][0]},{waypoints[0][1]}",
                'waypoints': waypoints_str,
                'mode': mode,
                'key': self.api_key,
                'optimizeWaypoints': True
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == 'OK':
                return data['routes'][0]
            else:
                print(f"Erreur optimisation: {data['status']}")
                return None
                
        except Exception as e:
            print(f"Erreur optimisation Google Maps: {e}")
            return None

# Les autres modèles restent similaires...
class PositionLivreur(models.Model):
    livreur = models.ForeignKey(Livreur, on_delete=models.CASCADE, related_name='positions')
    position = gis_models.PointField()
    timestamp = models.DateTimeField(auto_now_add=True)
    vitesse = models.FloatField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Position de {self.livreur.username}"

class EvaluationLivreur(models.Model):
    livraison = models.OneToOneField(Livraison, on_delete=models.CASCADE, related_name='evaluation')
    note = models.PositiveIntegerField(choices=[(i, f'{i} étoile{"s" if i > 1 else ""}') for i in range(1, 6)])
    commentaire = models.TextField(blank=True)
    ponctualite = models.PositiveIntegerField(choices=[(i, f'{i}/5') for i in range(1, 6)])
    professionalisme = models.PositiveIntegerField(choices=[(i, f'{i}/5') for i in range(1, 6)])
    securite = models.PositiveIntegerField(choices=[(i, f'{i}/5') for i in range(1, 6)])
    date_evaluation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Évaluation de {self.livraison.livreur.username}"

class TourneeLivraison(models.Model):
    STATUT_CHOICES = [
        ('planifiee', 'Planifiée'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]
    
    livreur = models.ForeignKey(Livreur, on_delete=models.CASCADE)
    reference = models.CharField(max_length=20, unique=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='planifiee')
    livraisons = models.ManyToManyField(Livraison, related_name='tournees')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_debut = models.DateTimeField(null=True, blank=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    distance_totale = models.FloatField(default=0.0)
    duree_estimee = models.PositiveIntegerField(default=0)
    gain_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Données Google Maps
    donnees_optimisation = models.JSONField(default=dict, blank=True)
    polyline_tournee = models.TextField(blank=True)
    
    def __str__(self):
        return f"Tournée {self.reference}"

class AlgorithmeOptimisation(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField()
    parametres = models.JSONField(default=dict)
    est_actif = models.BooleanField(default=True)
    
    def __str__(self):
        return self.nom

class NotificationLivreur(models.Model):
    TYPE_CHOICES = [
        ('nouvelle_livraison', 'Nouvelle livraison disponible'),
        ('livraison_acceptee', 'Livraison acceptée'),
        ('livraison_terminee', 'Livraison terminée'),
        ('paiement', 'Paiement reçu'),
        ('systeme', 'Notification système'),
    ]
    
    livreur = models.ForeignKey(Livreur, on_delete=models.CASCADE, related_name='notifications')
    type_notification = models.CharField(max_length=30, choices=TYPE_CHOICES)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    est_lue = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    donnees_supplementaires = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"{self.titre} - {self.livreur.username}"

class SignalementProbleme(models.Model):
    TYPES_PROBLEMES = [
        ('route_barree', 'Route barrée'),
        ('adresse_incorrecte', 'Adresse incorrecte'),
        ('trafic_extreme', 'Trafic extrême'),
        ('danger', 'Danger / Accident'),
        ('client_absent', 'Client absent'),
        ('colis_endommage', 'Colis endommagé'),
        ('autre', 'Autre problème'),
    ]
    
    livreur = models.ForeignKey(Livreur, on_delete=models.CASCADE)
    livraison = models.ForeignKey(Livraison, on_delete=models.CASCADE, null=True, blank=True)
    type_probleme = models.CharField(max_length=50, choices=TYPES_PROBLEMES)
    description = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    photo = models.ImageField(upload_to='signalements/', null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    resolu = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-timestamp']