# urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'livraisons'

urlpatterns = [
    # Authentification
    path('inscription/', views.inscription_livreur, name='inscription'),
    path('connexion/', auth_views.LoginView.as_view(template_name='livraisons/connexion.html'), name='login'),
    path('deconnexion/', auth_views.LogoutView.as_view(), name='deconnexion'),
    
    # Pages principales
    path('', views.tableau_de_bord, name='tableau_de_bord'),
    path('profil/', views.profil, name='profil'),
    path('carte/', views.carte_livraisons, name='carte_livraisons'),
    path('livraisons/', views.gestion_livraisons, name='gestion_livraisons'),
    
    # Actions de livraison
    path('livraison/<int:livraison_id>/action/', views.action_livraison, name='action_livraison'),
    path('notifications/', views.notifications, name='notifications'),
    path('livraison/<int:livraison_id>/detail/', views.detail_livraison_modal, name='detail_livraison_modal'),
    
    # API Google Maps
    path('api/google-maps/geocode/', views.api_google_geocode, name='api_google_geocode'),
    path('api/google-maps/directions/', views.api_google_directions, name='api_google_directions'),
    path('api/google-maps/optimize-route/', views.api_google_optimize_route, name='api_google_optimize_route'),
    path('api/google-maps/distance-matrix/', views.api_google_distance_matrix, name='api_google_distance_matrix'),
    
    # API Endpoints
    path('api/position/', views.api_position, name='api_position'),
    path('api/disponibilite/', views.api_disponibilite, name='api_disponibilite'),
    path('api/livraisons/', views.api_livraisons, name='api_livraisons'),
    path('api/itineraire/', views.api_itineraire, name='api_itineraire'),
    path('api/optimisation/', views.api_optimisation, name='api_optimisation'),
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    path('api/statistiques/', views.api_statistiques, name='api_statistiques'),
    path('api/signalements/', views.api_signalements, name='api_signalements'),
    
    # API GeoJSON
    path('api/geojson/livraisons/', views.api_geojson_livraisons, name='api_geojson_livraisons'),
    path('api/geojson/livreurs/', views.api_geojson_livreurs, name='api_geojson_livreurs'),
    path('api/geojson/zones/', views.api_geojson_zones, name='api_geojson_zones'),
]