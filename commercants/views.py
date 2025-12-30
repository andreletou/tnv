from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from .forms import CommercantInscriptionForm, ProduitForm, PromotionForm, ProfilForm
from .models import Commercant, Produit, Promotion
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, F, Avg
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime, timedelta
from clients.models import Commande, ArticleCommande, Avis,Commission,Portefeuille,RetraitCommercant
from clients.paygate import PayGateGlobal
from .forms import CommercantInscriptionForm, ProduitForm, PromotionForm, ProfilForm,DemandeRetraitForm
from django.core.paginator import Paginator

from django.contrib.gis.geos import Point
from decimal import Decimal
from livraisons.models import Livraison



def inscription_commercant(request):
    if request.method == 'POST':
        form = CommercantInscriptionForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                messages.success(request, 'Bienvenue ! Votre boutique a été créée avec succès et vos produits ont été générés automatiquement.')
                return redirect('commercants:tableau_de_bord')
            except Exception as e:
                messages.error(request, f'Erreur lors de la création de la boutique: {str(e)}')
                return render(request, 'commercants/inscription.html', {'form': form})
    else:
        form = CommercantInscriptionForm()
    
    return render(request, 'commercants/inscription.html', {'form': form})
@login_required
def tableau_de_bord(request):
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil commerçant.')
        return redirect('clients:accueil')
    
    produits = Produit.objects.filter(commercant=commercant)
    
    # Statistiques sur les produits
    total_produits = produits.count()
    produits_actifs = produits.filter(est_actif=True).count()
    stock_total = produits.aggregate(total=Sum('stock'))['total'] or 0
    stock_faible = produits.filter(stock__lte=F('stock_min')).count()
    
    # Produits récents
    produits_recents = produits.order_by('-date_ajout')[:5]
    
    # Promotions actives
    promotions_actives = Promotion.objects.filter(
        produit__commercant=commercant,
        est_active=True,
        date_debut__lte=timezone.now(),
        date_fin__gte=timezone.now()
    )
    
    # Statistiques sur les commandes
    commandes = Commande.objects.filter(commercant=commercant)
    commandes_en_attente = commandes.filter(statut='en_attente').count()
    commandes_validees = commandes.filter(statut='validee').count()
    commandes_en_preparation = commandes.filter(statut='en_preparation').count()
    commandes_pretes = commandes.filter(statut='prete').count()
    commandes_en_livraison = commandes.filter(statut='en_livraison').count()
    commandes_livrees = commandes.filter(statut='livree').count()
    
    # Commandes récentes
    commandes_recentes = commandes.order_by('-date_commande')[:5]
    
    context = {
        'total_produits': total_produits,
        'produits_actifs': produits_actifs,
        'stock_total': stock_total,
        'stock_faible': stock_faible,
        'produits_recents': produits_recents,
        'promotions_actives': promotions_actives,
        'commandes_en_attente': commandes_en_attente,
        'commandes_validees': commandes_validees,
        'commandes_en_preparation': commandes_en_preparation,
        'commandes_pretes': commandes_pretes,
        'commandes_en_livraison': commandes_en_livraison,
        'commandes_livrees': commandes_livrees,
        'commandes_recentes': commandes_recentes,
    }
    
    return render(request, 'commercants/tableau_de_bord.html', context)

@login_required
def liste_produits(request):
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil commerçant.')
        return redirect('clients:accueil')
    
    produits = Produit.objects.filter(commercant=commercant)
    
    # Filtrage
    search = request.GET.get('search', '')
    categorie = request.GET.get('categorie', '')
    statut = request.GET.get('statut', '')
    
    if search:
        produits = produits.filter(
            Q(nom__icontains=search) | 
            Q(description__icontains=search)
        )
    
    if categorie:
        produits = produits.filter(categorie=categorie)
    
    if statut == 'actif':
        produits = produits.filter(est_actif=True)
    elif statut == 'inactif':
        produits = produits.filter(est_actif=False)
    elif statut == 'stock_faible':
        produits = produits.filter(stock__lte=F('stock_min'))
    
    # Calculer les statistiques pour éviter les problèmes dans le template
    total_produits = produits.count()
    produits_actifs = produits.filter(est_actif=True).count()
    produits_en_promo = produits.filter(est_en_promotion=True).count()
    produits_stock_faible = produits.filter(stock__lte=F('stock_min')).count()
    
    context = {
        'produits': produits,
        'search': search,
        'categorie': categorie,
        'statut': statut,
        'total_produits': total_produits,
        'produits_actifs': produits_actifs,
        'produits_en_promo': produits_en_promo,
        'produits_stock_faible': produits_stock_faible,
    }
    
    return render(request, 'commercants/liste_produits.html', context)
