from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.utils import timezone
from django.db.models import Sum
from django import forms
from .models import (
    Client, Panier, ArticlePanier, Commande, ArticleCommande, 
    Favori, Avis, Portefeuille, TransactionPortefeuille, 
    Commission, DepotPortefeuille, RetraitCommercant
)

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'telephone', 'adresse', 'afficher_localisation', 'date_joined')
    list_filter = ('user__date_joined',)
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'user__telephone')
    readonly_fields = ('date_joined',)

    def username(self, obj):
        return obj.user.username
    username.short_description = "Nom d'utilisateur"

    def email(self, obj):
        return obj.user.email
    email.short_description = "Email"

    def telephone(self, obj):
        return obj.user.telephone
    telephone.short_description = "Téléphone"

    def adresse(self, obj):
        return obj.user.adresse
    adresse.short_description = "Adresse"

    def date_joined(self, obj):
        return obj.user.date_joined
    date_joined.short_description = "Date d'inscription"

    def afficher_localisation(self, obj):
        if obj.user.latitude and obj.user.longitude:
            return f"({obj.user.latitude}, {obj.user.longitude})"
        return "Non définie"
    afficher_localisation.short_description = "Localisation"

@admin.register(Panier)
class PanierAdmin(admin.ModelAdmin):
    list_display = ['client', 'date_creation', 'date_modification', 'nombre_articles', 'total']
    readonly_fields = ['date_creation', 'date_modification']
    search_fields = ['client__user__username']

@admin.register(ArticlePanier)
class ArticlePanierAdmin(admin.ModelAdmin):
    list_display = ['panier', 'produit', 'quantite', 'sous_total', 'date_ajout']
    readonly_fields = ['date_ajout']
    list_filter = ['produit__commercant']
    search_fields = ['panier__client__user__username', 'produit__nom']


class CommandeAdminForm(forms.ModelForm):
    class Meta:
        model = Commande
        fields = '__all__'

@admin.register(Commande)
class CommandeAdmin(GISModelAdmin):
    form = CommandeAdminForm
    list_display = [
        'reference', 'client', 'commercant', 'total', 'statut', 
        'statut_paiement', 'methode_paiement', 'date_commande', 
        'a_coordonnees_livraison', 'source_coordonnees'
    ]
    list_filter = ['statut', 'statut_paiement', 'methode_paiement', 'date_commande', 'commercant']
    search_fields = ['reference', 'client__user__username', 'commercant__nom_boutique']
    readonly_fields = ['date_commande', 'date_modification', 'reference', 'source_coordonnees']
    date_hierarchy = 'date_commande'
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('reference', 'client', 'commercant', 'statut', 'total')
        }),
        ('Livraison', {
            'fields': (
                'adresse_livraison', 
                'latitude_livraison', 
                'longitude_livraison',
                'point_livraison',
                'instructions_livraison'
            )
        }),
        ('Paiement', {
            'fields': (
                'methode_paiement', 
                'statut_paiement',
                'paygate_reference',
                'paygate_status',
                'paygate_network',
                'paygate_phone'
            )
        }),
        ('Dates', {
            'fields': ('date_commande', 'date_modification')
        }),
    )
    
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
    list_filter = ['commande__commercant', 'produit__categorie']
    search_fields = ['commande__reference', 'produit__nom']

@admin.register(Favori)
class FavoriAdmin(admin.ModelAdmin):
    list_display = ['client', 'produit', 'date_ajout']
    readonly_fields = ['date_ajout']
    list_filter = ['date_ajout']
    search_fields = ['client__user__username', 'produit__nom']

