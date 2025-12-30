# payout/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta
from .models import PayoutBatch, PayoutConfig
from .managers import PayoutManager
from clients.models import RetraitCommercant

def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_admin)
def dashboard_payout(request):
    """Dashboard de monitoring des payouts"""
    # Statistiques du jour
    aujourdhui = timezone.now().date()
    
    stats = {
        'retraits_24h': RetraitCommercant.objects.filter(
            date_demande__gte=timezone.now() - timedelta(hours=24)
        ).count(),
        
        'retraits_traites_24h': RetraitCommercant.objects.filter(
            statut='traite',
            date_traitement__gte=timezone.now() - timedelta(hours=24)
        ).count(),
        
        'montant_total_24h': RetraitCommercant.objects.filter(
            date_demande__gte=timezone.now() - timedelta(hours=24)
        ).aggregate(total=Sum('montant'))['total'] or 0,
        
        'frais_total_24h': RetraitCommercant.objects.filter(
            date_demande__gte=timezone.now() - timedelta(hours=24)
        ).aggregate(total=Sum('frais_retrait'))['total'] or 0,
        
        'batches_24h': PayoutBatch.objects.filter(
            date_creation__gte=timezone.now() - timedelta(hours=24)
        ).count(),
    }
    
    # Derniers batches
    derniers_batches = PayoutBatch.objects.all().order_by('-date_creation')[:10]
    
    # Retraits en attente
    retraits_attente = RetraitCommercant.objects.filter(
        statut='en_attente'
    ).order_by('-date_demande')[:20]
    
    context = {
        'stats': stats,
        'derniers_batches': derniers_batches,
        'retraits_attente': retraits_attente,
        'config': PayoutConfig.objects.first(),
    }
    
    return render(request, 'payout/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def api_lancer_traitement(request):
    """API pour lancer un traitement manuel"""
    if request.method == 'POST':
        try:
            batch_size = int(request.POST.get('batch_size', 50))
            
            # Lancer la tâche
            from .tasks import traiter_retraits_automatiques
            resultat = traiter_retraits_automatiques.delay(batch_size)
            
            return JsonResponse({
                'success': True,
                'message': 'Traitement lancé avec succès',
                'task_id': resultat.id
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@login_required
@user_passes_test(is_admin)
def api_statistiques(request):
    """API pour les statistiques en temps réel"""
    # Statistiques des 7 derniers jours
    date_debut = timezone.now() - timedelta(days=7)
    
    retraits_par_jour = RetraitCommercant.objects.filter(
        date_demande__gte=date_debut
    ).extra({
        'date': "DATE(date_demande)"
    }).values('date').annotate(
        total=Count('id'),
        montant=Sum('montant'),
        frais=Sum('frais_retrait')
    ).order_by('date')
    
    stats_jour = []
    for item in retraits_par_jour:
        stats_jour.append({
            'date': item['date'].strftime('%Y-%m-%d'),
            'total': item['total'],
            'montant': float(item['montant'] or 0),
            'frais': float(item['frais'] or 0)
        })
    
    return JsonResponse({
        'success': True,
        'stats_jour': stats_jour,
        'total_7j': RetraitCommercant.objects.filter(
            date_demande__gte=date_debut
        ).count(),
        'montant_7j': float(RetraitCommercant.objects.filter(
            date_demande__gte=date_debut
        ).aggregate(total=Sum('montant'))['total'] or 0)
    })