@login_required
def ajouter_produit(request):
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil commerçant.')
        return redirect('clients:accueil')
    
    if request.method == 'POST':
        form = ProduitForm(request.POST, request.FILES)
        if form.is_valid():
            produit = form.save(commit=False)
            produit.commercant = commercant
            produit.save()
            messages.success(request, 'Produit ajouté avec succès.')
            return redirect('commercants:liste_produits')
    else:
        form = ProduitForm()
    
    return render(request, 'commercants/formulaire_produit.html', {'form': form, 'titre': 'Ajouter un produit'})

@login_required
def modifier_produit(request, pk):
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil commerçant.')
        return redirect('clients:accueil')
    
    produit = get_object_or_404(Produit, pk=pk, commercant=commercant)
    
    if request.method == 'POST':
        form = ProduitForm(request.POST, request.FILES, instance=produit)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produit modifié avec succès.')
            return redirect('commercants:liste_produits')
    else:
        form = ProduitForm(instance=produit)
    
    return render(request, 'commercants/formulaire_produit.html', {'form': form, 'titre': 'Modifier un produit'})

@login_required
def supprimer_produit(request, pk):
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil commerçant.')
        return redirect('clients:accueil')
    
    produit = get_object_or_404(Produit, pk=pk, commercant=commercant)
    
    if request.method == 'POST':
        produit.delete()
        messages.success(request, 'Produit supprimé avec succès.')
        return redirect('commercants:liste_produits')
    
    return render(request, 'commercants/confirmer_suppression.html', {'objet': produit, 'type': 'produit'})

@login_required
def liste_promotions(request):
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil commerçant.')
        return redirect('clients:accueil')
    
    promotions = Promotion.objects.filter(produit__commercant=commercant).order_by('-date_creation')
    
    context = {
        'promotions': promotions,
    }
    
    return render(request, 'commercants/liste_promotions.html', context)

@login_required
def ajouter_promotion(request):
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil commerçant.')
        return redirect('clients:accueil')
    
    if request.method == 'POST':
        form = PromotionForm(request.POST, commercant=commercant)
        if form.is_valid():
            promotion = form.save()
            # Mettre à jour le prix promotionnel du produit
            produit = promotion.produit
            produit.est_en_promotion = True
            
            # Conversion en Decimal pour éviter l'erreur de type
            prix_original = Decimal(str(produit.prix))
            pourcentage_reduction = Decimal(str(promotion.pourcentage_reduction))
            
            reduction = (pourcentage_reduction / Decimal('100')) * prix_original
            produit.prix_promotionnel = prix_original - reduction
            
            # Arrondir à 2 décimales
            produit.prix_promotionnel = produit.prix_promotionnel.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            produit.save()
            
            messages.success(request, 'Promotion créée avec succès.')
            return redirect('commercants:liste_promotions')
    else:
        form = PromotionForm(commercant=commercant)
    
    return render(request, 'commercants/formulaire_promotion.html', {'form': form, 'titre': 'Ajouter une promotion'})

