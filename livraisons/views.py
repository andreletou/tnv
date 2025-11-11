from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Avg, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from django.contrib.gis.db.models.functions import Distance as GISDistance
from django.core.paginator import Paginator
from django.urls import reverse
import json
from datetime import datetime, timedelta
from decimal import Decimal

from .forms import (
    LivreurInscriptionForm, ProfilLivreurForm, PositionForm, 
    LivraisonForm, EvaluationLivreurForm, DisponibiliteForm,
    RechercheLivraisonForm
)
from .models import Livreur, Livraison, PositionLivreur, EvaluationLivreur, NotificationLivreur
from clients.models import Commande
from commercants.models import Commercant
from django.contrib.auth import get_user_model

User = get_user_model()


def inscription_livreur(request):
    """Vue pour l'inscription des livreurs"""
    if request.method == 'POST':
        form = LivreurInscriptionForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Bienvenue ! Votre compte livreur a été créé avec succès.')
            return redirect('livraisons:tableau_de_bord')
    else:
        form = LivreurInscriptionForm()
    
    return render(request, 'livraisons/inscription.html', {'form': form})

@login_required
def tableau_de_bord(request):
    """Tableau de bord du livreur"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil livreur.')
        return redirect('livraisons:inscription')
    
    # Statistiques générales
    livraisons_terminees = Livraison.objects.filter(
        livreur=livreur, 
        statut='terminee'
    ).count()
    
    livraisons_en_cours = Livraison.objects.filter(
        livreur=livreur, 
        statut__in=['acceptee', 'en_cours']
    ).count()
    
    # Revenus du mois
    debut_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0)
    revenus_mois = Livraison.objects.filter(
        livreur=livreur,
        statut='terminee',
        date_fin_livraison__gte=debut_mois
    ).aggregate(total=Sum('cout_livraison'))['total'] or Decimal('0.00')
    
    # Livraisons récentes
    livraisons_recentes = Livraison.objects.filter(
        livreur=livreur
    ).order_by('-date_attribution')[:5]
    
    # Notifications non lues
    notifications_non_lues = NotificationLivreur.objects.filter(
        livreur=livreur,
        est_lue=False
    ).count()
    
    context = {
        'livreur': livreur,
        'livraisons_terminees': livraisons_terminees,
        'livraisons_en_cours': livraisons_en_cours,
        'revenus_mois': revenus_mois,
        'livraisons_recentes': livraisons_recentes,
        'notifications_non_lues': notifications_non_lues,
    }
    
    return render(request, 'livraisons/tableau_de_bord.html', context)

@login_required
def profil(request):
    """Profil du livreur"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil livreur.')
        return redirect('livraisons:inscription')
    
    return render(request, 'livraisons/profil.html', {'livreur': livreur})

@login_required
def modifier_profil(request):
    """Modifier le profil du livreur"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil livreur.')
        return redirect('livraisons:inscription')
    
    if request.method == 'POST':
        form = ProfilLivreurForm(request.POST, request.FILES, instance=livreur)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès.')
            return redirect('livraisons:profil')
    else:
        form = ProfilLivreurForm(instance=livreur)
    
    return render(request, 'livraisons/modifier_profil.html', {'form': form})

@login_required
def carte_interactive(request):
    """Carte interactive montrant les boutiques et livraisons disponibles"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil livreur.')
        return redirect('livraisons:inscription')
    
    # Récupérer toutes les boutiques actives
    boutiques = Commercant.objects.filter(est_actif=True)
    
    # Filtrer par recherche
    search = request.GET.get('search', '')
    if search:
        boutiques = boutiques.filter(
            Q(nom_boutique__icontains=search) |
            Q(description__icontains=search) |
            Q(adresse__icontains=search)
        )
    
    context = {
        'livreur': livreur,
        'boutiques': boutiques,
        'search': search,
    }
    
    return render(request, 'livraisons/carte_interactive.html', context)

