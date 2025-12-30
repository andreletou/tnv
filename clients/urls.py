from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'clients'

urlpatterns = [
    path('redirection/', views.redirection_apres_connexion, name='redirection_apres_connexion'),
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

    path('commande/<int:commande_id>/paiement/choix/', views.choix_paiement, name='choix_paiement'),
    path('commande/<int:commande_id>/paiement/mobile/<str:network>/', views.paiement_mobile, name='paiement_mobile'),

    # Portefeuille
    path('portefeuille/', views.portefeuille, name='portefeuille'),
    path('api/portefeuille/solde/', views.api_solde_portefeuille, name='api_solde_portefeuille'),
    path('api/portefeuille/historique/', views.api_historique_portefeuille, name='api_historique_portefeuille'),
    path('commande/multiple/confirmation/', views.commandes_multiple_confirmation, name='commandes_multiple_confirmation'),
        
    path('commande/<int:commande_id>/verification-paiement/', views.verification_paiement, name='verification_paiement'),

    path('notifications/', views.notifications, name='notifications'),
    path('parametres/', views.parametres, name='parametres'),
    path('api/panier/info/', views.api_panier_info, name='api_panier_info'),
    
    # API de vérification (JSON)
    path('api/commande/<int:commande_id>/verification-paiement/', 
         views.api_verification_paiement, 
         name='api_verification_paiement'),

    path('webhook/paygate/', views.webhook_paygate, name='webhook_paygate'),

    # Dépôts et retraits
    path('portefeuille/depot/', views.depot_portefeuille, name='depot_portefeuille'),
    path('portefeuille/depot/mobile-money/', views.depot_mobile_money, name='depot_mobile_money'),
    path('portefeuille/depot/paygate/', views.depot_paygate, name='depot_paygate'),
    path('portefeuille/depot/verification/<int:depot_id>/', views.verification_depot, name='verification_depot'),
    path('portefeuille/retrait/demande/', views.demande_retrait, name='demande_retrait'),
    path('portefeuille/retrait/historique/', views.historique_retraits, name='historique_retraits'),

    # API Portefeuille
    path('api/portefeuille/solde/', views.api_solde_portefeuille, name='api_solde_portefeuille'),
    path('api/portefeuille/historique/', views.api_historique_portefeuille, name='api_historique_portefeuille'),
    path('api/portefeuille/depots/', views.api_historique_depots, name='api_historique_depots'),
    path('portefeuille/depot/verifier/<int:depot_id>/', views.verifier_statut_depot, name='verifier_statut_depot'),

    # path('portefeuille/debug/depot/<int:depot_id>/', views.debug_depot, name='debug_depot'),
]