@login_required
def modifier_promotion(request, pk):
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil commerçant.')
        return redirect('clients:accueil')
    
    promotion = get_object_or_404(Promotion, pk=pk, produit__commercant=commercant)
    
    if request.method == 'POST':
        form = PromotionForm(request.POST, instance=promotion, commercant=commercant)
        if form.is_valid():
            form.save()
            # Mettre à jour le prix promotionnel du produit
            produit = promotion.produit
            if promotion.est_active and promotion.est_en_cours:
                produit.est_en_promotion = True
                
                # Conversion en Decimal pour éviter l'erreur de type
                prix_original = Decimal(str(produit.prix))
                pourcentage_reduction = Decimal(str(promotion.pourcentage_reduction))
                
                reduction = (pourcentage_reduction / Decimal('100')) * prix_original
                produit.prix_promotionnel = prix_original - reduction
                
                # Arrondir à 2 décimales
                produit.prix_promotionnel = produit.prix_promotionnel.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            else:
                produit.est_en_promotion = False
                produit.prix_promotionnel = None
            produit.save()
            
            messages.success(request, 'Promotion modifiée avec succès.')
            return redirect('commercants:liste_promotions')
    else:
        form = PromotionForm(instance=promotion, commercant=commercant)
    
    return render(request, 'commercants/formulaire_promotion.html', {'form': form, 'titre': 'Modifier une promotion'})
    
@login_required
def supprimer_promotion(request, pk):
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil commerçant.')
        return redirect('clients:accueil')
    
    promotion = get_object_or_404(Promotion, pk=pk, produit__commercant=commercant)
    
    if request.method == 'POST':
        # Désactiver la promotion sur le produit
        produit = promotion.produit
        produit.est_en_promotion = False
        produit.prix_promotionnel = None
        produit.save()
        
        promotion.delete()
        messages.success(request, 'Promotion supprimée avec succès.')
        return redirect('commercants:liste_promotions')
    
    return render(request, 'commercants/confirmer_suppression.html', {'objet': promotion, 'type': 'promotion'})

@login_required
def profil(request):
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil commerçant.')
        return redirect('clients:accueil')
    
    return render(request, 'commercants/profil.html', {'commercant': commercant})

@login_required
def modifier_profil(request):
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil commerçant.')
        return redirect('clients:accueil')
    
    if request.method == 'POST':
        form = ProfilForm(request.POST, request.FILES, instance=commercant)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès.')
            return redirect('commercants:profil')
    else:
        form = ProfilForm(instance=commercant)
    
    return render(request, 'commercants/modifier_profil.html', {'form': form})

@login_required
def api_statistiques(request):
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil commerçant non trouvé.'}, status=400)
    
    # Période pour les statistiques (30 derniers jours)
    date_debut = timezone.now() - timedelta(days=30)
    
    # Chiffre d'affaires
    ca_total = Commande.objects.filter(
        commercant=commercant,
        date_commande__gte=date_debut,
        statut='livree'
    ).aggregate(total=Sum('total'))['total'] or 0
    
    # Commandes
    commandes_total = Commande.objects.filter(
        commercant=commercant,
        date_commande__gte=date_debut
    ).count()
    
    commandes_livrees = Commande.objects.filter(
        commercant=commercant,
        date_commande__gte=date_debut,
        statut='livree'
    ).count()
    
    # Produits les plus vendus
    produits_vendus = ArticleCommande.objects.filter(
        commande__commercant=commercant,
        commande__date_commande__gte=date_debut
    ).values('produit__nom').annotate(
        total_vendu=Sum('quantite'),
        ca_produit=Sum(F('quantite') * F('prix_unitaire'))
    ).order_by('-total_vendu')[:5]
    
    # Évolution du CA sur 30 jours
    evolution_ca = []
    for i in range(30):
        date_jour = timezone.now() - timedelta(days=29-i)
        ca_jour = Commande.objects.filter(
            commercant=commercant,
            date_commande__date=date_jour.date(),
            statut='livree'
        ).aggregate(total=Sum('total'))['total'] or 0
        evolution_ca.append({
            'date': date_jour.strftime('%d/%m'),
            'ca': float(ca_jour)
        })
    
    return JsonResponse({
        'success': True,
        'statistiques': {
            'chiffre_affaires': float(ca_total),
            'commandes_total': commandes_total,
            'commandes_livrees': commandes_livrees,
            'taux_livraison': round((commandes_livrees / commandes_total * 100) if commandes_total > 0 else 0, 1),
            'produits_vendus': list(produits_vendus),
            'evolution_ca': evolution_ca
        }
    })

