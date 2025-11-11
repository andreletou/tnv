from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from decimal import Decimal

User = get_user_model()

class Livreur(models.Model):
    TYPE_VEHICULE_CHOICES = [
        ('moto', 'Moto'),
        ('voiture', 'Voiture'),
        ('velo', 'Vélo'),
        ('scooter', 'Scooter'),
    ]
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='livreur_profile'
    )
    
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
    
    def __str__(self):
        return f"Livreur {self.user.username}"

    # Propriétés pour accéder aux données utilisateur
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

    
    def mettre_a_jour_position(self, latitude, longitude):
        """Met à jour la position actuelle du livreur"""
        try:
            # S'assurer que les coordonnées sont valides
            if latitude and longitude:
                self.position_actuelle = Point(float(longitude), float(latitude))
                self.derniere_position_mise_a_jour = timezone.now()
                self.save()
                
                # Enregistrer dans l'historique des positions
                PositionLivreur.objects.create(
                    livreur=self,
                    position=self.position_actuelle
                )
                return True
        except (ValueError, TypeError) as e:
            print(f"Erreur lors de la mise à jour de la position: {e}")
            return False
    
    def calculer_distance(self, point_destination):
        """Calcule la distance entre la position actuelle et un point de destination"""
        if not self.position_actuelle or not point_destination:
            return None
        
        try:
            # Calculer la distance en mètres
            distance = self.position_actuelle.distance(point_destination) * 100000  # Conversion approximative en mètres
            return distance
        except Exception as e:
            print(f"Erreur lors du calcul de distance: {e}")
            return None
    
    def est_dans_rayon(self, point_destination, rayon_km=10):
        """Vérifie si le livreur est dans un rayon donné d'un point de destination"""
        distance = self.calculer_distance(point_destination)
        if distance is None:
            return False
        
        return distance <= (rayon_km * 1000)  # Conversion en mètres

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
    date_attribution = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'attribution"
    )
    date_acceptation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'acceptation"
    )
    date_debut_livraison = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de début de livraison"
    )
    date_fin_livraison = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de fin de livraison"
    )
    cout_livraison = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('500.00'),
        verbose_name="Coût de livraison (FCFA)"
    )
    distance_estimee = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Distance estimée (km)"
    )
    duree_estimee = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Durée estimée (minutes)"
    )
    adresse_livraison_point = gis_models.PointField(
        null=True,
        blank=True,
        verbose_name="Point de livraison"
    )
    boutique_point = gis_models.PointField(
        null=True,
        blank=True,
        verbose_name="Point de la boutique"
    )
    instructions_speciales = models.TextField(
        blank=True,
        verbose_name="Instructions spéciales de livraison"
    )
    preuve_livraison = models.ImageField(
        upload_to='preuves_livraison/',
        null=True,
        blank=True,
        verbose_name="Preuve de livraison"
    )
    signature_client = models.ImageField(
        upload_to='signatures/',
        null=True,
        blank=True,
        verbose_name="Signature du client"
    )
    
    class Meta:
        verbose_name = "Livraison"
        verbose_name_plural = "Livraisons"
        ordering = ['-date_attribution']
    
    def __str__(self):
        return f"Livraison {self.id} - Commande {self.commande.reference}"
    
    def assigner_livreur(self, livreur):
        """Assigne un livreur à cette livraison"""
        self.livreur = livreur
        self.date_attribution = timezone.now()
        self.statut = 'attribuee'
        self.save()
    
    def accepter_livraison(self):
        """Marque la livraison comme acceptée par le livreur"""
        if self.statut == 'attribuee':
            self.statut = 'acceptee'
            self.date_acceptation = timezone.now()
            self.save()
    
    def commencer_livraison(self):
        """Marque le début de la livraison"""
        if self.statut == 'acceptee':
            self.statut = 'en_cours'
            self.date_debut_livraison = timezone.now()
            self.save()
    
    def terminer_livraison(self):
        """Marque la livraison comme terminée"""
        if self.statut == 'en_cours':
            self.statut = 'terminee'
            self.date_fin_livraison = timezone.now()
            
            # Mettre à jour le statut de la commande
            self.commande.statut = 'livree'
            self.commande.save()
            
            # Mettre à jour les statistiques du livreur
            if self.livreur:
                self.livreur.nombre_livraisons += 1
                self.livreur.save()
            
            self.save()
    
    def annuler_livraison(self):
        """Annule la livraison"""
        self.statut = 'annulee'
        self.save()
    
    def calculer_distance_et_duree(self, point_depart=None):
        """Calcule la distance et la durée estimées de la livraison"""
        if not point_depart and self.livreur and self.livreur.position_actuelle:
            point_depart = self.livreur.position_actuelle
        elif not point_depart and self.boutique_point:
            point_depart = self.boutique_point
        
        if point_depart and self.adresse_livraison_point:
            # Calcul de la distance en km
            distance_km = point_depart.distance(self.adresse_livraison_point) * 111.32  # Conversion approximative
            self.distance_estimee = round(distance_km, 2)
            
            # Estimation de la durée (basée sur une vitesse moyenne de 30 km/h en ville)
            vitesse_moyenne = 30  # km/h
            self.duree_estimee = int((distance_km / vitesse_moyenne) * 60)  # en minutes
            self.save()

