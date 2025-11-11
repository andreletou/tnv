from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils import timezone

User = get_user_model()

class Commercant(models.Model):
    CATEGORIES = [
        ('alimentation', 'Alimentation'),
        ('electronique', 'Électronique'),
        ('vetements', 'Vêtements'),
        ('sante', 'Santé et Beauté'),
        ('maison', 'Maison et Jardin'),
        ('sport', 'Sport et Loisirs'),
        ('autre', 'Autre'),
    ]
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='commercant_profile'
    )
    nom_boutique = models.CharField(max_length=200, verbose_name="Nom de la boutique")
    categorie = models.CharField(max_length=20, choices=CATEGORIES, verbose_name="Catégorie")
    description = models.TextField(blank=True, verbose_name="Description de la boutique")
    photo_boutique = models.ImageField(upload_to='boutiques/', blank=True, null=True, verbose_name="Photo de la boutique")
    horaire_ouverture = models.TimeField(verbose_name="Heure d'ouverture")
    horaire_fermeture = models.TimeField(verbose_name="Heure de fermeture")
    jours_ouverture = models.CharField(
        max_length=100,
        default="Lundi-Mardi-Mercredi-Jeudi-Vendredi-Samedi",
        verbose_name="Jours d'ouverture"
    )
    est_actif = models.BooleanField(default=True, verbose_name="Boutique active")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    class Meta:
        verbose_name = "Commerçant"
        verbose_name_plural = "Commerçants"
    
    def __str__(self):
        return f"{self.nom_boutique} - {self.get_categorie_display()}"
    
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
    def latitude(self):
        return self.user.latitude
    
    @property
    def longitude(self):
        return self.user.longitude
class Produit(models.Model):
    CATEGORIES_PRODUIT = [
        ('alimentaire', 'Produit alimentaire'),
        ('electronique', 'Électronique'),
        ('vetement', 'Vêtement'),
        ('beaute', 'Beauté et soin'),
        ('maison', 'Maison'),
        ('sport', 'Sport'),
        ('autre', 'Autre'),
    ]
    
    nom = models.CharField(max_length=200, verbose_name="Nom du produit")
    description = models.TextField(blank=True, verbose_name="Description")
    prix = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix (FCFA)")
    prix_promotionnel = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Prix promotionnel (FCFA)"
    )
    stock = models.PositiveIntegerField(default=0, verbose_name="Quantité en stock")
    stock_min = models.PositiveIntegerField(default=5, verbose_name="Stock minimum alerte")
    categorie = models.CharField(max_length=20, choices=CATEGORIES_PRODUIT, verbose_name="Catégorie du produit")
    photo = models.ImageField(upload_to='produits/', blank=True, null=True, verbose_name="Photo du produit")
    est_actif = models.BooleanField(default=True, verbose_name="Produit actif")
    est_en_promotion = models.BooleanField(default=False, verbose_name="En promotion")
    date_ajout = models.DateTimeField(auto_now_add=True, verbose_name="Date d'ajout")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Date de modification")
    commercant = models.ForeignKey('Commercant', on_delete=models.CASCADE, related_name='produits')
    
    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
        ordering = ['-date_ajout']
    
    def __str__(self):
        return f"{self.nom} - {self.prix} FCFA"
    
    @property
    def prix_effectif(self):
        """Retourne le prix effectif (promotionnel si applicable, sinon prix normal)"""
        return self.prix_promotionnel if self.est_en_promotion and self.prix_promotionnel else self.prix
    
    @property
    def est_en_stock(self):
        """Vérifie si le produit est en stock"""
        return self.stock > 0
    
    @property
    def est_stock_faible(self):
        """Vérifie si le stock est faible"""
        return self.stock <= self.stock_min

class Promotion(models.Model):
    produit = models.ForeignKey('Produit', on_delete=models.CASCADE, related_name='promotions')
    pourcentage_reduction = models.PositiveIntegerField(
        verbose_name="Pourcentage de réduction (%)"
    )
    date_debut = models.DateTimeField(verbose_name="Date de début")
    date_fin = models.DateTimeField(verbose_name="Date de fin")
    description = models.TextField(blank=True, verbose_name="Description de la promotion")
    est_active = models.BooleanField(default=True, verbose_name="Promotion active")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    
    class Meta:
        verbose_name = "Promotion"
        verbose_name_plural = "Promotions"
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"Promotion {self.pourcentage_reduction}% sur {self.produit.nom}"
    
    @property
    def est_en_cours(self):
        """Vérifie si la promotion est en cours"""
        now = timezone.now()
        return self.est_active and self.date_debut <= now <= self.date_fin
    
    def calculer_prix_promotionnel(self, prix_original):
        """Calcule le prix promotionnel basé sur le pourcentage de réduction"""
        from decimal import Decimal
        reduction = (Decimal(str(self.pourcentage_reduction)) / Decimal('100')) * Decimal(str(prix_original))
        prix_promo = Decimal(str(prix_original)) - reduction
        return prix_promo.quantize(Decimal('0.01'))