@login_required
def api_promotions(request):
    promotions = Produit.objects.filter(commercant=request.user.commercant_profile, est_en_promotion=True)
    data = [
        {
            'id': p.id,
            'nom': p.nom,
            'prix': float(p.prix_promotionnel or p.prix),
            'date_debut': p.date_debut_promo.strftime('%Y-%m-%d') if p.date_debut_promo else None,
            'date_fin': p.date_fin_promo.strftime('%Y-%m-%d') if p.date_fin_promo else None,
        }
        for p in promotions
    ]
    return JsonResponse({'success': True, 'promotions': data})


@login_required
def api_produits(request):
    produits = Produit.objects.filter(commercant=request.user.commercant_profile)
    data = [
        {
            'id': p.id,
            'nom': p.nom,
            'prix': float(p.prix),
            'stock': p.stock,
            'est_en_promotion': p.est_en_promotion,
        }
        for p in produits
    ]
    return JsonResponse({'success': True, 'produits': data})

@login_required
def api_commandes(request):
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil commerçant non trouvé.'}, status=400)
    
    statut = request.GET.get('statut', '')
    page = int(request.GET.get('page', 1))
    
    commandes = Commande.objects.filter(commercant=commercant)
    
    if statut:
        commandes = commandes.filter(statut=statut)
    
    commandes = commandes.order_by('-date_commande')
    
    # Pagination
    paginator = Paginator(commandes, 10)
    try:
        commandes_page = paginator.page(page)
    except:
        commandes_page = paginator.page(1)
    
    commandes_data = []
    for commande in commandes_page:
        commandes_data.append({
            'id': commande.id,
            'reference': commande.reference,
            'client_nom': f"{commande.client.first_name} {commande.client.last_name}",
            'total': float(commande.total),
            'statut': commande.statut,
            'statut_display': commande.get_statut_display(),
            'date_commande': commande.date_commande.strftime('%d/%m/%Y %H:%M'),
            'nb_articles': commande.articles.count()
        })
    
    return JsonResponse({
        'success': True,
        'commandes': commandes_data,
        'has_previous': commandes_page.has_previous(),
        'has_next': commandes_page.has_next(),
        'page': page,
        'total_pages': paginator.num_pages
    })

@login_required
def api_detail_commande(request, commande_id):
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil commerçant non trouvé.'}, status=400)
    
    commande = get_object_or_404(Commande, id=commande_id, commercant=commercant)
    
    articles_data = []
    for article in commande.articles.all():
        articles_data.append({
            'produit_nom': article.produit.nom,
            'quantite': article.quantite,
            'prix_unitaire': float(article.prix_unitaire),
            'sous_total': float(article.sous_total)
        })
    
    commande_data = {
        'id': commande.id,
        'reference': commande.reference,
        'client': {
            'nom_complet': f"{commande.client.prenom} {commande.client.nom}",
            'email': commande.client.email,
            'telephone': commande.client.telephone
        },
        'adresse_livraison': commande.adresse_livraison,
        'instructions_livraison': commande.instructions_livraison,
        'methode_paiement': commande.get_methode_paiement_display(),
        'statut': commande.statut,
        'statut_display': commande.get_statut_display(),
        'total': float(commande.total),
        'date_commande': commande.date_commande.strftime('%d/%m/%Y %H:%M'),
        'articles': articles_data
    }
    
    return JsonResponse({
        'success': True,
        'commande': commande_data
    })