@login_required
def liste_livraisons(request):
    """Liste des livraisons du livreur"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil livreur.')
        return redirect('livraisons:inscription')
    
    livraisons = Livraison.objects.filter(livreur=livreur)
    
    # Filtrage par statut
    statut = request.GET.get('statut', '')
    if statut:
        livraisons = livraisons.filter(statut=statut)
    
    # Pagination
    paginator = Paginator(livraisons, 10)
    page = request.GET.get('page')
    livraisons_page = paginator.get_page(page)
    
    context = {
        'livraisons': livraisons_page,
        'statut': statut,
    }
    
    return render(request, 'livraisons/liste_livraisons.html', context)

@login_required
def livraisons_disponibles(request):
    """Livraisons disponibles à accepter"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil livreur.')
        return redirect('livraisons:inscription')
    
    # Livraisons sans livreur assigné
    livraisons = Livraison.objects.filter(
        livreur__isnull=True,
        statut='attribuee'
    ).select_related('commande', 'commande__client')
    
    # Filtrer par proximité si le livreur a une position
    if livreur.position_actuelle:
        livraisons_proches = []
        for livraison in livraisons:
            if livraison.boutique_point:
                distance = livreur.calculer_distance(livraison.boutique_point)
                if distance and distance <= 10000:  # 10km max
                    livraison.distance_km = distance / 1000
                    livraisons_proches.append(livraison)
        
        livraisons_proches.sort(key=lambda x: x.distance_km)
        livraisons = livraisons_proches
    
    context = {
        'livraisons': livraisons,
    }
    
    return render(request, 'livraisons/livraisons_disponibles.html', context)

