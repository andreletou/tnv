from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
# postgis
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Client(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='client_profile'
    )
    
    class Meta:
        verbose_name = "Profil Client"
        verbose_name_plural = "Profils Clients"

    def __str__(self):
        return f"Client: {self.user.username}"

    # Propriétés pour accéder aux données utilisateur
    @property
    def username(self):
        return self.user.username
    
    @property
    def email(self):
        return self.user.email
    
    @property
    def first_name(self):
        return self.user.first_name
    
    @property
    def last_name(self):
        return self.user.last_name
    
    @property
    def telephone(self):
        return self.user.telephone
    
    @property
    def adresse(self):
        return self.user.adresse
    
    @property
    def photo_profil(self):
        return self.user.photo_profil

class Panier(models.Model):
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='panier')
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Date de modification")
    
    class Meta:
        verbose_name = "Panier"
        verbose_name_plural = "Paniers"
    
    def __str__(self):
        return f"Panier de {self.client.username}"
    
    @property
    def total(self):
        """Calcule le total du panier"""
        return sum(item.sous_total for item in self.items.all())
    
    @property
    def nombre_articles(self):
        """Retourne le nombre total d'articles dans le panier"""
        return sum(item.quantite for item in self.items.all())

class ArticlePanier(models.Model):
    panier = models.ForeignKey(Panier, on_delete=models.CASCADE, related_name='items')
    produit = models.ForeignKey('commercants.Produit', on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(default=1, verbose_name="Quantité")
    date_ajout = models.DateTimeField(auto_now_add=True, verbose_name="Date d'ajout")
    
    class Meta:
        verbose_name = "Article du panier"
        verbose_name_plural = "Articles du panier"
        unique_together = ['panier', 'produit']
    
    def __str__(self):
        return f"{self.quantite} x {self.produit.nom}"
    
    @property
    def sous_total(self):
        """Calcule le sous-total pour cet article"""
        return self.quantite * self.produit.prix_effectif

class Commande(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente de validation'),
        ('validee', 'Validée'),
        ('en_preparation', 'En préparation'),
        ('prete', 'Prête pour livraison'),
        ('en_livraison', 'En cours de livraison'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='commandes')
    commercant = models.ForeignKey('commercants.Commercant', on_delete=models.CASCADE, related_name='commandes_recues')
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente', verbose_name="Statut")
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total (FCFA)")
    adresse_livraison = models.TextField(verbose_name="Adresse de livraison")
    latitude_livraison = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name="Latitude livraison")
    longitude_livraison = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name="Longitude livraison")
    instructions_livraison = models.TextField(blank=True, verbose_name="Instructions de livraison")
    methode_paiement = models.CharField(
        max_length=20,
        choices=[
            ('paygate', 'PayGate'),
            ('espece', 'Espèce à la livraison'),
            ('mobile_money', 'Mobile Money'),
        ],
        default='espece',
        verbose_name="Méthode de paiement"
    )
    statut_paiement = models.CharField(
        max_length=20,
        choices=[
            ('en_attente', 'En attente'),
            ('paye', 'Payé'),
            ('echec', 'Échec'),
            ('rembourse', 'Remboursé'),
        ],
        default='en_attente',
        verbose_name="Statut du paiement"
    )
    date_commande = models.DateTimeField(auto_now_add=True, verbose_name="Date de commande")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Date de modification")
    reference = models.CharField(max_length=50, unique=True, verbose_name="Référence de commande")
    point_livraison = gis_models.PointField(
        geography=True, 
        null=True, 
        blank=True, 
        verbose_name="Point de livraison"
    )
    
    class Meta:
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"
        ordering = ['-date_commande']
    
    def __str__(self):
        return f"Commande {self.reference} - {self.client.username}"
    
    def save(self, *args, **kwargs):
        # Génération de la référence si absente
        if not self.reference:
            import uuid
            self.reference = f"CMD-{uuid.uuid4().hex[:8].upper()}"

        # Gestion du point de livraison
        self._set_point_livraison()

        super().save(*args, **kwargs)
    
    def _set_point_livraison(self):
        """Définit le point de livraison avec fallback sur les coordonnées du client"""
        self.point_livraison = None
        
        # Essayer d'abord avec les coordonnées de livraison
        if self._coordonnees_valides(self.latitude_livraison, self.longitude_livraison):
            try:
                lat = float(self.latitude_livraison)
                lng = float(self.longitude_livraison)
                # Vérifier que les coordonnées ne sont pas nulles
                if lat != 0 and lng != 0:
                    self.point_livraison = Point(lng, lat, srid=4326)
                    print(f"Point de livraison défini avec coordonnées livraison: ({lat}, {lng})")
                    return
            except (ValueError, TypeError) as e:
                print(f"Erreur lors de la conversion des coordonnées livraison: {e}")


    def _set_point_from_client(self):
        """Méthode helper pour définir le point de livraison à partir des coordonnées du client"""
        try:
            client = self.client.user
            if self._coordonnees_valides(client.latitude, client.longitude):
                lat = float(client.latitude)
                lng = float(client.longitude)
                self.point_livraison = Point(lng, lat, srid=4326)
                print(f"Point de livraison défini avec coordonnées client: ({lat}, {lng})")
                
                # Mettre à jour les coordonnées de livraison avec celles du client
                if not self.latitude_livraison or not self.longitude_livraison:
                    self.latitude_livraison = lat
                    self.longitude_livraison = lng
                    print("Coordonnées de livraison mises à jour avec celles du client")
            else:
                print("Client sans coordonnées GPS valides, point de livraison non défini")
        except Exception as e:
            print(f"Erreur lors de la récupération des coordonnées client: {e}")
    
    def _coordonnees_valides(self, lat, lng):
        """Vérifie si les coordonnées sont valides"""
        if lat is None or lng is None:
            return False
        
        try:
            lat_float = float(lat)
            lng_float = float(lng)
            return (-90 <= lat_float <= 90 and -180 <= lng_float <= 180)
        except (ValueError, TypeError):
            return False
    
    @property
    def a_coordonnees_livraison(self):
        """Vérifie si la commande a des coordonnées de livraison valides"""
        return self.point_livraison is not None
    
    @property
    def source_coordonnees(self):
        """Retourne la source des coordonnées utilisées"""
        if not self.point_livraison:
            return "Aucune"
        
        # Vérifier si les coordonnées correspondent à celles du client
        try:
            if (self.client.user.latitude and self.client.user.longitude and
                self.latitude_livraison and self.longitude_livraison and
                abs(float(self.latitude_livraison) - float(self.client.user.latitude)) < 0.0001 and
                abs(float(self.longitude_livraison) - float(self.client.user.longitude)) < 0.0001):
                return "Client"
        except (ValueError, TypeError, AttributeError):
            pass
        
        return "Livraison"

    