@login_required
@require_http_methods(["POST"])
def api_changer_statut_commande(request, commande_id):
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil commerçant non trouvé.'}, status=400)
    
    try:
        data = json.loads(request.body)
        nouveau_statut = data.get('statut')
        
        commande = get_object_or_404(Commande, id=commande_id, commercant=commercant)
        
        # Validation de la transition de statut
        transitions_valides = {
            'en_attente': ['confirmee', 'annulee'],
            'confirmee': ['en_preparation', 'annulee'],
            'en_preparation': ['en_livraison'],
            'en_livraison': ['livree'],
            'annulee': [],
            'livree': []
        }
        
        if nouveau_statut not in transitions_valides.get(commande.statut, []):
            return JsonResponse({
                'success': False,
                'message': 'Transition de statut non autorisée.'
            }, status=400)
        
        commande.statut = nouveau_statut
        commande.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Statut de la commande mis à jour: {commande.get_statut_display()}',
            'nouveau_statut': commande.statut,
            'statut_display': commande.get_statut_display()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Une erreur est survenue.'
        }, status=500)

@login_required
def api_stats_produits(request):
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil commerçant non trouvé.'}, status=400)
    
    # Produits les mieux notés
    produits_notes = Produit.objects.filter(
        commercant=commercant,
        avis__isnull=False
    ).annotate(
        note_moyenne=Avg('avis__note'),
        nb_avis=Count('avis')
    ).order_by('-note_moyenne')[:10]
    
    # Produits les plus vendus
    produits_vendus = ArticleCommande.objects.filter(
        commande__commercant=commercant
    ).values(
        'produit__id', 'produit__nom'
    ).annotate(
        total_vendu=Sum('quantite'),
        ca_total=Sum(F('quantite') * F('prix_unitaire'))
    ).order_by('-total_vendu')[:10]
    
    # Stock faible
    stock_faible = Produit.objects.filter(
        commercant=commercant,
        stock__lte=F('stock_min')
    ).order_by('stock')[:10]
    
    produits_notes_data = []
    for produit in produits_notes:
        produits_notes_data.append({
            'id': produit.id,
            'nom': produit.nom,
            'note_moyenne': round(produit.note_moyenne, 1),
            'nb_avis': produit.nb_avis
        })
    
    produits_vendus_data = []
    for pv in produits_vendus:
        produits_vendus_data.append({
            'id': pv['produit__id'],
            'nom': pv['produit__nom'],
            'total_vendu': pv['total_vendu'],
            'ca_total': float(pv['ca_total'])
        })
    
    stock_faible_data = []
    for produit in stock_faible:
        stock_faible_data.append({
            'id': produit.id,
            'nom': produit.nom,
            'stock_actuel': produit.stock,
            'stock_min': produit.stock_min
        })
    
    return JsonResponse({
        'success': True,
        'produits_notes': produits_notes_data,
        'produits_vendus': produits_vendus_data,
        'stock_faible': stock_faible_data
    })

@login_required
def api_notifications(request):
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil commerçant non trouvé.'}, status=400)
    
    # Commandes en attente
    commandes_attente = Commande.objects.filter(
        commercant=commercant,
        statut='en_attente'
    ).count()
    
    # Stock faible
    stock_faible = Produit.objects.filter(
        commercant=commercant,
        stock__lte=F('stock_min')
    ).count()
    
    # Avis en attente de modération
    avis_attente = Avis.objects.filter(
        produit__commercant=commercant,
        est_approuve=False
    ).count()
    
    return JsonResponse({
        'success': True,
        'notifications': {
            'commandes_attente': commandes_attente,
            'stock_faible': stock_faible,
            'avis_attente': avis_attente,
            'total': commandes_attente + stock_faible + avis_attente
        }
    })

@login_required
def gestion_commandes(request):
    """
    Vue pour que les commerçants voient et gèrent les commandes de leur boutique
    """
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil commerçant.')
        return redirect('clients:accueil')
    
    # Récupérer toutes les commandes pour ce commerçant
    commandes = Commande.objects.filter(commercant=commercant).order_by('-date_commande')
    
    # Filtrage par statut
    statut = request.GET.get('statut', '')
    if statut:
        commandes = commandes.filter(statut=statut)
    
    # Pagination
    paginator = Paginator(commandes, 10)
    page = request.GET.get('page')
    commandes_page = paginator.get_page(page)
    
    context = {
        'commandes': commandes_page,
        'statut': statut,
    }
    
    return render(request, 'commercants/gestion_commandes.html', context)

