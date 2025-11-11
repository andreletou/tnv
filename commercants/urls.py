from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'commercants'

urlpatterns = [
    # Authentification
    path('inscription/', views.inscription_commercant, name='inscription'),
    path('connexion/', auth_views.LoginView.as_view(template_name='commercants/connexion.html'), name='connexion'),
    path('deconnexion/', auth_views.LogoutView.as_view(), name='deconnexion'),
    
    # Tableau de bord
    path('', views.tableau_de_bord, name='tableau_de_bord'),
    
    # Gestion des produits
    path('produits/', views.liste_produits, name='liste_produits'),
    path('produits/ajouter/', views.ajouter_produit, name='ajouter_produit'),
    path('produits/<int:pk>/modifier/', views.modifier_produit, name='modifier_produit'),
    path('produits/<int:pk>/supprimer/', views.supprimer_produit, name='supprimer_produit'),
    
    # Gestion des promotions
    path('promotions/', views.liste_promotions, name='liste_promotions'),
    path('promotions/ajouter/', views.ajouter_promotion, name='ajouter_promotion'),
    path('promotions/<int:pk>/modifier/', views.modifier_promotion, name='modifier_promotion'),
    path('promotions/<int:pk>/supprimer/', views.supprimer_promotion, name='supprimer_promotion'),
    
    # Profil
    path('profil/', views.profil, name='profil'),
    path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
    
    # API Endpoints
    path('api/statistiques/', views.api_statistiques, name='api_statistiques'),
    path('api/commandes/', views.api_commandes, name='api_commandes'),
    path('api/produits/', views.api_produits, name='api_produits'),
    path('api/commande/<int:commande_id>/', views.api_detail_commande, name='api_detail_commande'),
    path('api/commande/<int:commande_id>/statut/', views.api_changer_statut_commande, name='api_changer_statut_commande'),
    path('api/produits/stats/', views.api_stats_produits, name='api_stats_produits'),
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    path('api/promotions/', views.api_promotions, name='api_promotions'),

    # Gestion des commandes
    path('commandes/', views.gestion_commandes, name='gestion_commandes'),
    path('commandes/<int:commande_id>/', views.detail_commande_commercant, name='detail_commande_commercant'),
    path('api/commandes/<int:commande_id>/valider/', views.api_valider_commande, name='api_valider_commande'),
    path('api/commandes/<int:commande_id>/refuser/', views.api_refuser_commande, name='api_refuser_commande'),
    path('api/commandes/<int:commande_id>/preparer/', views.api_preparer_commande, name='api_preparer_commande'),
    path('api/commandes/<int:commande_id>/prete/', views.api_commande_prete, name='api_commande_prete'),

]