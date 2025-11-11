from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'livraisons'

urlpatterns = [
    # Authentification
    path('inscription/', views.inscription_livreur, name='inscription'),
    path('connexion/', auth_views.LoginView.as_view(template_name='livraisons/connexion.html'), name='login'),
    path('deconnexion/', auth_views.LogoutView.as_view(), name='deconnexion'),
    
    # Tableau de bord et profil
    path('tableau-de-bord/', views.tableau_de_bord, name='tableau_de_bord'),
    path('profil/', views.profil, name='profil'),
    path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
    
    # Carte et localisation
    path('carte/', views.carte_interactive, name='carte'),
    path('carte/boutiques/', views.api_boutiques_carte, name='api_boutiques_carte'),
    path('carte/livraisons/', views.api_livraisons_carte, name='api_livraisons_carte'),
    
    # Gestion des livraisons
    path('livraisons/', views.liste_livraisons, name='liste_livraisons'),
    path('livraisons/disponibles/', views.livraisons_disponibles, name='livraisons_disponibles'),
    path('livraisons/<int:livraison_id>/', views.detail_livraison, name='detail_livraison'),
    path('livraisons/<int:livraison_id>/accepter/', views.accepter_livraison, name='accepter_livraison'),
    path('livraisons/<int:livraison_id>/commencer/', views.commencer_livraison, name='commencer_livraison'),
    path('livraisons/<int:livraison_id>/terminer/', views.terminer_livraison, name='terminer_livraison'),
    path('livraisons/<int:livraison_id>/annuler/', views.annuler_livraison, name='annuler_livraison'),
    path('livraisons/<int:livraison_id>/itineraire/', views.itineraire_livraison, name='itineraire_livraison'),
    
    # Historique et statistiques
    path('historique/', views.historique_livraisons, name='historique'),
    path('statistiques/', views.statistiques, name='statistiques'),
    path('evaluations/', views.evaluations, name='evaluations'),
    
    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notification_id>/lire/', views.marquer_notification_lue, name='marquer_notification_lue'),
    
    # API Endpoints
    path('api/position/mettre-a-jour/', views.api_mettre_a_jour_position, name='api_mettre_a_jour_position'),
    path('api/disponibilite/', views.api_gerer_disponibilite, name='api_gerer_disponibilite'),
    path('api/livraisons/disponibles/', views.api_livraisons_disponibles, name='api_livraisons_disponibles'),
    path('api/livraisons/proches/', views.api_livraisons_proches, name='api_livraisons_proches'),
    path('api/itineraire/<int:livraison_id>/', views.api_itineraire, name='api_itineraire'),
    path('api/position/historique/', views.api_historique_positions, name='api_historique_positions'),
    path('api/statistiques/', views.api_statistiques, name='api_statistiques'),
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    path('api/evaluations/ajouter/', views.api_ajouter_evaluation, name='api_ajouter_evaluation'),
    
    # Suivi en temps réel (WebSocket)
    path('suivi/<int:livraison_id>/', views.suivi_livraison, name='suivi_livraison'),
]