@login_required
def detail_commande_commercant(request, commande_id):
    """
    Vue pour voir les détails d'une commande du commerçant
    """
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil commerçant.')
        return redirect('clients:accueil')
    
    commande = get_object_or_404(Commande, id=commande_id, commercant=commercant)
    
    context = {
        'commande': commande,
    }
    
    return render(request, 'commercants/detail_commande.html', context)

@login_required
@require_http_methods(["POST"])
def api_valider_commande(request, commande_id):
    """
    API pour valider une commande et la rendre disponible pour les livreurs
    """
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil commerçant non trouvé.'}, status=400)
    
    commande = get_object_or_404(Commande, id=commande_id, commercant=commercant)
    
    # Vérifier que la commande peut être validée
    if commande.statut != 'en_attente':
        return JsonResponse({
            'success': False,
            'message': 'Cette commande ne peut pas être validée.'
        }, status=400)
    
    try:
        # Mettre à jour le statut de la commande
        commande.statut = 'validee'
        commande.save()
        
        # Créer un point de livraison sécurisé - CORRECTION
        adresse_livraison_point = None
        if commande.latitude_livraison and commande.longitude_livraison:
            try:
                lat = float(commande.latitude_livraison)
                lng = float(commande.longitude_livraison)
                # Vérifier que les coordonnées ne sont pas nulles
                if lat != 0 and lng != 0:
                    adresse_livraison_point = Point(lng, lat, srid=4326)
            except (ValueError, TypeError) as e:
                print(f"Erreur création point livraison: {e}")
        
        # Créer un point boutique sécurisé - CORRECTION
        boutique_point = None
        if commercant.latitude and commercant.longitude:
            try:
                lat = float(commercant.latitude)
                lng = float(commercant.longitude)
                if lat != 0 and lng != 0:
                    boutique_point = Point(lng, lat, srid=4326)
            except (ValueError, TypeError) as e:
                print(f"Erreur création point boutique: {e}")
        
        # Créer une livraison associée à cette commande
        livraison = Livraison.objects.create(
            commande=commande,
            statut='attribuee',
            cout_livraison=Decimal('500.00'),  # Coût de livraison par défaut
            adresse_livraison_point=adresse_livraison_point,
            boutique_point=boutique_point
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Commande validée avec succès. Elle est maintenant disponible pour les livreurs.',
            'nouveau_statut': commande.statut,
            'statut_display': commande.get_statut_display(),
            'livraison_id': livraison.id
        })
        
    except Exception as e:
        print(f"Error in api_valider_commande: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Une erreur est survenue: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def api_refuser_commande(request, commande_id):
    """
    API pour refuser une commande
    """
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil commerçant non trouvé.'}, status=400)
    
    commande = get_object_or_404(Commande, id=commande_id, commercant=commercant)
    
    # Vérifier que la commande peut être refusée
    if commande.statut not in ['en_attente', 'validee']:
        return JsonResponse({
            'success': False,
            'message': 'Cette commande ne peut pas être refusée.'
        }, status=400)
    
    try:
        # Mettre à jour le statut de la commande
        commande.statut = 'annulee'
        commande.save()
        
        # Si une livraison existe, l'annuler aussi
        if hasattr(commande, 'livraison'):
            commande.livraison.statut = 'annulee'
            commande.livraison.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Commande refusée.',
            'nouveau_statut': commande.statut,
            'statut_display': commande.get_statut_display()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Une erreur est survenue: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def api_preparer_commande(request, commande_id):
    """
    API pour marquer une commande comme en préparation
    """
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil commerçant non trouvé.'}, status=400)
    
    commande = get_object_or_404(Commande, id=commande_id, commercant=commercant)
    
    # Vérifier que la commande peut être marquée comme en préparation
    if commande.statut != 'validee':
        return JsonResponse({
            'success': False,
            'message': 'Cette commande ne peut pas être marquée comme en préparation.'
        }, status=400)
    
    try:
        # Mettre à jour le statut de la commande
        commande.statut = 'en_preparation'
        commande.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Commande marquée comme en préparation.',
            'nouveau_statut': commande.statut,
            'statut_display': commande.get_statut_display()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Une erreur est survenue: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def api_commande_prete(request, commande_id):
    """
    API pour marquer une commande comme prête pour la livraison
    """
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil commerçant non trouvé.'}, status=400)
    
    commande = get_object_or_404(Commande, id=commande_id, commercant=commercant)
    
    # Vérifier que la commande peut être marquée comme prête
    if commande.statut != 'en_preparation':
        return JsonResponse({
            'success': False,
            'message': 'Cette commande ne peut pas être marquée comme prête.'
        }, status=400)
    
    try:
        # Mettre à jour le statut de la commande
        commande.statut = 'prete'
        commande.save()
        
        # Mettre à jour le statut de la livraison si elle existe
        if hasattr(commande, 'livraison'):
            commande.livraison.statut = 'attribuee'
            commande.livraison.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Commande marquée comme prête pour la livraison.',
            'nouveau_statut': commande.statut,
            'statut_display': commande.get_statut_display()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Une erreur est survenue: {str(e)}'
        }, status=500)