@admin.register(Avis)
class AvisAdmin(admin.ModelAdmin):
    list_display = ['client', 'produit', 'note', 'est_approuve', 'date_creation']
    list_filter = ['note', 'est_approuve', 'date_creation']
    search_fields = ['client__user__username', 'produit__nom']
    readonly_fields = ['date_creation']
    actions = ['approuver_avis', 'desapprouver_avis']

    def approuver_avis(self, request, queryset):
        queryset.update(est_approuve=True)
        self.message_user(request, f"{queryset.count()} avis approuvés avec succès.")
    approuver_avis.short_description = "Approuver les avis sélectionnés"

    def desapprouver_avis(self, request, queryset):
        queryset.update(est_approuve=False)
        self.message_user(request, f"{queryset.count()} avis désapprouvés avec succès.")
    desapprouver_avis.short_description = "Désapprouver les avis sélectionnés"

@admin.register(Portefeuille)
class PortefeuilleAdmin(admin.ModelAdmin):
    list_display = ['user', 'solde', 'date_creation', 'date_modification', 'total_transactions']
    readonly_fields = ['date_creation', 'date_modification', 'total_transactions']
    search_fields = ['user__username', 'user__email']
    list_filter = ['date_creation']
    
    def total_transactions(self, obj):
        return obj.transactions.count()
    total_transactions.short_description = "Nb transactions"

@admin.register(TransactionPortefeuille)
class TransactionPortefeuilleAdmin(admin.ModelAdmin):
    list_display = ['portefeuille', 'type_transaction', 'montant', 'solde_apres', 'date_transaction', 'description_courte']
    list_filter = ['type_transaction', 'date_transaction']
    search_fields = ['portefeuille__user__username', 'description']
    readonly_fields = ['date_transaction']
    date_hierarchy = 'date_transaction'
    
    def description_courte(self, obj):
        return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description
    description_courte.short_description = "Description"

@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = [
        'commande', 'montant_commande', 'commission_plateforme', 
        'montant_commercant', 'taux_commission', 'est_transfere', 
        'date_calcul', 'date_transfert'
    ]
    list_filter = ['est_transfere', 'date_calcul', 'date_transfert']
    search_fields = ['commande__reference', 'commande__commercant__nom_boutique']
    readonly_fields = ['date_calcul']
    actions = ['marquer_comme_transfere', 'marquer_comme_non_transfere']
    
    def marquer_comme_transfere(self, request, queryset):
        updated = queryset.update(est_transfere=True, date_transfert=timezone.now())
        self.message_user(request, f"{updated} commissions marquées comme transférées.")
    marquer_comme_transfere.short_description = "Marquer comme transférées"

    def marquer_comme_non_transfere(self, request, queryset):
        updated = queryset.update(est_transfere=False, date_transfert=None)
        self.message_user(request, f"{updated} commissions marquées comme non transférées.")
    marquer_comme_non_transfere.short_description = "Marquer comme non transférées"

@admin.register(DepotPortefeuille)
class DepotPortefeuilleAdmin(admin.ModelAdmin):
    list_display = [
        'portefeuille', 'montant', 'methode', 'statut', 
        'numero_transaction', 'date_depot', 'date_validation'
    ]
    list_filter = ['methode', 'statut', 'date_depot', 'operateur']
    search_fields = [
        'portefeuille__user__username', 
        'numero_transaction',
        'numero_telephone'
    ]
    readonly_fields = ['date_depot']
    date_hierarchy = 'date_depot'
    actions = ['valider_depots', 'annuler_depots']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('portefeuille', 'montant', 'methode', 'statut')
        }),
        ('Détails du paiement', {
            'fields': ('numero_transaction', 'operateur', 'numero_telephone')
        }),
        ('Suivi', {
            'fields': ('date_depot', 'date_validation', 'notes')
        }),
    )
    
    def valider_depots(self, request, queryset):
        depots_valides = 0
        for depot in queryset.filter(statut='en_attente'):
            if depot.valider():
                depots_valides += 1
        self.message_user(request, f"{depots_valides} dépôts validés avec succès.")
    valider_depots.short_description = "Valider les dépôts sélectionnés"

    def annuler_depots(self, request, queryset):
        updated = queryset.filter(statut='en_attente').update(statut='annule')
        self.message_user(request, f"{updated} dépôts annulés.")
    annuler_depots.short_description = "Annuler les dépôts sélectionnés"