@login_required
def detail_livraison(request, livraison_id):
    """Détails d'une livraison"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil livreur.')
        return redirect('livraisons:inscription')
    
    livraison = get_object_or_404(Livraison, id=livraison_id, livreur=livreur)
    
    # Calculer l'itinéraire si nécessaire
    if livreur.position_actuelle and livraison.adresse_livraison_point:
        distance = livreur.calculer_distance(livraison.adresse_livraison_point)
        livraison.distance_actuelle = distance / 1000 if distance else None
    
    context = {
        'livraison': livraison,
    }
    
    return render(request, 'livraisons/detail_livraison.html', context)

@login_required
@require_POST
def accepter_livraison(request, livraison_id):
    """Accepter une livraison"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil livreur non trouvé.'})
    
    livraison = get_object_or_404(Livraison, id=livraison_id, livreur__isnull=True)
    
    try:
        livraison.assigner_livreur(livreur)
        livraison.accepter_livraison()
        
        # Créer une notification
        NotificationLivreur.objects.create(
            livreur=livreur,
            type_notification='livraison_acceptee',
            titre='Livraison acceptée',
            message=f'Vous avez accepté la livraison {livraison.id}',
            donnees_supplementaires={'livraison_id': livraison.id}
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Livraison acceptée avec succès.',
            'redirect_url': reverse('livraisons:detail_livraison', args=[livraison_id])
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@require_POST
def commencer_livraison(request, livraison_id):
    """Commencer une livraison"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil livreur non trouvé.'})
    
    livraison = get_object_or_404(Livraison, id=livraison_id, livreur=livreur)
    
    try:
        livraison.commencer_livraison()
        
        # Mettre à jour la position du livreur à la boutique (méthode sécurisée)
        if livraison.boutique_point:
            try:
                # Vérifier si la méthode existe
                if hasattr(livreur, 'mettre_a_jour_position'):
                    livreur.mettre_a_jour_position(
                        livraison.boutique_point.y,  # latitude
                        livraison.boutique_point.x   # longitude
                    )
                else:
                    # Méthode de secours
                    livreur.position_actuelle = livraison.boutique_point
                    livreur.derniere_position_mise_a_jour = timezone.now()
                    livreur.save()
                    
                    # Enregistrer dans l'historique
                    PositionLivreur.objects.create(
                        livreur=livreur,
                        position=livraison.boutique_point
                    )
            except Exception as e:
                print(f"Erreur mise à jour position: {e}")
                # Continuer même si la mise à jour de position échoue
        
        return JsonResponse({
            'success': True,
            'message': 'Livraison commencée.',
            'redirect_url': reverse('livraisons:itineraire_livraison', args=[livraison_id])
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@require_POST
def terminer_livraison(request, livraison_id):
    """Terminer une livraison"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil livreur non trouvé.'})
    
    livraison = get_object_or_404(Livraison, id=livraison_id, livreur=livreur)
    
    try:
        # Gérer les fichiers de preuve
        form = LivraisonForm(request.POST, request.FILES, instance=livraison)
        if form.is_valid():
            form.save()
        
        livraison.terminer_livraison()
        
        # Créer une notification
        NotificationLivreur.objects.create(
            livreur=livreur,
            type_notification='livraison_terminee',
            titre='Livraison terminée',
            message=f'La livraison {livraison.id} a été terminée avec succès.',
            donnees_supplementaires={'livraison_id': livraison.id}
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Livraison terminée avec succès.',
            'redirect_url': reverse('livraisons:detail_livraison', args=[livraison_id])
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def itineraire_livraison(request, livraison_id):
    """Vue pour suivre l'itinéraire de livraison en temps réel"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil livreur.')
        return redirect('livraisons:inscription')
    
    livraison = get_object_or_404(Livraison, id=livraison_id, livreur=livreur)
    
    if livraison.statut not in ['acceptee', 'en_cours']:
        messages.error(request, 'Cette livraison n\'est pas en cours.')
        return redirect('livraisons:detail_livraison', livraison_id=livraison_id)
    
    context = {
        'livraison': livraison,
        'livreur': livreur,
    }
    
    return render(request, 'livraisons/itineraire.html', context)

@login_required
def historique_livraisons(request):
    """Historique des livraisons du livreur"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil livreur.')
        return redirect('livraisons:inscription')
    
    livraisons = Livraison.objects.filter(livreur=livreur).order_by('-date_attribution')
    
    # Filtrage par période
    periode = request.GET.get('periode', '')
    if periode == 'semaine':
        debut = timezone.now() - timedelta(days=7)
        livraisons = livraisons.filter(date_attribution__gte=debut)
    elif periode == 'mois':
        debut = timezone.now() - timedelta(days=30)
        livraisons = livraisons.filter(date_attribution__gte=debut)
    
    # Pagination
    paginator = Paginator(livraisons, 20)
    page = request.GET.get('page')
    livraisons_page = paginator.get_page(page)
    
    context = {
        'livraisons': livraisons_page,
        'periode': periode,
    }
    
    return render(request, 'livraisons/historique.html', context)

@login_required
def statistiques(request):
    """Statistiques du livreur"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil livreur.')
        return redirect('livraisons:inscription')
    
    # Statistiques générales
    total_livraisons = Livraison.objects.filter(livreur=livreur).count()
    livraisons_terminees = Livraison.objects.filter(livreur=livreur, statut='terminee').count()
    
    # Revenus
    revenus_total = Livraison.objects.filter(
        livreur=livreur,
        statut='terminee'
    ).aggregate(total=Sum('cout_livraison'))['total'] or Decimal('0.00')
    
    # Évaluations
    evaluations = EvaluationLivreur.objects.filter(livraison__livreur=livreur)
    note_moyenne = evaluations.aggregate(avg=Avg('note'))['avg'] or 0
    
    context = {
        'total_livraisons': total_livraisons,
        'livraisons_terminees': livraisons_terminees,
        'revenus_total': revenus_total,
        'note_moyenne': round(note_moyenne, 1),
        'nombre_evaluations': evaluations.count(),
    }
    
    return render(request, 'livraisons/statistiques.html', context)

@login_required
def evaluations(request):
    """Évaluations reçues par le livreur"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil livreur.')
        return redirect('livraisons:inscription')
    
    evaluations = EvaluationLivreur.objects.filter(
        livraison__livreur=livreur
    ).order_by('-date_evaluation')
    
    # Pagination
    paginator = Paginator(evaluations, 10)
    page = request.GET.get('page')
    evaluations_page = paginator.get_page(page)
    
    context = {
        'evaluations': evaluations_page,
    }
    
    return render(request, 'livraisons/evaluations.html', context)

@login_required
def notifications(request):
    """Notifications du livreur"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil livreur.')
        return redirect('livraisons:inscription')
    
    notifications = NotificationLivreur.objects.filter(
        livreur=livreur
    ).order_by('-date_creation')
    
    context = {
        'notifications': notifications,
    }
    
    return render(request, 'livraisons/notifications.html', context)

@login_required
@require_POST
def marquer_notification_lue(request, notification_id):
    """Marquer une notification comme lue"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil livreur non trouvé.'})
    
    notification = get_object_or_404(NotificationLivreur, id=notification_id, livreur=livreur)
    notification.marquer_comme_lue()
    
    return JsonResponse({'success': True})

# API Endpoints

@login_required
@require_http_methods(["POST"])
def api_mettre_a_jour_position(request):
    """API pour mettre à jour la position du livreur"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil livreur non trouvé.'})
    
    try:
        data = json.loads(request.body)
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
        
        # Mettre à jour la position du livreur
        livreur.mettre_a_jour_position(latitude, longitude)
        
        # Enregistrer dans l'historique des positions
        PositionLivreur.objects.create(
            livreur=livreur,
            position=Point(longitude, latitude)
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Position mise à jour.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@require_http_methods(["POST"])
def api_gerer_disponibilite(request):
    """API pour gérer la disponibilité du livreur"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil livreur non trouvé.'})
    
    try:
        data = json.loads(request.body)
        livreur.est_disponible = data.get('est_disponible', False)
        livreur.est_en_ligne = data.get('est_en_ligne', False)
        livreur.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Disponibilité mise à jour.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def api_livraisons_disponibles(request):
    """API pour obtenir les livraisons disponibles"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil livreur non trouvé.'})
    
    livraisons = Livraison.objects.filter(
        livreur__isnull=True,
        statut='attribuee'
    ).select_related('commande', 'commande__client')
    
    livraisons_data = []
    for livraison in livraisons:
        distance = None
        if livreur.position_actuelle and livraison.boutique_point:
            distance = livreur.calculer_distance(livraison.boutique_point)
        
        livraisons_data.append({
            'id': livraison.id,
            'reference_commande': livraison.commande.reference,
            'client_nom': f"{livraison.commande.client.first_name} {livraison.commande.client.last_name}",
            'adresse_livraison': livraison.commande.adresse_livraison,
            'cout_livraison': float(livraison.cout_livraison),
            'distance_metres': distance,
            'boutique_nom': livraison.commande.commercant.nom_boutique if livraison.commande.commercant else 'Non spécifié',
        })
    
    # Trier par distance
    livraisons_data.sort(key=lambda x: x['distance_metres'] if x['distance_metres'] else float('inf'))
    
    return JsonResponse({
        'success': True,
        'livraisons': livraisons_data
    })

@login_required
def api_boutiques_carte(request):
    """API pour obtenir les boutiques pour la carte"""
    boutiques = Commercant.objects.filter(est_actif=True)
    
    boutiques_data = []
    for boutique in boutiques:
        boutiques_data.append({
            'id': boutique.id,
            'nom': boutique.nom_boutique,
            'categorie': boutique.get_categorie_display(),
            'adresse': boutique.adresse,
            'latitude': float(boutique.latitude) if boutique.latitude else None,
            'longitude': float(boutique.longitude) if boutique.longitude else None,
            'telephone': boutique.telephone,
            'horaires': f"{boutique.horaire_ouverture} - {boutique.horaire_fermeture}",
        })
    
    return JsonResponse({
        'success': True,
        'boutiques': boutiques_data
    })

@login_required
def api_livraisons_carte(request):
    """API pour obtenir les livraisons pour la carte"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil livreur non trouvé.'})
    
    # Livraisons disponibles et livraisons du livreur
    livraisons = Livraison.objects.filter(
        Q(livreur__isnull=True, statut='attribuee') | 
        Q(livreur=livreur)
    ).select_related('commande', 'commande__client', 'commande__commercant')
    
    livraisons_data = []
    for livraison in livraisons:
        # Calculer les coordonnées si elles n'existent pas - CORRIGÉ
        if not livraison.adresse_livraison_point:
            try:
                if (livraison.commande.latitude_livraison and 
                    livraison.commande.longitude_livraison and
                    float(livraison.commande.latitude_livraison) != 0 and 
                    float(livraison.commande.longitude_livraison) != 0):
                    
                    livraison.adresse_livraison_point = Point(
                        float(livraison.commande.longitude_livraison),
                        float(livraison.commande.latitude_livraison)
                    )
                    livraison.save()
            except (ValueError, TypeError, AttributeError) as e:
                print(f"Erreur création point livraison: {e}")
        
        if not livraison.boutique_point and livraison.commande.commercant:
            try:
                if (livraison.commande.commercant.latitude and 
                    livraison.commande.commercant.longitude and
                    float(livraison.commande.commercant.latitude) != 0 and 
                    float(livraison.commande.commercant.longitude) != 0):
                    
                    livraison.boutique_point = Point(
                        float(livraison.commande.commercant.longitude),
                        float(livraison.commande.commercant.latitude)
                    )
                    livraison.save()
            except (ValueError, TypeError, AttributeError) as e:
                print(f"Erreur création point boutique: {e}")
        
        # Préparer les données pour la réponse
        livraison_dict = {
            'id': livraison.id,
            'reference_commande': livraison.commande.reference,
            'statut': livraison.statut,
            'statut_display': livraison.get_statut_display(),
            'client_nom': f"{livraison.commande.client.first_name} {livraison.commande.client.last_name}",
            'adresse_livraison': livraison.commande.adresse_livraison,
            'cout_livraison': float(livraison.cout_livraison),
            'est_assignee_a_livreur': livraison.livreur == livreur,
        }
        
        # Ajouter les coordonnées seulement si elles existent
        if livraison.adresse_livraison_point:
            livraison_dict.update({
                'latitude_livraison': float(livraison.adresse_livraison_point.y),
                'longitude_livraison': float(livraison.adresse_livraison_point.x),
            })
        else:
            livraison_dict.update({
                'latitude_livraison': None,
                'longitude_livraison': None,
            })
            
        if livraison.boutique_point:
            livraison_dict.update({
                'boutique_nom': livraison.commande.commercant.nom_boutique if livraison.commande.commercant else None,
                'latitude_boutique': float(livraison.boutique_point.y),
                'longitude_boutique': float(livraison.boutique_point.x),
            })
        else:
            livraison_dict.update({
                'boutique_nom': None,
                'latitude_boutique': None,
                'longitude_boutique': None,
            })
        
        livraisons_data.append(livraison_dict)
    
    return JsonResponse({
        'success': True,
        'livraisons': livraisons_data
    })


@login_required
def api_itineraire(request, livraison_id):
    """API pour obtenir l'itinéraire d'une livraison"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil livreur non trouvé.'})
    
    livraison = get_object_or_404(Livraison, id=livraison_id, livreur=livreur)
    
    itineraire_data = {
        'id': livraison.id,
        'reference_commande': livraison.commande.reference,
        'statut': livraison.statut,
        'client_nom': f"{livraison.commande.client.first_name} {livraison.commande.client.last_name}",
        'adresse_livraison': livraison.commande.adresse_livraison,
        'instructions_livraison': livraison.commande.instructions_livraison,
        'cout_livraison': float(livraison.cout_livraison),
        'distance_estimee': livraison.distance_estimee,
        'duree_estimee': livraison.duree_estimee,
    }
    
    # Points de l'itinéraire
    if livreur.position_actuelle:
        itineraire_data['position_livreur'] = {
            'latitude': livreur.position_actuelle.y,
            'longitude': livreur.position_actuelle.x,
        }
    
    if livraison.boutique_point:
        itineraire_data['point_boutique'] = {
            'latitude': livraison.boutique_point.y,
            'longitude': livraison.boutique_point.x,
            'nom': livraison.commande.commercant.nom_boutique if livraison.commande.commercant else 'Boutique',
            'adresse': livraison.commande.commercant.adresse if livraison.commande.commercant else 'Adresse boutique',
        }
    
    if livraison.adresse_livraison_point:
        itineraire_data['point_livraison'] = {
            'latitude': livraison.adresse_livraison_point.y,
            'longitude': livraison.adresse_livraison_point.x,
            'adresse': livraison.commande.adresse_livraison,
        }
    
    return JsonResponse({
        'success': True,
        'itineraire': itineraire_data
    })

@login_required
def api_historique_positions(request):
    """API pour obtenir l'historique des positions du livreur"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil livreur non trouvé.'})
    
    # Positions des dernières 24 heures
    depuis = timezone.now() - timedelta(hours=24)
    positions = PositionLivreur.objects.filter(
        livreur=livreur,
        timestamp__gte=depuis
    ).order_by('timestamp')
    
    positions_data = []
    for position in positions:
        positions_data.append({
            'latitude': position.position.y,
            'longitude': position.position.x,
            'timestamp': position.timestamp.isoformat(),
            'vitesse': position.vitesse,
        })
    
    return JsonResponse({
        'success': True,
        'positions': positions_data
    })