@login_required
def portefeuille_commercant(request):
    """Page de gestion du portefeuille pour commerçants"""
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil commerçant.')
        return redirect('clients:accueil')
    
    portefeuille, created = Portefeuille.objects.get_or_create(user=request.user)
    
    # Statistiques spécifiques aux commerçants
    total_ventes = Commission.objects.filter(
        commande__commercant=commercant,
        est_transfere=True
    ).aggregate(total=Sum('montant_commercant'))['total'] or 0
    
    total_commissions = Commission.objects.filter(
        commande__commercant=commercant,
        est_transfere=True
    ).aggregate(total=Sum('commission_plateforme'))['total'] or 0
    
    # Commandes du mois
    debut_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ventes_mois = Commission.objects.filter(
        commande__commercant=commercant,
        est_transfere=True,
        date_calcul__gte=debut_mois
    ).aggregate(total=Sum('montant_commercant'))['total'] or 0
    
    # Transactions récentes
    transactions = portefeuille.transactions.all().order_by('-date_transaction')[:20]
    
    # Retraits
    retraits = portefeuille.retraits.all().order_by('-date_demande')[:10]
    
    context = {
        'portefeuille': portefeuille,
        'commercant': commercant,
        'total_ventes': total_ventes,
        'total_commissions': total_commissions,
        'ventes_mois': ventes_mois,
        'transactions': transactions,
        'retraits': retraits,
    }
    
    return render(request, 'commercants/portefeuille.html', context)

