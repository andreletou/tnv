from django.contrib import admin
from .models import Commercant, Produit, Promotion

@admin.register(Commercant)
class CommercantAdmin(admin.ModelAdmin):
    list_display = ['username', 'nom_boutique', 'categorie', 'telephone', 'est_actif', 'date_creation']
    list_filter = ['categorie', 'est_actif', 'date_creation']
    search_fields = ['username', 'nom_boutique', 'email']
    readonly_fields = ['date_creation']

@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ['nom', 'commercant', 'prix', 'stock', 'categorie', 'est_actif', 'est_en_promotion', 'date_ajout']
    list_filter = ['categorie', 'est_actif', 'est_en_promotion', 'date_ajout']
    search_fields = ['nom', 'commercant__nom_boutique']
    readonly_fields = ['date_ajout', 'date_modification']

@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ['produit', 'pourcentage_reduction', 'date_debut', 'date_fin', 'est_active', 'date_creation']
    list_filter = ['est_active', 'date_creation']
    search_fields = ['produit__nom', 'produit__commercant__nom_boutique']
    readonly_fields = ['date_creation']