class PositionLivreur(models.Model):
    """Historique des positions du livreur pour le suivi en temps réel"""
    livreur = models.ForeignKey(
        Livreur,
        on_delete=models.CASCADE,
        related_name='positions'
    )
    position = gis_models.PointField(verbose_name="Position")
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Timestamp"
    )
    vitesse = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Vitesse (km/h)"
    )
    
    class Meta:
        verbose_name = "Position du livreur"
        verbose_name_plural = "Positions des livreurs"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['livreur', 'timestamp'])
        ]
    
    def __str__(self):
        return f"Position de {self.livreur.username} à {self.timestamp}"

class EvaluationLivreur(models.Model):
    """Évaluation du livreur par le client"""
    livraison = models.OneToOneField(
        Livraison,
        on_delete=models.CASCADE,
        related_name='evaluation'
    )
    note = models.PositiveIntegerField(
        choices=[(i, f'{i} étoile{"s" if i > 1 else ""}') for i in range(1, 6)],
        verbose_name="Note"
    )
    commentaire = models.TextField(
        blank=True,
        verbose_name="Commentaire"
    )
    ponctualite = models.PositiveIntegerField(
        choices=[(i, f'{i}/5') for i in range(1, 6)],
        verbose_name="Ponctualité"
    )
    professionalisme = models.PositiveIntegerField(
        choices=[(i, f'{i}/5') for i in range(1, 6)],
        verbose_name="Professionalisme"
    )
    securite = models.PositiveIntegerField(
        choices=[(i, f'{i}/5') for i in range(1, 6)],
        verbose_name="Sécurité du colis"
    )
    date_evaluation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'évaluation"
    )
    
    class Meta:
        verbose_name = "Évaluation du livreur"
        verbose_name_plural = "Évaluations des livreurs"
    
    def __str__(self):
        return f"Évaluation de {self.livraison.livreur.username} - {self.note}/5"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Mettre à jour la note moyenne du livreur
        livreur = self.livraison.livreur
        evaluations = EvaluationLivreur.objects.filter(livraison__livreur=livreur)
        if evaluations.exists():
            moyenne = evaluations.aggregate(models.Avg('note'))['note__avg']
            livreur.note_moyenne = round(moyenne, 2)
            livreur.save()

class NotificationLivreur(models.Model):
    """Notifications pour les livreurs"""
    TYPE_CHOICES = [
        ('nouvelle_livraison', 'Nouvelle livraison disponible'),
        ('livraison_acceptee', 'Livraison acceptée'),
        ('livraison_terminee', 'Livraison terminée'),
        ('paiement', 'Paiement reçu'),
        ('systeme', 'Notification système'),
    ]
    
    livreur = models.ForeignKey(
        Livreur,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    type_notification = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        verbose_name="Type de notification"
    )
    titre = models.CharField(
        max_length=200,
        verbose_name="Titre"
    )
    message = models.TextField(
        verbose_name="Message"
    )
    est_lue = models.BooleanField(
        default=False,
        verbose_name="Lue"
    )
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    donnees_supplementaires = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Données supplémentaires"
    )
    
    class Meta:
        verbose_name = "Notification du livreur"
        verbose_name_plural = "Notifications des livreurs"
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"{self.titre} - {self.livreur.username}"
    
    def marquer_comme_lue(self):
        """Marque la notification comme lue"""
        self.est_lue = True
        self.save()