@login_required
def api_statistiques(request):
    """API pour obtenir les statistiques du livreur"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil livreur non trouvé.'})
    
    # Statistiques des 30 derniers jours
    depuis = timezone.now() - timedelta(days=30)
    
    livraisons_periode = Livraison.objects.filter(
        livreur=livreur,
        date_attribution__gte=depuis
    )
    
    livraisons_terminees_periode = livraisons_periode.filter(statut='terminee')
    
    # Revenus
    revenus_periode = livraisons_terminees_periode.aggregate(
        total=Sum('cout_livraison')
    )['total'] or Decimal('0.00')
    
    # Évolution des livraisons par jour
    evolution = []
    for i in range(30):
        jour = timezone.now() - timedelta(days=29-i)
        count = livraisons_periode.filter(
            date_attribution__date=jour.date()
        ).count()
        evolution.append({
            'date': jour.strftime('%d/%m'),
            'nombre': count
        })
    
    return JsonResponse({
        'success': True,
        'statistiques': {
            'total_livraisons': livraisons_periode.count(),
            'livraisons_terminees': livraisons_terminees_periode.count(),
            'revenus': float(revenus_periode),
            'note_moyenne': float(livreur.note_moyenne),
            'evolution': evolution
        }
    })

@login_required
def api_notifications(request):
    """API pour obtenir les notifications du livreur"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil livreur non trouvé.'})
    
    notifications = NotificationLivreur.objects.filter(
        livreur=livreur
    ).order_by('-date_creation')[:20]
    
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': notification.id,
            'type': notification.type_notification,
            'titre': notification.titre,
            'message': notification.message,
            'est_lue': notification.est_lue,
            'date_creation': notification.date_creation.isoformat(),
            'donnees_supplementaires': notification.donnees_supplementaires,
        })
    
    non_lues_count = NotificationLivreur.objects.filter(
        livreur=livreur,
        est_lue=False
    ).count()
    
    return JsonResponse({
        'success': True,
        'notifications': notifications_data,
        'non_lues_count': non_lues_count
    })

