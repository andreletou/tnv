from django.contrib import admin
from .models import Client, Panier, ArticlePanier, Commande, ArticleCommande, Favori, Avis

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('username', 'telephone', 'adresse', 'afficher_localisation')

    def afficher_localisation(self, obj):
        # Access latitude/longitude through the user relationship
        if obj.user.latitude and obj.user.longitude:
            return f"({obj.user.latitude}, {obj.user.longitude})"
        return "Non définie"
    afficher_localisation.short_description = "Localisation"

@admin.register(Panier)
class PanierAdmin(admin.ModelAdmin):
    list_display = ['client', 'date_creation', 'nombre_articles', 'total']
    readonly_fields = ['date_creation', 'date_modification']

@admin.register(ArticlePanier)
class ArticlePanierAdmin(admin.ModelAdmin):
    list_display = ['panier', 'produit', 'quantite', 'sous_total', 'date_ajout']
    readonly_fields = ['date_ajout']

@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'client', 'commercant', 'total', 'statut', 
        'statut_paiement', 'date_commande', 'a_coordonnees_livraison', 'source_coordonnees'
    ]
    list_filter = ['statut', 'statut_paiement', 'methode_paiement', 'date_commande']
    search_fields = ['reference', 'client__username', 'commercant__nom_boutique']
    readonly_fields = ['date_commande', 'date_modification', 'reference', 'source_coordonnees']
    
    def a_coordonnees_livraison(self, obj):
        return obj.a_coordonnees_livraison
    a_coordonnees_livraison.boolean = True
    a_coordonnees_livraison.short_description = "A coordonnées"
    
    def source_coordonnees(self, obj):
        return obj.source_coordonnees
    source_coordonnees.short_description = "Source coordonnées"
    
@admin.register(ArticleCommande)
class ArticleCommandeAdmin(admin.ModelAdmin):
    list_display = ['commande', 'produit', 'quantite', 'prix_unitaire', 'sous_total']
    readonly_fields = []

@admin.register(Favori)
class FavoriAdmin(admin.ModelAdmin):
    list_display = ['client', 'produit', 'date_ajout']
    readonly_fields = ['date_ajout']

@admin.register(Avis)
class AvisAdmin(admin.ModelAdmin):
    list_display = ['client', 'produit', 'note', 'est_approuve', 'date_creation']
    list_filter = ['note', 'est_approuve', 'date_creation']
    search_fields = ['client__username', 'produit__nom']
    readonly_fields = ['date_creation']