class ArticleCommande(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='articles')
    produit = models.ForeignKey('commercants.Produit', on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(verbose_name="Quantité")
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix unitaire (FCFA)")
    
    class Meta:
        verbose_name = "Article de commande"
        verbose_name_plural = "Articles de commande"
    
    def __str__(self):
        return f"{self.quantite} x {self.produit.nom} - {self.commande.reference}"
    
    @property
    def sous_total(self):
        """Calcule le sous-total pour cet article"""
        return self.quantite * self.prix_unitaire

class Favori(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='favoris')
    produit = models.ForeignKey('commercants.Produit', on_delete=models.CASCADE, related_name='clients_favoris')
    date_ajout = models.DateTimeField(auto_now_add=True, verbose_name="Date d'ajout")
    
    class Meta:
        verbose_name = "Favori"
        verbose_name_plural = "Favoris"
        unique_together = ['client', 'produit']
    
    def __str__(self):
        return f"{self.client.username} - {self.produit.nom}"

class Avis(models.Model):
    NOTE_CHOICES = [
        (1, '1 étoile'),
        (2, '2 étoiles'),
        (3, '3 étoiles'),
        (4, '4 étoiles'),
        (5, '5 étoiles'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='avis')
    produit = models.ForeignKey('commercants.Produit', on_delete=models.CASCADE, related_name='avis')
    note = models.IntegerField(choices=NOTE_CHOICES, verbose_name="Note")
    commentaire = models.TextField(verbose_name="Commentaire")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    est_approuve = models.BooleanField(default=True, verbose_name="Avis approuvé")
    
    class Meta:
        verbose_name = "Avis"
        verbose_name_plural = "Avis"
        unique_together = ['client', 'produit']
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"Avis de {self.client.username} sur {self.produit.nom} - {self.note}/5"