@admin.register(RetraitCommercant)
class RetraitCommercantAdmin(admin.ModelAdmin):
    list_display = [
        'portefeuille', 'montant', 'methode', 'statut', 
        'montant_net', 'frais_retrait', 'date_demande', 'date_traitement'
    ]
    list_filter = ['methode', 'statut', 'date_demande', 'operateur']
    search_fields = [
        'portefeuille__user__username', 
        'numero_compte',
        'nom_beneficiaire'
    ]
    readonly_fields = ['date_demande']
    date_hierarchy = 'date_demande'
    actions = ['traiter_retraits', 'valider_retraits', 'rejeter_retraits']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('portefeuille', 'montant', 'methode', 'statut')
        }),
        ('Détails du retrait', {
            'fields': ('numero_compte', 'operateur', 'nom_beneficiaire')
        }),
        ('Calculs', {
            'fields': ('frais_retrait', 'montant_net')
        }),
        ('Suivi', {
            'fields': ('date_demande', 'date_traitement', 'notes_admin')
        }),
    )
    
    def traiter_retraits(self, request, queryset):
        retraits_traites = 0
        for retrait in queryset.filter(statut='en_attente'):
            if retrait.traiter():
                retraits_traites += 1
        self.message_user(request, f"{retraits_traites} retraits traités avec succès.")
    traiter_retraits.short_description = "Traiter les retraits sélectionnés"

    def valider_retraits(self, request, queryset):
        updated = queryset.filter(statut='en_attente').update(statut='valide')
        self.message_user(request, f"{updated} retraits validés.")
    valider_retraits.short_description = "Valider les retraits (sans traitement)"

    def rejeter_retraits(self, request, queryset):
        updated = queryset.filter(statut='en_attente').update(statut='echec')
        self.message_user(request, f"{updated} retraits rejetés.")
    rejeter_retraits.short_description = "Rejeter les retraits sélectionnés"

    def save_model(self, request, obj, form, change):
        # Recalculer les frais si le montant change
        if 'montant' in form.changed_data:
            obj.calculer_frais()
        super().save_model(request, obj, form, change)

# Tableau de bord personnalisé
class TableauBordAdmin(admin.AdminSite):
    site_header = "Administration Local-Links"
    site_title = "Tableau de bord Local-Links"
    index_title = "Tableau de bord"

    def index(self, request, extra_context=None):
        # Statistiques pour le tableau de bord
        stats = {
            'total_clients': Client.objects.count(),
            'total_commandes': Commande.objects.count(),
            'total_portefeuilles': Portefeuille.objects.count(),
            'total_depots': DepotPortefeuille.objects.filter(statut='valide').count(),
            'total_retraits': RetraitCommercant.objects.filter(statut='traite').count(),
            'solde_total_plateforme': Portefeuille.objects.aggregate(Sum('solde'))['solde__sum'] or 0,
            'commissions_total': Commission.objects.filter(est_transfere=True).aggregate(Sum('commission_plateforme'))['commission_plateforme__sum'] or 0,
        }
        
        # Dépôts en attente
        depots_en_attente = DepotPortefeuille.objects.filter(statut='en_attente')[:5]
        
        # Retraits en attente
        retraits_en_attente = RetraitCommercant.objects.filter(statut='en_attente')[:5]
        
        extra_context = {
            'stats': stats,
            'depots_en_attente': depots_en_attente,
            'retraits_en_attente': retraits_en_attente,
        }
        
        return super().index(request, extra_context)

# Enregistrement des modèles avec des groupes logiques
admin.site.site_header = "Administration Local-Links"
admin.site.site_title = "Tableau de bord Local-Links"
admin.site.index_title = "Tableau de bord"