@login_required
def demande_retrait_commercant(request):
    """Demande de retrait pour commerçants - VERSION ULTRA MODERNE"""
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        messages.error(request, '❌ Vous n\'avez pas de profil commerçant.')
        return redirect('clients:accueil')
    
    portefeuille, created = Portefeuille.objects.get_or_create(user=request.user)
    
    # Récupérer les retraits récents (10 derniers)
    retraits_recents = portefeuille.retraits.all().order_by('-date_demande')[:10]
    
    if request.method == 'POST':
        form = DemandeRetraitForm(request.POST, portefeuille=portefeuille)
        if form.is_valid():
            try:
                # Créer l'objet retrait
                retrait = form.save(commit=False)
                retrait.portefeuille = portefeuille
                retrait.calculer_frais()
                
                # Vérifications supplémentaires
                frais = retrait.montant * Decimal('0.02')
                total_requis = retrait.montant + frais
                
                if portefeuille.solde < total_requis:
                    messages.error(
                        request,
                        f'❌ Solde insuffisant. Solde disponible: {portefeuille.solde:.0f} FCFA, '
                        f'Total requis: {total_requis:.0f} FCFA (inclut les frais de 2%)'
                    )
                    return render(request, 'commercants/demande_retrait.html', {
                        'form': form,
                        'portefeuille': portefeuille,
                        'commercant': commercant,
                        'retraits_recents': retraits_recents,
                        'solde_minimum': Decimal('500.00'),
                    })
                
                # Sauvegarder le retrait
                retrait.save()
                
                print(f"🔄 Traitement retrait {retrait.id} pour {commercant.nom_boutique}")
                print(f"💰 Détails: {retrait.montant} FCFA → Frais: {retrait.frais_retrait} FCFA → Net: {retrait.montant_net} FCFA")
                
                # Si mobile money, initier le paiement PayGate
                if retrait.methode == 'mobile_money':
                    success = retrait.initier_paiement_retrait(
                        phone_number=form.cleaned_data['numero_compte'],
                        operateur=form.cleaned_data['operateur']
                    )
                    
                    if success:
                        messages.success(
                            request,
                            f'✅ Demande de retrait envoyée ! '
                            f'Montant: {retrait.montant:.0f} FCFA | '
                            f'Frais: {retrait.frais_retrait:.0f} FCFA | '
                            f'Net: {retrait.montant_net:.0f} FCFA\n\n'
                            f'📱 Un message a été envoyé au {form.cleaned_data["numero_compte"]}. '
                            f'Veuillez confirmer le paiement pour finaliser le retrait.'
                        )
                    else:
                        messages.error(
                            request,
                            f'❌ Erreur lors de l\'envoi du paiement. '
                            f'Veuillez réessayer ou contacter le support.'
                        )
                else:
                    # Pour virement bancaire, marquer comme en attente
                    messages.success(
                        request,
                        f'✅ Demande de retrait enregistrée ! '
                        f'Montant: {retrait.montant:.0f} FCFA | '
                        f'Frais: {retrait.frais_retrait:.0f} FCFA | '
                        f'Net: {retrait.montant_net:.0f} FCFA\n\n'
                        f'🕒 Votre demande sera traitée sous 24-48 heures.'
                    )
                
                return redirect('commercants:portefeuille_commercant')
                
            except Exception as e:
                print(f"💥 Erreur critique lors du retrait: {str(e)}")
                import traceback
                traceback.print_exc()
                
                messages.error(
                    request,
                    f'❌ Une erreur technique est survenue. '
                    f'Veuillez réessayer ou contacter le support.'
                )
        else:
            # Afficher les erreurs de formulaire de manière stylée
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"⚠️ {form.fields[field].label}: {error}")
    else:
        # Données initiales avec valeurs par défaut
        initial_data = {
            'nom_beneficiaire': commercant.nom_boutique,
            'numero_compte': request.user.telephone,
            'operateur': 'FLOOZ',
            'methode': 'mobile_money'
        }
        form = DemandeRetraitForm(portefeuille=portefeuille, initial=initial_data)
    
    context = {
        'form': form,
        'portefeuille': portefeuille,
        'commercant': commercant,
        'retraits_recents': retraits_recents,
        'solde_minimum': Decimal('500.00'),
    }
    
    return render(request, 'commercants/demande_retrait.html', context)

@login_required
def api_statistiques_commercant(request):
    """API pour les statistiques du commerçant"""
    try:
        commercant = request.user.commercant_profile
    except Commercant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profil commerçant non trouvé.'}, status=400)
    
    portefeuille, created = Portefeuille.objects.get_or_create(user=request.user)
    
    # Statistiques des 30 derniers jours
    date_debut = timezone.now() - timedelta(days=30)
    
    ventes_30j = Commission.objects.filter(
        commande__commercant=commercant,
        est_transfere=True,
        date_calcul__gte=date_debut
    ).aggregate(total=Sum('montant_commercant'))['total'] or 0
    
    commandes_30j = Commande.objects.filter(
        commercant=commercant,
        statut_paiement='paye',
        date_commande__gte=date_debut
    ).count()
    
    return JsonResponse({
        'success': True,
        'statistiques': {
            'solde_actuel': float(portefeuille.solde),
            'ventes_30j': float(ventes_30j),
            'commandes_30j': commandes_30j,
            'total_ventes': float(Commission.objects.filter(
                commande__commercant=commercant,
                est_transfere=True
            ).aggregate(total=Sum('montant_commercant'))['total'] or 0),
        }
    })