@login_required
@require_http_methods(["POST"])
def api_ajouter_evaluation(request):
    """API pour ajouter une évaluation"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil livreur non trouvé.'})
    
    # Cette API sera utilisée par les clients, pas par les livreurs
    # mais elle est placée ici pour l'organisation du code
    return JsonResponse({
        'success': False,
        'message': 'Cette API doit être appelée par un client.'
    })

@login_required
@require_http_methods(["POST"])
def annuler_livraison(request, livraison_id):
    """Annuler une livraison"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil livreur non trouvé.'})
    
    livraison = get_object_or_404(Livraison, id=livraison_id, livreur=livreur)
    
    try:
        livraison.annuler_livraison()
        
        # Créer une notification
        NotificationLivreur.objects.create(
            livreur=livreur,
            type_notification='livraison_annulee',
            titre='Livraison annulée',
            message=f'Vous avez annulé la livraison {livraison.id}',
            donnees_supplementaires={'livraison_id': livraison.id}
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Livraison annulée avec succès.',
            'redirect_url': reverse('livraisons:liste_livraisons')
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
@login_required
def api_livraisons_proches(request):
    """API pour obtenir les livraisons proches du livreur"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil livreur non trouvé.'})
    
    if not livreur.position_actuelle:
        return JsonResponse({'success': False, 'message': 'Position actuelle du livreur non définie.'})
    
    # Rechercher les livraisons dans un rayon de 10 km
    rayon_km = 10
    livraisons = Livraison.objects.filter(
        livreur__isnull=True,
        statut='attribuee',
        boutique_point__distance_lte=(
            livreur.position_actuelle,
            Distance(km=rayon_km)
        )
    ).annotate(
        distance=GISDistance('boutique_point', livreur.position_actuelle)
    ).order_by('distance')
    
    livraisons_data = []
    for livraison in livraisons:
        livraisons_data.append({
            'id': livraison.id,
            'reference_commande': livraison.commande.reference,
            'client_nom': f"{livraison.commande.client.first_name} {livraison.commande.client.last_name}",
            'adresse_livraison': livraison.commande.adresse_livraison,
            'cout_livraison': float(livraison.cout_livraison),
            'distance_metres': livraison.distance.m,
            'boutique_nom': livraison.commande.commercant.nom_boutique if livraison.commande.commercant else 'Non spécifié',
        })
    
    return JsonResponse({
        'success': True,
        'livraisons': livraisons_data
    })

# suivi livraison en temps réel via websocket
from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio
import json

@login_required
def suivi_livraison(request, livraison_id):
    """Vue pour le suivi en temps réel via WebSocket"""
    try:
        livreur = request.user.livreur
    except Livreur.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil livreur.')
        return redirect('livraisons:inscription')
    
    livraison = get_object_or_404(Livraison, id=livraison_id, livreur=livreur)
    
    context = {
        'livraison': livraison,
        'livreur': livreur,
    }
    
    return render(request, 'livraisons/suivi_livraison.html', context)