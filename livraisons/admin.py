from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin
from django.utils.html import format_html
from django.db.models import Avg, Count
from .models import Livreur, Livraison, PositionLivreur, EvaluationLivreur, NotificationLivreur


@admin.register(Livreur)
class LivreurAdmin(admin.ModelAdmin):
    list_display = [
        'username', 'email', 'telephone', 'type_vehicule', 
        'est_disponible', 'est_en_ligne', 'note_moyenne', 
        'nombre_livraisons', 'date_inscription'
    ]
    list_filter = [
        'type_vehicule', 'est_disponible', 'est_en_ligne', 
        'est_actif', 'date_inscription'
    ]
    search_fields = ['username', 'email', 'first_name', 'last_name', 'telephone']
    readonly_fields = ['note_moyenne', 'nombre_livraisons', 'date_inscription']
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('username', 'email', 'first_name', 'last_name', 'telephone')
        }),
        ('Véhicule', {
            'fields': ('type_vehicule', 'immatriculation', 'photo_profil')
        }),
        ('Documents', {
            'fields': ('permis_conduire', 'carte_grise')
        }),
        ('Statut', {
            'fields': ('est_disponible', 'est_en_ligne', 'est_actif')
        }),
        ('Position', {
            'fields': ('position_actuelle', 'derniere_position_mise_a_jour')
        }),
        ('Statistiques', {
            'fields': ('note_moyenne', 'nombre_livraisons', 'date_inscription'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            avg_note=Avg('livraisons__evaluation__note'),
            liv_count=Count('livraisons')
        )
    
    def note_moyenne(self, obj):
        return f"{obj.note_moyenne}/5" if obj.note_moyenne else "N/A"
    note_moyenne.short_description = "Note moyenne"
    
    def nombre_livraisons(self, obj):
        return obj.livraisons.count()
    nombre_livraisons.short_description = "Livraisons"


@admin.register(Livraison)
class LivraisonAdmin(OSMGeoAdmin):
    list_display = [
        'id', 'commande', 'livreur', 'statut', 'date_attribution',
        'cout_livraison', 'distance_estimee'
    ]
    list_filter = [
        'statut', 'date_attribution', 'cout_livraison'
    ]
    search_fields = [
        'commande__reference', 'livreur__username', 
        'commande__client__first_name'
    ]
    readonly_fields = [
        'date_attribution', 'date_acceptation', 
        'date_debut_livraison', 'date_fin_livraison'
    ]
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('commande', 'livreur', 'statut')
        }),
        ('Dates', {
            'fields': (
                'date_attribution', 'date_acceptation',
                'date_debut_livraison', 'date_fin_livraison'
            ),
            'classes': ('collapse',)
        }),
        ('Coûts et distances', {
            'fields': ('cout_livraison', 'distance_estimee', 'duree_estimee')
        }),
        ('Localisation', {
            'fields': ('adresse_livraison_point', 'boutique_point')
        }),
        ('Détails', {
            'fields': ('instructions_speciales', 'preuve_livraison', 'signature_client')
        })
    )
    
    default_lon = 1.2225  # Longitude de Lomé
    default_lat = 6.1319   # Latitude de Lomé
    default_zoom = 12


@admin.register(PositionLivreur)
class PositionLivreurAdmin(OSMGeoAdmin):
    list_display = ['livreur', 'timestamp', 'vitesse']
    list_filter = ['timestamp']
    search_fields = ['livreur__username']
    readonly_fields = ['timestamp']
    
    default_lon = 1.2225
    default_lat = 6.1319
    default_zoom = 12


@admin.register(EvaluationLivreur)
class EvaluationLivreurAdmin(admin.ModelAdmin):
    list_display = [
        'livraison', 'note', 'ponctualite', 'professionalisme', 
        'securite', 'date_evaluation'
    ]
    list_filter = [
        'note', 'ponctualite', 'professionalisme', 'securite', 'date_evaluation'
    ]
    search_fields = [
        'livraison__livreur__username', 'livraison__commande__reference'
    ]
    readonly_fields = ['date_evaluation']
    
    fieldsets = (
        ('Livraison', {
            'fields': ('livraison',)
        }),
        ('Évaluations', {
            'fields': ('note', 'ponctualite', 'professionalisme', 'securite')
        }),
        ('Commentaires', {
            'fields': ('commentaire',)
        }),
        ('Métadonnées', {
            'fields': ('date_evaluation',),
            'classes': ('collapse',)
        })
    )


@admin.register(NotificationLivreur)
class NotificationLivreurAdmin(admin.ModelAdmin):
    list_display = [
        'livreur', 'type_notification', 'titre', 'est_lue', 'date_creation'
    ]
    list_filter = [
        'type_notification', 'est_lue', 'date_creation'
    ]
    search_fields = [
        'livreur__username', 'titre', 'message'
    ]
    readonly_fields = ['date_creation']
    
    fieldsets = (
        ('Destinataire', {
            'fields': ('livreur',)
        }),
        ('Notification', {
            'fields': ('type_notification', 'titre', 'message')
        }),
        ('Statut', {
            'fields': ('est_lue',)
        }),
        ('Données supplémentaires', {
            'fields': ('donnees_supplementaires',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('date_creation',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('livreur')


# Personnalisation de l'interface admin
admin.site.site_header = "Administration - Livraison Express"
admin.site.site_title = "Livraison Express"
admin.site.index_title = "Gestion des livraisons"