# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
import json
import requests
from datetime import datetime, timedelta
from decimal import Decimal

from .forms import (
    LivreurInscriptionForm, ProfilLivreurForm, PositionForm,
    LivraisonForm, EvaluationLivreurForm, DisponibiliteForm
)
from .models import (
    Livreur, Livraison, PositionLivreur, EvaluationLivreur, 
    NotificationLivreur, ZoneLivraison, TourneeLivraison
)
from django.conf import settings
GOOGLE_MAPS_API_KEY = settings.GOOGLE_MAPS_API_KEY

class GoogleMapsService:
    """Service pour interagir avec Google Maps API"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or GOOGLE_MAPS_API_KEY
        self.base_url = "https://maps.googleapis.com/maps/api"
    
    def calculer_itineraire(self, origine, destination, mode='driving'):
        """Calculer l'itinéraire entre deux points"""
        try:
            url = f"{self.base_url}/directions/json"
            params = {
                'origin': f"{origine[0]},{origine[1]}",
                'destination': f"{destination[0]},{destination[1]}",
                'mode': mode,
                'key': self.api_key,
                'alternatives': True
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == 'OK':
                return data['routes'][0]  # Prendre le premier itinéraire
            else:
                print(f"Erreur Google Maps: {data['status']}")
                return None
                
        except Exception as e:
            print(f"Erreur API Google Maps: {e}")
            return None
    
    def geocoder_adresse(self, adresse):
        """Géocoder une adresse en coordonnées"""
        try:
            url = f"{self.base_url}/geocode/json"
            params = {
                'address': adresse,
                'key': self.api_key
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == 'OK':
                location = data['results'][0]['geometry']['location']
                return (location['lat'], location['lng'])
            else:
                print(f"Erreur géocodage: {data['status']}")
                return None
                
        except Exception as e:
            print(f"Erreur géocodage Google Maps: {e}")
            return None
    
    def optimiser_tournee(self, waypoints, origine=None, mode='driving'):
        """Optimiser une tournée avec Google Maps"""
        try:
            url = f"{self.base_url}/directions/json"
            
            waypoints_str = '|'.join([f"optimize:true|{lat},{lng}" for lat, lng in waypoints])
            
            params = {
                'origin': f"{origine[0]},{origine[1]}" if origine else f"{waypoints[0][0]},{waypoints[0][1]}",
                'destination': f"{origine[0]},{origine[1]}" if origine else f"{waypoints[0][0]},{waypoints[0][1]}",
                'waypoints': waypoints_str,
                'mode': mode,
                'key': self.api_key,
                'optimizeWaypoints': True
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == 'OK':
                return data['routes'][0]
            else:
                print(f"Erreur optimisation: {data['status']}")
                return None
                
        except Exception as e:
            print(f"Erreur optimisation Google Maps: {e}")
            return None
    
    def calculer_distance_matrix(self, origins, destinations, mode='driving'):
        """Calculer la matrice de distances"""
        try:
            url = f"{self.base_url}/distancematrix/json"
            params = {
                'origins': '|'.join([f"{lat},{lng}" for lat, lng in origins]),
                'destinations': '|'.join([f"{lat},{lng}" for lat, lng in destinations]),
                'mode': mode,
                'key': self.api_key
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == 'OK':
                return data
            else:
                print(f"Erreur distance matrix: {data['status']}")
                return None
                
        except Exception as e:
            print(f"Erreur distance matrix Google Maps: {e}")
            return None

# Instance globale du service
google_maps_service = GoogleMapsService(api_key=GOOGLE_MAPS_API_KEY)

# Vues principales
def inscription_livreur(request):
    """Inscription des livreurs"""
    if request.method == 'POST':
        form = LivreurInscriptionForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Bienvenue ! Votre compte livreur a été créé.')
            return redirect('livraisons:tableau_de_bord')
    else:
        form = LivreurInscriptionForm()
    
    return render(request, 'livraisons/inscription.html', {
        'form': form,
        'google_maps_api_key': GOOGLE_MAPS_API_KEY
    })
@login_required
def tableau_de_bord(request):
    """Tableau de bord unifié avec Google Maps"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Profil livreur non trouvé.')
        return redirect('livraisons:inscription')
    
    # Statistiques rapides
    stats = Livraison.objects.filter(
        livreur=livreur,
        date_attribution__date=timezone.now().date()
    ).aggregate(
        total=Count('id'),
        en_cours=Count('id', filter=Q(statut__in=['acceptee', 'en_cours'])),
        terminees=Count('id', filter=Q(statut='terminee'))
    )
    
    # Calcul des gains du jour
    gains_du_jour = Livraison.objects.filter(
        livreur=livreur,
        statut='terminee',
        date_attribution__date=timezone.now().date()
    ).aggregate(total_gains=Sum('cout_livraison'))['total_gains'] or 0
    
    contexte = {
        'livreur': livreur,
        'livraisons_en_cours': Livraison.objects.filter(
            livreur=livreur, 
            statut__in=['acceptee', 'en_cours']
        )[:5],
        'livraisons_disponibles': Livraison.objects.filter(
            livreur__isnull=True,
            statut='attribuee'
        )[:5],
        'notifications_non_lues': NotificationLivreur.objects.filter(
            livreur=livreur, est_lue=False
        ).count(),
        'stats_jour': stats,
        'gains_du_jour': gains_du_jour,
        'google_maps_api_key': GOOGLE_MAPS_API_KEY,
    }
    
    return render(request, 'livraisons/tableau_de_bord.html', contexte)

@login_required
def profil(request):
    """Gestion du profil livreur"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Profil livreur non trouvé.')
        return redirect('livraisons:inscription')
    
    if request.method == 'POST':
        form = ProfilLivreurForm(request.POST, request.FILES, instance=livreur)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès.')
            return redirect('livraisons:profil')
    else:
        form = ProfilLivreurForm(instance=livreur)
    
    return render(request, 'livraisons/profil.html', {
        'livreur': livreur,
        'form': form,
        'google_maps_api_key': GOOGLE_MAPS_API_KEY,
    })

# views.py - Modifier la vue carte_livraisons
@login_required
def carte_livraisons(request):
    """Carte interactive avec Google Maps"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Profil livreur non trouvé.')
        return redirect('livraisons:inscription')
    
    # Récupérer la première livraison en cours pour ce livreur
    livraison_en_cours = Livraison.objects.filter(
        livreur=livreur,
        statut__in=['acceptee', 'en_cours']
    ).first()
    
    # Récupérer toutes les livraisons du livreur
    livraisons_du_livreur = Livraison.objects.filter(
        livreur=livreur
    )[:10]
    
    # Préparer les données de livraison pour le template
    livraison_data = None
    if livraison_en_cours:
        livraison_data = {
            'id': livraison_en_cours.id,
            'statut': livraison_en_cours.statut,
            'statut_display': livraison_en_cours.get_statut_display(),
            'cout_livraison': float(livraison_en_cours.cout_livraison or 0),
            'instructions_speciales': livraison_en_cours.instructions_speciales or "",
            'date_attribution': livraison_en_cours.date_attribution,
            'boutique_point': livraison_en_cours.boutique_point,
            'adresse_livraison_point': livraison_en_cours.adresse_livraison_point,
            'commande': {
                'reference': livraison_en_cours.commande.reference if livraison_en_cours.commande else "N/A",
                'total': float(livraison_en_cours.commande.total) if livraison_en_cours.commande and hasattr(livraison_en_cours.commande, 'total') else 0,
                'adresse_livraison': livraison_en_cours.commande.adresse_livraison if livraison_en_cours.commande else "Adresse non disponible",
                'client': {
                    'first_name': livraison_en_cours.commande.client.first_name if livraison_en_cours.commande and livraison_en_cours.commande.client else "",
                    'last_name': livraison_en_cours.commande.client.last_name if livraison_en_cours.commande and livraison_en_cours.commande.client else "",
                    'telephone': getattr(livraison_en_cours.commande.client, 'telephone', '') if livraison_en_cours.commande and livraison_en_cours.commande.client else ""
                } if livraison_en_cours.commande else {'first_name': '', 'last_name': '', 'telephone': ''},
                'boutique': {
                    'adresse': getattr(livraison_en_cours.commande.boutique, 'adresse', 'Boutique') if livraison_en_cours.commande and livraison_en_cours.commande.boutique else "Boutique",
                    'telephone': getattr(livraison_en_cours.commande.boutique, 'telephone', '') if livraison_en_cours.commande and livraison_en_cours.commande.boutique else ""
                } if livraison_en_cours.commande else {'adresse': 'Boutique', 'telephone': ''}
            }
        }
    else:
        # Créer un objet vide avec des valeurs par défaut
        livraison_data = {
            'id': 0,
            'statut': 'aucune',
            'statut_display': 'Aucune livraison',
            'cout_livraison': 0,
            'instructions_speciales': "",
            'date_attribution': None,
            'boutique_point': None,
            'adresse_livraison_point': None,
            'commande': {
                'reference': "N/A",
                'total': 0,
                'adresse_livraison': "Adresse non disponible",
                'client': {
                    'first_name': '',
                    'last_name': '',
                    'telephone': ''
                },
                'boutique': {
                    'adresse': 'Boutique',
                    'telephone': ''
                }
            }
        }
    
    contexte = {
        'livreur': livreur,
        'livraison': livraison_data,
        'livraisons': livraisons_du_livreur,
        'google_maps_api_key': GOOGLE_MAPS_API_KEY,
    }
    
    return render(request, 'livraisons/carte.html', contexte)

# views.py - Ajouter cette vue
@login_required
@require_POST
def api_signalements(request):
    """API pour signaler un problème"""
    try:
        livreur = request.user.livreur
        livraison_id = request.POST.get('livraison_id')
        type_probleme = request.POST.get('type_probleme')
        description = request.POST.get('description', '')
        
        if not type_probleme:
            return JsonResponse({'success': False, 'message': 'Type de problème requis'})
        
        # Créer le signalement
        signalement = SignalementProbleme.objects.create(
            livreur=livreur,
            livraison_id=livraison_id if livraison_id else None,
            type_probleme=type_probleme,
            description=description
        )
        
        # Gérer le fichier photo s'il existe
        if 'photo' in request.FILES:
            signalement.photo = request.FILES['photo']
            signalement.save()
        
        # Enregistrer la position actuelle
        if livreur.position_actuelle:
            signalement.latitude = livreur.position_actuelle.y
            signalement.longitude = livreur.position_actuelle.x
            signalement.save()
        
        return JsonResponse({'success': True, 'message': 'Problème signalé avec succès'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

def notifications(request):
    """Afficher les notifications du livreur"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Profil livreur non trouvé.')
        return redirect('livraisons:inscription')
    
    notifications = NotificationLivreur.objects.filter(
        livreur=livreur
    ).order_by('-date_creation')[:50]
    
    # Marquer toutes les notifications comme lues
    notifications.update(est_lue=True)
    
    return render(request, 'livraisons/notifications.html', {
        'livreur': livreur,
        'notifications': notifications,
        'google_maps_api_key': GOOGLE_MAPS_API_KEY,
    })
@login_required
def gestion_livraisons(request):
    """Gestion des livraisons avec calculs Google Maps"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Profil livreur non trouvé.')
        return redirect('livraisons:inscription')
    
    filtre = request.GET.get('filtre', 'toutes')
    recherches = {
        'toutes': Livraison.objects.filter(livreur=livreur),
        'en_cours': Livraison.objects.filter(livreur=livreur, statut__in=['acceptee', 'en_cours']),
        'terminees': Livraison.objects.filter(livreur=livreur, statut='terminee'),
        'disponibles': Livraison.objects.filter(livreur__isnull=True, statut='attribuee'),
    }
    
    livraisons = recherches.get(filtre, recherches['toutes'])
    
    return render(request, 'livraisons/livraisons.html', {
        'livreur': livreur,
        'livraisons': livraisons[:20],
        'filtre_actuel': filtre,
        'google_maps_api_key': GOOGLE_MAPS_API_KEY,
    })

# Actions de livraison
@login_required
@require_http_methods(["GET", "POST"])
def detail_livraison_modal(request, livraison_id):
    """Détail d'une livraison pour modal"""
    try:
        livreur = request.user.livreur
        livraison = get_object_or_404(Livraison, id=livraison_id)
        
        # Vérifier les permissions
        if livraison.livreur and livraison.livreur != livreur:
            return JsonResponse({'success': False, 'message': 'Accès non autorisé.'})
        
        if request.method == 'POST':
            return action_livraison(request, livraison_id)
        
        # Préparer les données pour le modal
        donnees_livraison = {
            'id': livraison.id,
            'statut': livraison.statut,
            'statut_display': livraison.get_statut_display(),
            'reference_commande': livraison.commande.reference,
            'client': f"{livraison.commande.client.first_name} {livraison.commande.client.last_name}",
            'adresse_livraison': livraison.commande.adresse_livraison,
            'telephone_client': livraison.commande.client.telephone,
            'instructions': livraison.instructions_speciales,
            'cout_livraison': float(livraison.cout_livraison),
            'distance_estimee': livraison.distance_estimee,
            'duree_estimee': livraison.duree_estimee,
        }
        
        # Coordonnées géographiques
        if livraison.adresse_livraison_point:
            donnees_livraison.update({
                'latitude_livraison': livraison.adresse_livraison_point.y,
                'longitude_livraison': livraison.adresse_livraison_point.x,
            })
        
        if livraison.boutique_point:
            donnees_livraison.update({
                'latitude_boutique': livraison.boutique_point.y,
                'longitude_boutique': livraison.boutique_point.x,
            })
        
        return JsonResponse({'success': True, 'livraison': donnees_livraison})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@require_POST
def action_livraison(request, livraison_id):
    """Gestion centralisée des actions sur les livraisons"""
    try:
        livreur = request.user.livreur
        livraison = get_object_or_404(Livraison, id=livraison_id)
        action = request.POST.get('action')
        
        if action == 'accepter':
            if not livreur.est_disponible:
                return JsonResponse({'success': False, 'message': 'Vous n\'êtes pas disponible pour les livraisons.'})
            
            if not livraison.peut_etre_acceptee_par(livreur):
                return JsonResponse({'success': False, 'message': 'Livraison non disponible ou déjà assignée.'})
            
            # Calculer l'itinéraire et le coût avant acceptation
            if livreur.position_actuelle and livraison.boutique_point:
                origine = (livreur.position_actuelle.y, livreur.position_actuelle.x)
                destination = (livraison.boutique_point.y, livraison.boutique_point.x)
                
                itineraire = google_maps_service.calculer_itineraire(origine, destination)
                if itineraire:
                    leg = itineraire['legs'][0]
                    cout_livraison = livraison.calculer_cout_google_maps({
                        'distance': leg['distance'],
                        'duration': leg['duration']
                    })
                    livraison.cout_livraison = cout_livraison
                    livraison.donnees_google_maps = itineraire
                    livraison.polyline_itineraire = itineraire['overview_polyline']['points']
            
            livraison.assigner_livreur(livreur)
            livraison.accepter_livraison()
            message = 'Livraison acceptée avec succès.'
            
        elif action == 'commencer':
            if not livraison.peut_etre_commencee_par(livreur):
                return JsonResponse({'success': False, 'message': 'Action non autorisée ou livraison non prête.'})
            
            livraison.commencer_livraison()
            
            # Mise à jour position vers la boutique
            if livraison.boutique_point:
                livreur.mettre_a_jour_position(
                    livraison.boutique_point.y,
                    livraison.boutique_point.x
                )
            message = 'Livraison commencée.'
            
        elif action == 'terminer':
            if not livraison.peut_etre_terminee_par(livreur):
                return JsonResponse({'success': False, 'message': 'Action non autorisée ou livraison non prête.'})
            
            # Gérer les preuves
            form = LivraisonForm(request.POST, request.FILES, instance=livraison)
            if form.is_valid():
                form.save()
            
            livraison.terminer_livraison()
            message = 'Livraison terminée avec succès.'
            
        elif action == 'annuler':
            if not livraison.peut_etre_annulee_par(livreur):
                return JsonResponse({'success': False, 'message': 'Action non autorisée.'})
            
            livraison.annuler_livraison()
            message = 'Livraison annulée.'
            
        else:
            return JsonResponse({'success': False, 'message': 'Action non reconnue.'})
        
        # Notification
        NotificationLivreur.objects.create(
            livreur=livreur,
            type_notification=f'livraison_{action}',
            titre=f'Livraison {action}',
            message=f'Livraison #{livraison.id} {action} avec succès',
            donnees_supplementaires={'livraison_id': livraison.id}
        )
        
        return JsonResponse({'success': True, 'message': message})
        
    except Exception as e:
        import traceback
        print(f"Erreur dans action_livraison: {e}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'message': f'Erreur serveur: {str(e)}'})

# API Google Maps
@login_required
def api_google_geocode(request):
    """API pour le géocodage d'adresses avec Google Maps"""
    try:
        adresse = request.GET.get('adresse')
        if not adresse:
            return JsonResponse({'success': False, 'message': 'Adresse requise'})
        
        coordinates = google_maps_service.geocoder_adresse(adresse)
        if coordinates:
            return JsonResponse({
                'success': True,
                'coordinates': {
                    'latitude': coordinates[0],
                    'longitude': coordinates[1]
                }
            })
        else:
            return JsonResponse({'success': False, 'message': 'Géocodage échoué'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def api_google_directions(request):
    """API pour le calcul d'itinéraire avec Google Maps"""
    try:
        origine_lat = request.GET.get('origine_lat')
        origine_lng = request.GET.get('origine_lng')
        destination_lat = request.GET.get('destination_lat')
        destination_lng = request.GET.get('destination_lng')
        mode = request.GET.get('mode', 'driving')
        
        if not all([origine_lat, origine_lng, destination_lat, destination_lng]):
            return JsonResponse({'success': False, 'message': 'Coordonnées manquantes'})
        
        origine = (float(origine_lat), float(origine_lng))
        destination = (float(destination_lat), float(destination_lng))
        
        itineraire = google_maps_service.calculer_itineraire(origine, destination, mode)
        
        if itineraire:
            # Extraire les données importantes
            leg = itineraire['legs'][0]
            donnees_itineraire = {
                'distance': leg['distance'],
                'duration': leg['duration'],
                'polyline': itineraire['overview_polyline']['points'],
                'steps': [
                    {
                        'instruction': step['html_instructions'],
                        'distance': step['distance'],
                        'duration': step['duration'],
                        'polyline': step['polyline']['points']
                    } for step in leg['steps']
                ]
            }
            
            return JsonResponse({'success': True, 'itineraire': donnees_itineraire})
        else:
            return JsonResponse({'success': False, 'message': 'Calcul itinéraire échoué'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def api_google_optimize_route(request):
    """API pour l'optimisation de tournée avec Google Maps"""
    try:
        data = json.loads(request.body) if request.body else {}
        waypoints = data.get('waypoints', [])
        origine_lat = data.get('origine_lat')
        origine_lng = data.get('origine_lng')
        mode = data.get('mode', 'driving')
        
        if not waypoints:
            return JsonResponse({'success': False, 'message': 'Waypoints manquants'})
        
        origine = None
        if origine_lat and origine_lng:
            origine = (float(origine_lat), float(origine_lng))
        
        # Convertir waypoints en format attendu
        waypoints_coords = [(wp['lat'], wp['lng']) for wp in waypoints]
        
        tournee_optimisee = google_maps_service.optimiser_tournee(waypoints_coords, origine, mode)
        
        if tournee_optimisee:
            # Traiter l'ordre optimisé des waypoints
            waypoint_order = tournee_optimisee.get('waypoint_order', [])
            legs = tournee_optimisee['legs']
            
            donnees_optimisation = {
                'waypoint_order': waypoint_order,
                'total_distance': sum(leg['distance']['value'] for leg in legs) / 1000,
                'total_duration': sum(leg['duration']['value'] for leg in legs) / 60,
                'polyline': tournee_optimisee['overview_polyline']['points'],
                'legs': [
                    {
                        'distance': leg['distance'],
                        'duration': leg['duration']
                    } for leg in legs
                ]
            }
            
            return JsonResponse({'success': True, 'optimisation': donnees_optimisation})
        else:
            return JsonResponse({'success': False, 'message': 'Optimisation échouée'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def api_google_distance_matrix(request):
    """API pour la matrice de distances avec Google Maps"""
    try:
        data = json.loads(request.body) if request.body else {}
        origins = data.get('origins', [])
        destinations = data.get('destinations', [])
        mode = data.get('mode', 'driving')
        
        if not origins or not destinations:
            return JsonResponse({'success': False, 'message': 'Origines ou destinations manquantes'})
        
        # Convertir en format coordonnées
        origins_coords = [(origin['lat'], origin['lng']) for origin in origins]
        destinations_coords = [(dest['lat'], dest['lng']) for dest in destinations]
        
        matrix_data = google_maps_service.calculer_distance_matrix(origins_coords, destinations_coords, mode)
        
        if matrix_data:
            return JsonResponse({'success': True, 'matrix': matrix_data})
        else:
            return JsonResponse({'success': False, 'message': 'Calcul matrice échoué'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

# API GeoJSON
@login_required
def api_geojson_livraisons(request):
    """API GeoJSON pour les livraisons"""
    try:
        livreur = request.user.livreur
        type_livraisons = request.GET.get('type', 'mes_livraisons')
        
        if type_livraisons == 'mes_livraisons':
            livraisons = Livraison.objects.filter(livreur=livreur)
        elif type_livraisons == 'disponibles':
            livraisons = Livraison.objects.filter(livreur__isnull=True, statut='attribuee')
        elif type_livraisons == 'en_cours':
            livraisons = Livraison.objects.filter(livreur=livreur, statut__in=['acceptee', 'en_cours'])
        else:
            livraisons = Livraison.objects.filter(livreur=livreur)
        
        features = []
        for livraison in livraisons:
            geojson_data = livraison.to_geojson()
            if geojson_data and 'features' in geojson_data:
                features.extend(geojson_data['features'])
        
        geojson_response = {
            "type": "FeatureCollection",
            "features": features
        }
        
        return JsonResponse(geojson_response)
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def api_geojson_livreurs(request):
    """API GeoJSON pour les livreurs"""
    try:
        # Récupérer tous les livreurs actifs et en ligne
        livreurs = Livreur.objects.filter(est_actif=True, est_en_ligne=True)
        
        features = []
        for livreur in livreurs:
            geojson_data = livreur.to_geojson()
            if geojson_data:
                features.append(geojson_data)
        
        geojson_response = {
            "type": "FeatureCollection",
            "features": features
        }
        
        return JsonResponse(geojson_response)
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def api_geojson_zones(request):
    """API GeoJSON pour les zones de livraison"""
    try:
        zones = ZoneLivraison.objects.filter(est_actif=True)
        
        features = []
        for zone in zones:
            geojson_data = zone.to_geojson()
            if geojson_data:
                features.append(geojson_data)
        
        geojson_response = {
            "type": "FeatureCollection",
            "features": features
        }
        
        return JsonResponse(geojson_response)
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

# API Fonctionnelles
@login_required
@require_http_methods(["GET", "POST"])
def api_position(request):
    """API unifiée pour la gestion de position"""
    try:
        livreur = request.user.livreur
        
        if request.method == 'POST':
            data = json.loads(request.body)
            latitude = float(data.get('latitude'))
            longitude = float(data.get('longitude'))
            
            if livreur.mettre_a_jour_position(latitude, longitude):
                return JsonResponse({'success': True, 'message': 'Position mise à jour.'})
            else:
                return JsonResponse({'success': False, 'message': 'Erreur de position.'})
        
        else:  # GET - historique des positions
            depuis = timezone.now() - timedelta(hours=24)
            positions = PositionLivreur.objects.filter(
                livreur=livreur, timestamp__gte=depuis
            ).order_by('timestamp')
            
            positions_data = [{
                'latitude': p.position.y,
                'longitude': p.position.x,
                'timestamp': p.timestamp.isoformat()
            } for p in positions]
            
            return JsonResponse({'success': True, 'positions': positions_data})
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@require_http_methods(["GET", "POST"])
def api_disponibilite(request):
    """API pour la gestion de disponibilité"""
    try:
        livreur = request.user.livreur
        
        if request.method == 'POST':
            data = json.loads(request.body)
            livreur.est_disponible = data.get('est_disponible', False)
            livreur.est_en_ligne = data.get('est_en_ligne', False)
            livreur.save()
            
            return JsonResponse({'success': True, 'message': 'Disponibilité mise à jour.'})
        
        else:  # GET - statut actuel
            return JsonResponse({
                'success': True,
                'disponibilite': {
                    'est_disponible': livreur.est_disponible,
                    'est_en_ligne': livreur.est_en_ligne
                }
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def api_itineraire(request):
    """API pour le calcul d'itinéraire utilisant Google Maps"""
    try:
        livreur = request.user.livreur
        livraison_id = request.GET.get('livraison_id')
        mode = request.GET.get('mode', 'driving')
        
        if not livraison_id:
            return JsonResponse({'success': False, 'message': 'ID livraison requis.'})
        
        livraison = get_object_or_404(Livraison, id=livraison_id)
        
        # Points de l'itinéraire
        points = []
        
        # Point de départ
        if livreur.position_actuelle:
            points.append({
                'type': 'depart',
                'position': (livreur.position_actuelle.y, livreur.position_actuelle.x),
                'label': 'Votre position'
            })
        elif livraison.boutique_point:
            points.append({
                'type': 'depart', 
                'position': (livraison.boutique_point.y, livraison.boutique_point.x),
                'label': 'Boutique'
            })
        
        # Point d'arrivée
        if livraison.adresse_livraison_point:
            points.append({
                'type': 'arrivee',
                'position': (livraison.adresse_livraison_point.y, livraison.adresse_livraison_point.x),
                'label': 'Livraison'
            })
        
        # Calculer l'itinéraire avec Google Maps
        if len(points) >= 2:
            itineraire = google_maps_service.calculer_itineraire(
                points[0]['position'], 
                points[1]['position'],
                mode
            )
        else:
            itineraire = None
        
        if itineraire:
            leg = itineraire['legs'][0]
            reponse = {
                'points': [{
                    'latitude': p['position'][0],
                    'longitude': p['position'][1],
                    'type': p['type'],
                    'label': p['label']
                } for p in points],
                'itineraire': {
                    'distance_km': round(leg['distance']['value'] / 1000, 2),
                    'duree_minutes': round(leg['duration']['value'] / 60),
                    'polyline': itineraire['overview_polyline']['points']
                },
                'instructions': f"Distance: {leg['distance']['text']} • Durée: {leg['duration']['text']}"
            }
            
            # Calculer et sauvegarder le coût
            cout_livraison = livraison.calculer_cout_google_maps({
                'distance': leg['distance'],
                'duration': leg['duration']
            })
            livraison.cout_livraison = cout_livraison
            livraison.donnees_google_maps = itineraire
            livraison.polyline_itineraire = itineraire['overview_polyline']['points']
            livraison.save()
            
            return JsonResponse({'success': True, 'data': reponse})
        else:
            return JsonResponse({'success': False, 'message': 'Impossible de calculer l\'itinéraire'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def api_optimisation(request):
    """API pour l'optimisation de tournées avec Google Maps"""
    try:
        livreur = request.user.livreur
        
        # Récupérer les livraisons à optimiser
        livraisons = Livraison.objects.filter(
            livreur=livreur,
            statut='acceptee'
        )[:10]  # Limiter pour des raisons de performance
        
        if livraisons.count() < 2:
            return JsonResponse({
                'success': False, 
                'message': 'Au moins 2 livraisons nécessaires pour l\'optimisation'
            })
        
        # Préparer les points pour l'optimisation
        waypoints = []
        for livraison in livraisons:
            if livraison.adresse_livraison_point:
                waypoints.append({
                    'lat': livraison.adresse_livraison_point.y,
                    'lng': livraison.adresse_livraison_point.x,
                    'livraison_id': livraison.id
                })
        
        # Point de départ (position du livreur)
        origine = None
        if livreur.position_actuelle:
            origine = (livreur.position_actuelle.y, livreur.position_actuelle.x)
        
        # Optimiser la tournée avec Google Maps
        profile = request.GET.get('profile', 'driving')
        waypoints_coords = [(wp['lat'], wp['lng']) for wp in waypoints]
        
        tournee_optimisee = google_maps_service.optimiser_tournee(waypoints_coords, origine, profile)
        
        if tournee_optimisee:
            waypoint_order = tournee_optimisee.get('waypoint_order', [])
            legs = tournee_optimisee['legs']
            
            # Reorganiser les livraisons selon l'ordre optimisé
            livraisons_optimisees = []
            for order_index in waypoint_order:
                if order_index < len(waypoints):
                    livraison_id = waypoints[order_index]['livraison_id']
                    livraison = Livraison.objects.get(id=livraison_id)
                    livraisons_optimisees.append(livraison)
            
            # Préparer la réponse
            points_data = []
            
            # Point de départ
            if livreur.position_actuelle:
                points_data.append({
                    'latitude': livreur.position_actuelle.y,
                    'longitude': livreur.position_actuelle.x,
                    'ordre': 0,
                    'type': 'depart',
                    'label': 'Départ'
                })
            
            # Points de livraison optimisés
            for i, livraison in enumerate(livraisons_optimisees, 1):
                if livraison.adresse_livraison_point:
                    points_data.append({
                        'latitude': livraison.adresse_livraison_point.y,
                        'longitude': livraison.adresse_livraison_point.x,
                        'ordre': i,
                        'type': 'livraison',
                        'livraison_id': livraison.id,
                        'client': f"{livraison.commande.client.first_name} {livraison.commande.client.last_name}",
                        'adresse': livraison.commande.adresse_livraison
                    })
            
            return JsonResponse({
                'success': True,
                'optimisation': {
                    'nombre_livraisons': livraisons.count(),
                    'distance_totale': round(sum(leg['distance']['value'] for leg in legs) / 1000, 2),
                    'duree_totale': round(sum(leg['duration']['value'] for leg in legs) / 60),
                    'points_optimises': points_data,
                    'polyline': tournee_optimisee['overview_polyline']['points'],
                    'waypoint_order': waypoint_order
                }
            })
        else:
            return JsonResponse({'success': False, 'message': 'Optimisation échouée'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def api_livraisons(request):
    """API unifiée pour les livraisons avec calculs Google Maps"""
    try:
        livreur = request.user.livreur
        type_livraisons = request.GET.get('type', 'mes_livraisons')
        mode = request.GET.get('mode', 'driving')
        
        if type_livraisons == 'mes_livraisons':
            livraisons = Livraison.objects.filter(livreur=livreur)
        elif type_livraisons == 'disponibles':
            livraisons = Livraison.objects.filter(livreur__isnull=True, statut='attribuee')
        elif type_livraisons == 'proches':
            if not livreur.position_actuelle:
                return JsonResponse({'success': False, 'message': 'Position non disponible.'})
            
            livraisons = Livraison.objects.filter(
                livreur__isnull=True,
                statut='attribuee',
                boutique_point__distance_lte=(
                    livreur.position_actuelle, Distance(km=10)
                )
            )
        else:
            livraisons = Livraison.objects.filter(livreur=livreur)
        
        livraisons_data = []
        for livraison in livraisons[:50]:  # Limiter pour les performances
            livraison_data = {
                'id': livraison.id,
                'statut': livraison.statut,
                'statut_display': livraison.get_statut_display(),
                'reference_commande': livraison.commande.reference,
                'client': f"{livraison.commande.client.first_name} {livraison.commande.client.last_name}",
                'adresse_livraison': livraison.commande.adresse_livraison,
                'telephone_client': getattr(livraison.commande.client, 'telephone', ''),
                'instructions': livraison.instructions_speciales,
                'cout_livraison': float(livraison.cout_livraison),
                'distance_estimee': livraison.distance_estimee,
                'duree_estimee': livraison.duree_estimee,
            }
            
            # Ajouter les coordonnées si disponibles
            if livraison.adresse_livraison_point:
                livraison_data.update({
                    'latitude_livraison': livraison.adresse_livraison_point.y,
                    'longitude_livraison': livraison.adresse_livraison_point.x,
                })
            
            if livraison.boutique_point:
                livraison_data.update({
                    'latitude_boutique': livraison.boutique_point.y,
                    'longitude_boutique': livraison.boutique_point.x,
                })
            
            # Calculer la distance actuelle avec Google Maps
            if livreur.position_actuelle and livraison.boutique_point:
                origine = (livreur.position_actuelle.y, livreur.position_actuelle.x)
                destination = (livraison.boutique_point.y, livraison.boutique_point.x)
                
                itineraire = google_maps_service.calculer_itineraire(origine, destination, mode)
                if itineraire:
                    leg = itineraire['legs'][0]
                    livraison_data['distance_actuelle'] = round(leg['distance']['value'] / 1000, 2)
                    livraison_data['duree_actuelle'] = round(leg['duration']['value'] / 60)
                    livraison_data['polyline_itineraire'] = itineraire['overview_polyline']['points']
            
            livraisons_data.append(livraison_data)
        
        return JsonResponse({'success': True, 'livraisons': livraisons_data})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def api_notifications(request):
    """API pour les notifications"""
    try:
        livreur = request.user.livreur
        
        if request.method == 'POST':
            # Marquer comme lues
            notification_id = request.POST.get('notification_id')
            if notification_id:
                notification = get_object_or_404(NotificationLivreur, id=notification_id, livreur=livreur)
                notification.marquer_comme_lue()
                message = 'Notification marquée comme lue.'
            else:
                # Marquer toutes comme lues
                NotificationLivreur.objects.filter(livreur=livreur, est_lue=False).update(est_lue=True)
                message = 'Toutes les notifications marquées comme lues.'
            
            return JsonResponse({'success': True, 'message': message})
        
        else:  # GET - récupérer les notifications
            notifications = NotificationLivreur.objects.filter(
                livreur=livreur
            ).order_by('-date_creation')[:20]
            
            notifications_data = [{
                'id': n.id,
                'titre': n.titre,
                'message': n.message,
                'est_lue': n.est_lue,
                'date_creation': n.date_creation.isoformat(),
                'type': n.type_notification
            } for n in notifications]
            
            non_lues_count = NotificationLivreur.objects.filter(
                livreur=livreur, est_lue=False
            ).count()
            
            return JsonResponse({
                'success': True,
                'notifications': notifications_data,
                'non_lues_count': non_lues_count
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def api_statistiques(request):
    """API pour les statistiques avancées"""
    try:
        livreur = request.user.livreur
        
        # Période (30 derniers jours)
        depuis = timezone.now() - timedelta(days=30)
        
        # Statistiques générales
        stats = Livraison.objects.filter(
            livreur=livreur,
            date_attribution__gte=depuis
        ).aggregate(
            total=Count('id'),
            terminees=Count('id', filter=Q(statut='terminee')),
            en_cours=Count('id', filter=Q(statut__in=['acceptee', 'en_cours'])),
            revenus=Sum('cout_livraison', filter=Q(statut='terminee'))
        )
        
        # Évolution quotidienne (7 derniers jours)
        evolution = []
        for i in range(7):
            jour = timezone.now() - timedelta(days=6-i)
            count = Livraison.objects.filter(
                livreur=livreur,
                date_attribution__date=jour.date()
            ).count()
            evolution.append({
                'date': jour.strftime('%a'),
                'livraisons': count
            })
        
        # Performances
        note_moyenne = livreur.note_moyenne or 0
        taux_reussite = (stats['terminees'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        # Statistiques de distance
        distance_totale = Livraison.objects.filter(
            livreur=livreur,
            statut='terminee',
            date_attribution__gte=depuis
        ).aggregate(total_distance=Sum('distance_estimee'))['total_distance'] or 0
        
        return JsonResponse({
            'success': True,
            'statistiques': {
                'livraisons_total': stats['total'] or 0,
                'livraisons_terminees': stats['terminees'] or 0,
                'livraisons_en_cours': stats['en_cours'] or 0,
                'revenus_total': float(stats['revenus'] or 0),
                'note_moyenne': float(note_moyenne),
                'taux_reussite': round(taux_reussite, 1),
                'distance_totale': round(distance_totale, 2),
                'evolution': evolution
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

# Vues utilitaires supplémentaires
@login_required
def api_calculer_cout_livraison(request):
    """API pour calculer le coût d'une livraison basé sur Google Maps"""
    try:
        origine_lat = request.GET.get('origine_lat')
        origine_lng = request.GET.get('origine_lng')
        destination_lat = request.GET.get('destination_lat')
        destination_lng = request.GET.get('destination_lng')
        
        if not all([origine_lat, origine_lng, destination_lat, destination_lng]):
            return JsonResponse({'success': False, 'message': 'Coordonnées manquantes'})
        
        origine = (float(origine_lat), float(origine_lng))
        destination = (float(destination_lat), float(destination_lng))
        
        itineraire = google_maps_service.calculer_itineraire(origine, destination)
        
        if itineraire:
            leg = itineraire['legs'][0]
            
            # Créer une instance temporaire de Livraison pour calculer le coût
            livraison_temp = Livraison()
            cout = livraison_temp.calculer_cout_google_maps({
                'distance': leg['distance'],
                'duration': leg['duration']
            })
            
            return JsonResponse({
                'success': True,
                'cout': float(cout),
                'distance': leg['distance'],
                'duration': leg['duration']
            })
        else:
            return JsonResponse({'success': False, 'message': 'Impossible de calculer le coût'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})