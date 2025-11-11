from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'clients'

urlpatterns = [
    # Page d'accueil
    path('', views.accueil, name='accueil'),
    
    # Authentification
    path('inscription/', views.inscription_client, name='inscription'),
    path('connexion/', auth_views.LoginView.as_view(template_name='clients/connexion.html'), name='connexion'),
    path('deconnexion/', auth_views.LogoutView.as_view(), name='deconnexion'),
    
    # Boutique et produits
    path('boutiques/', views.liste_boutiques, name='liste_boutiques'),
    path('boutique/<int:boutique_id>/', views.detail_boutique, name='detail_boutique'),
    path('produit/<int:produit_id>/', views.detail_produit, name='detail_produit'),
    path('recherche/', views.recherche, name='recherche'),
    path('api/geolocalisation/mettre-a-jour/', views.api_mettre_a_jour_geolocalisation, name='api_mettre_a_jour_geolocalisation'),
    
    # Panier
    path('panier/', views.panier, name='panier'),
    path('panier/ajouter/<int:produit_id>/', views.ajouter_au_panier, name='ajouter_au_panier'),
    path('panier/modifier/<int:item_id>/', views.modifier_panier, name='modifier_panier'),
    path('panier/supprimer/<int:item_id>/', views.supprimer_du_panier, name='supprimer_du_panier'),
    
    # Commandes
    path('commande/finaliser/', views.finaliser_commande, name='finaliser_commande'),  # NOUVEAU
    path('commande/confirmation/<int:commande_id>/', views.confirmation_commande, name='confirmation_commande'),  # NOUVEAU
    path('commande/passer/', views.passer_commande, name='passer_commande'),
    path('commandes/', views.mes_commandes, name='mes_commandes'),
    path('commande/<int:commande_id>/', views.detail_commande, name='detail_commande'),
    
    # Favoris
    path('favoris/', views.mes_favoris, name='mes_favoris'),
    path('favoris/ajouter/<int:produit_id>/', views.ajouter_favori, name='ajouter_favori'),
    path('favoris/supprimer/<int:produit_id>/', views.supprimer_favori, name='supprimer_favori'),
    
    # Profil
    path('profil/', views.profil, name='profil'),
    path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
    
    # API Endpoints
    path('api/panier/ajouter/', views.api_ajouter_au_panier, name='api_ajouter_au_panier'),
    path('api/panier/modifier/', views.api_modifier_panier, name='api_modifier_panier'),
    path('api/panier/supprimer/', views.api_supprimer_du_panier, name='api_supprimer_du_panier'),
    path('api/panier/infos/', views.api_infos_panier, name='api_infos_panier'),
    path('api/favoris/ajouter/', views.api_ajouter_favori, name='api_ajouter_favori'),
    path('api/favoris/supprimer/', views.api_supprimer_favori, name='api_supprimer_favori'),
    path('api/avis/ajouter/', views.api_ajouter_avis, name='api_ajouter_avis'),
    path('api/produits/suggestions/', views.api_produits_suggestions, name='api_produits_suggestions'),
    path('api/commande/statut/', views.api_changer_statut_commande, name='api_changer_statut_commande'),
]