from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from .forms import ClientInscriptionForm, ProfilForm, AvisForm
from .models import Client, Panier, ArticlePanier, Commande, ArticleCommande, Favori, Avis
from commercants.models import Commercant, Produit
from livraisons.models import Livraison
from django.urls import reverse, reverse_lazy

from django.utils import timezone
import json


def redirection_apres_connexion(request):
    user = request.user
    if user.type_utilisateur == 'livreur':
        return redirect('livraisons:tableau_de_bord')
    elif user.type_utilisateur == 'commercant':
        return redirect('commercants:tableau_de_bord')
    elif user.type_utilisateur == 'admin':
        return redirect('/admin/')
    else:
        return redirect('clients:accueil')

@login_required
@require_http_methods(["POST"])
def api_modifier_panier(request):
    """API pour modifier la quantité d'un article dans le panier"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantite = int(data.get('quantite', 1))
        
        print(f"API: Modifying item {item_id} to quantity {quantite}")
        
        article = get_object_or_404(ArticlePanier, id=item_id, panier__client=request.user.client_profile)
        
        if quantite <= 0:
            article.delete()
            message = 'Produit retiré du panier.'
            article_data = None
        elif quantite <= article.produit.stock:
            article.quantite = quantite
            article.save()
            message = 'Quantité mise à jour.'
            article_data = {
                'id': article.id,
                'sous_total': float(article.sous_total)
            }
        else:
            return JsonResponse({
                'success': False,
                'message': 'Quantité non disponible en stock.'
            }, status=400)
        
        panier = article.panier
        total_panier = panier.total
        nombre_articles = panier.items.aggregate(total=Sum('quantite'))['total'] or 0
        
        return JsonResponse({
            'success': True,
            'message': message,
            'total_panier': float(total_panier),
            'nombre_articles': nombre_articles,
            'article': article_data
        })
        
    except Exception as e:
        print(f"Error in api_modifier_panier: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Une erreur est survenue lors de la mise à jour du panier.'
        }, status=500)



def accueil(request):
    # Boutiques récentes et actives
    boutiques = Commercant.objects.filter(est_actif=True).order_by('-date_creation')[:6]
    
    # Produits en promotion
    produits_promotion = Produit.objects.filter(
        est_actif=True,
        est_en_promotion=True
    ).order_by('-date_ajout')[:8]
    
    # Produits populaires (basé sur les avis)
    produits_populaires = Produit.objects.filter(
        est_actif=True,
        avis__isnull=False
    ).annotate(
        note_moyenne=Avg('avis__note'),
        nb_avis=Count('avis')
    ).order_by('-note_moyenne', '-nb_avis')[:8]
    
    # Produits tendance (basé sur les commandes récentes)
    produits_tendance = Produit.objects.filter(
        est_actif=True,
        articlecommande__commande__date_commande__gte=timezone.now() - timezone.timedelta(days=7)
    ).annotate(
        nb_commandes=Count('articlecommande')
    ).order_by('-nb_commandes')[:8]
    
    context = {
        'boutiques': boutiques,
        'produits_promotion': produits_promotion,
        'produits_populaires': produits_populaires,
        'produits_tendance': produits_tendance,
    }
    
    return render(request, 'clients/accueil.html', context)

def inscription_client(request):
    if request.method == 'POST':
        form = ClientInscriptionForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            
            # Créer un panier pour le client
            Panier.objects.get_or_create(client=user.client_profile)
            
            # Si le client a accepté la géolocalisation, essayer de récupérer les coordonnées
            if user.consentement_geolocalisation:
                try:
                    # Récupérer les coordonnées depuis les données du formulaire ou la requête
                    latitude = request.POST.get('latitude')
                    longitude = request.POST.get('longitude')
                    
                    if latitude and longitude:
                        user.latitude = latitude
                        user.longitude = longitude
                        user.save()
                        
                        # Géocoder l'adresse si elle n'est pas encore définie
                        if not user.adresse or user.adresse.strip() == '':
                            from django.contrib.gis.geos import Point
                            from geopy.geocoders import Nominatim
                            
                            try:
                                geolocator = Nominatim(user_agent="delivery_app")
                                location = geolocator.reverse(f"{latitude}, {longitude}")
                                if location and location.address:
                                    user.adresse = location.address
                                    user.save()
                            except Exception as e:
                                print(f"Erreur géocodage: {e}")
                                
                except Exception as e:
                    print(f"Erreur géolocalisation: {e}")
                    # Continuer sans géolocalisation
            
            messages.success(request, 'Bienvenue ! Votre compte a été créé avec succès.')
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Bienvenue ! Votre compte a été créé avec succès.',
                    'redirect_url': reverse('clients:accueil')
                })
            return redirect('clients:accueil')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
    else:
        form = ClientInscriptionForm()
    
    return render(request, 'clients/inscription.html', {'form': form})

# Ajouter une vue API pour mettre à jour la géolocalisation
@require_http_methods(["POST"])
def api_mettre_a_jour_geolocalisation(request):
    """API pour mettre à jour la géolocalisation de l'utilisateur"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur non authentifié.'
            }, status=401)
        
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if latitude and longitude:
            request.user.latitude = latitude
            request.user.longitude = longitude
            request.user.consentement_geolocalisation = True
            request.user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Géolocalisation mise à jour avec succès.'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Coordonnées manquantes.'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }, status=500)


def liste_boutiques(request):
    boutiques = Commercant.objects.filter(est_actif=True)
    
    # Filtrage par catégorie
    categorie = request.GET.get('categorie', '')
    if categorie:
        boutiques = boutiques.filter(categorie=categorie)
    
    # Recherche
    search = request.GET.get('search', '')
    if search:
        boutiques = boutiques.filter(
            Q(nom_boutique__icontains=search) |
            Q(description__icontains=search) |
            Q(adresse__icontains=search)
        )
    
    # Precompute counts for each boutique
    boutiques_data = []
    for boutique in boutiques:
        total_produits = boutique.produits.count()
        promo_count = boutique.produits.filter(est_en_promotion=True).count()
        
        boutiques_data.append({
            'boutique': boutique,
            'total_produits': total_produits,
            'promo_count': promo_count
        })
    
    context = {
        'boutiques_data': boutiques_data,
        'categorie': categorie,
        'search': search,
        'categories': Commercant.CATEGORIES,
    }
    
    return render(request, 'clients/liste_boutiques.html', context)

def detail_boutique(request, boutique_id):
    boutique = get_object_or_404(Commercant, id=boutique_id, est_actif=True)
    produits = boutique.produits.filter(est_actif=True)
    
    # Calculer les statistiques dans la vue
    total_produits = produits.count()
    produits_actifs = produits.filter(est_actif=True).count()
    produits_en_promotion = produits.filter(est_en_promotion=True).count()
    
    # Filtrage des produits
    categorie_produit = request.GET.get('categorie', '')
    if categorie_produit:
        produits = produits.filter(categorie=categorie_produit)
    
    # Tri
    tri = request.GET.get('tri', 'recent')
    if tri == 'prix_croissant':
        produits = produits.order_by('prix')
    elif tri == 'prix_decroissant':
        produits = produits.order_by('-prix')
    elif tri == 'promotion':
        produits = produits.filter(est_en_promotion=True)
    else:
        produits = produits.order_by('-date_ajout')
    
    context = {
        'boutique': boutique,
        'produits': produits,
        'total_produits': total_produits,
        'produits_actifs': produits_actifs,
        'produits_en_promotion': produits_en_promotion,
        'categorie_produit': categorie_produit,
        'tri': tri,
        'categories_produit': Produit.CATEGORIES_PRODUIT,
    }
    
    return render(request, 'clients/detail_boutique.html', context)

def detail_produit(request, produit_id):
    produit = get_object_or_404(Produit, id=produit_id, est_actif=True)
    boutique = produit.commercant
    
    # Produits similaires
    similaires = Produit.objects.filter(
        commercant=boutique,
        categorie=produit.categorie,
        est_actif=True
    ).exclude(id=produit.id)[:4]
    
    # Avis du produit
    avis_list = produit.avis.filter(est_approuve=True).order_by('-date_creation')
    note_moyenne = avis_list.aggregate(avg=Avg('note'))['avg'] or 0
    
    # Vérifier si le produit est dans les favoris - CORRIGÉ
    est_favori = False
    if request.user.is_authenticated:
        try:
            client_profile = request.user.client_profile
            est_favori = Favori.objects.filter(
                client=client_profile,
                produit=produit
            ).exists()
        except Client.DoesNotExist:
            # Si le profil client n'existe pas
            est_favori = False
    
    context = {
        'produit': produit,
        'boutique': boutique,
        'similaires': similaires,
        'avis_list': avis_list,
        'note_moyenne': note_moyenne,
        'est_favori': est_favori,
    }
    
    return render(request, 'clients/detail_produit.html', context)

def recherche(request):
    query = request.GET.get('q', '')
    produits = []
    boutiques = []
    
    if query:
        # Recherche de produits
        produits = Produit.objects.filter(
            Q(nom__icontains=query) |
            Q(description__icontains=query),
            est_actif=True
        ).order_by('-date_ajout')
        
        # Recherche de boutiques
        boutiques = Commercant.objects.filter(
            Q(nom_boutique__icontains=query) |
            Q(description__icontains=query),
            est_actif=True
        ).order_by('-date_creation')
    
    context = {
        'query': query,
        'produits': produits,
        'boutiques': boutiques,
    }
    
    return render(request, 'clients/recherche.html', context)

@login_required
def panier(request):
    panier, created = Panier.objects.get_or_create(client=request.user.client_profile)
    articles = panier.items.all()
    
    context = {
        'panier': panier,
        'articles': articles,
    }
    
    return render(request, 'clients/panier.html', context)

@login_required
@require_POST
def ajouter_au_panier(request, produit_id):
    produit = get_object_or_404(Produit, id=produit_id, est_actif=True)
    
    if not produit.est_en_stock:
        messages.error(request, 'Ce produit n\'est plus en stock.')
        return redirect('clients:detail_produit', produit_id=produit_id)
    
    panier, created = Panier.objects.get_or_create(client=request.user.client_profile)
    
    # Vérifier si le produit est déjà dans le panier
    article, article_created = ArticlePanier.objects.get_or_create(
        panier=panier,
        produit=produit,
        defaults={'quantite': 1}
    )
    
    if not article_created:
        # Vérifier si la quantité ne dépasse pas le stock
        if article.quantite < produit.stock:
            article.quantite += 1
            article.save()
        else:
            messages.warning(request, 'La quantité maximale disponible a été atteinte.')
    
    messages.success(request, 'Produit ajouté au panier.')
    return redirect('clients:panier')

@login_required
@require_POST
def modifier_panier(request, item_id):
    article = get_object_or_404(ArticlePanier, id=item_id, panier__client=request.user.client_profile)
    nouvelle_quantite = int(request.POST.get('quantite', 1))
    
    if nouvelle_quantite <= 0:
        article.delete()
        messages.info(request, 'Produit retiré du panier.')
    elif nouvelle_quantite <= article.produit.stock:
        article.quantite = nouvelle_quantite
        article.save()
        messages.success(request, 'Quantité mise à jour.')
    else:
        messages.warning(request, 'Quantité non disponible en stock.')
    
    return redirect('clients:panier')

@login_required
@require_POST
def supprimer_du_panier(request, item_id):
    article = get_object_or_404(ArticlePanier, id=item_id, panier__client=request.user.client_profile)
    article.delete()
    messages.info(request, 'Produit retiré du panier.')
    return redirect('clients:panier')

@login_required
@require_http_methods(["POST"])
def finaliser_commande(request):
    """
    Finalise la commande et simule le processus de paiement
    """
    try:
        panier = get_object_or_404(Panier, client=request.user.client_profile)
        articles = panier.items.select_related('produit', 'produit__commercant')
        
        if not articles.exists():
            return JsonResponse({
                'success': False,
                'message': 'Votre panier est vide.'
            }, status=400)
        
        # Récupérer les données du formulaire
        adresse_livraison = request.POST.get('adresse_livraison', request.user.adresse)
        instructions_livraison = request.POST.get('instructions_livraison', '')
        methode_paiement = request.POST.get('methode_paiement', 'espece')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        # Vérifier que tous les produits sont encore en stock
        for article in articles:
            if article.quantite > article.produit.stock:
                error_msg = f"Le produit {article.produit.nom} n'est plus disponible en quantité suffisante."
                return JsonResponse({
                    'success': False,
                    'message': error_msg
                }, status=400)
        
        # Vérifier l'adresse de livraison
        if not adresse_livraison or adresse_livraison == 'Aucune adresse définie':
            return JsonResponse({
                'success': False,
                'message': 'Veuillez définir une adresse de livraison.'
            }, status=400)
        
        # Vérifier les coordonnées GPS
        if not latitude or not longitude:
            return JsonResponse({
                'success': False,
                'message': 'Veuillez sélectionner une adresse sur la carte.'
            }, status=400)
        
        # Créer la commande
        commande = Commande.objects.create(
            client=request.user.client_profile,
            commercant=articles.first().produit.commercant,
            total=panier.total,
            adresse_livraison=adresse_livraison,
            instructions_livraison=instructions_livraison,
            methode_paiement=methode_paiement,
            statut_paiement='paye' if methode_paiement != 'espece' else 'en_attente',
            statut='validee' if methode_paiement != 'espece' else 'en_attente',
            latitude_livraison=latitude,
            longitude_livraison=longitude
        )
        
        # Créer les articles de commande
        for article in articles:
            ArticleCommande.objects.create(
                commande=commande,
                produit=article.produit,
                quantite=article.quantite,
                prix_unitaire=article.produit.prix_effectif
            )
            
            # Mettre à jour le stock
            produit = article.produit
            produit.stock -= article.quantite
            produit.save()
        
        # Vider le panier
        articles.delete()
        
        # Préparer la réponse
        return JsonResponse({
            'success': True,
            'message': 'Commande créée avec succès !' if methode_paiement == 'espece' else 'Paiement confirmé ! Commande validée.',
            'commande_id': commande.id,
            'redirect_url': reverse('clients:confirmation_commande', args=[commande.id])
        })
            
    except Exception as e:
        print(f"Error in finaliser_commande: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Une erreur est survenue lors de la création de la commande.'
        }, status=500)

@login_required
def passer_commande(request):
    """Page pour finaliser la commande avec sélection d'adresse sur carte"""
    try:
        panier = get_object_or_404(Panier, client=request.user.client_profile)
        articles = panier.items.select_related('produit', 'produit__commercant')
        
        if not articles.exists():
            messages.error(request, 'Votre panier est vide.')
            return redirect('clients:panier')
        
        context = {
            'panier': panier,
            'articles': articles,
        }
        
        return render(request, 'clients/passer_commande.html', context)
        
    except Exception as e:
        messages.error(request, 'Erreur lors du chargement de la page de commande.')
        return redirect('clients:panier')

@login_required
def confirmation_commande(request, commande_id):
    """
    Page de confirmation de commande
    """
    commande = get_object_or_404(Commande, id=commande_id, client=request.user.client_profile)
    
    context = {
        'commande': commande,
    }
    
    return render(request, 'clients/confirmation_commande.html', context)

@login_required
def mes_commandes(request):
    try:
        # Vérifier si le profil client existe
        client_profile = request.user.client_profile
        commandes = Commande.objects.filter(client=client_profile).order_by('-date_commande')
    except Client.DoesNotExist:
        # Si le profil client n'existe pas, créer un message et rediriger
        messages.error(request, 'Profil client non trouvé. Veuillez contacter le support.')
        return redirect('clients:accueil')
    
    context = {
        'commandes': commandes,
    }
    
    return render(request, 'clients/mes_commandes.html', context)

@login_required
def detail_commande(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id, client=request.user.client_profile)
    
    context = {
        'commande': commande,
    }
    
    return render(request, 'clients/detail_commande.html', context)

@login_required
@require_POST
def ajouter_favori(request, produit_id):
    produit = get_object_or_404(Produit, id=produit_id, est_actif=True)
    
    favori, created = Favori.objects.get_or_create(
        client=request.user.client_profile,
        produit=produit
    )
    
    if created:
        messages.success(request, 'Produit ajouté aux favoris.')
    else:
        messages.info(request, 'Produit déjà dans vos favoris.')
    
    return redirect('clients:detail_produit', produit_id=produit_id)

@login_required
@require_POST
def supprimer_favori(request, produit_id):
    produit = get_object_or_404(Produit, id=produit_id)
    
    try:
        favori = Favori.objects.get(client=request.user.client_profile, produit=produit)
        favori.delete()
        messages.info(request, 'Produit retiré des favoris.')
    except Favori.DoesNotExist:
        messages.warning(request, 'Ce produit n\'est pas dans vos favoris.')
    
    return redirect('clients:mes_favoris')

@login_required
def mes_favoris(request):
    try:
        client_profile = request.user.client_profile
        favoris = Favori.objects.filter(client=client_profile).select_related('produit', 'produit__commercant').order_by('-date_ajout')
    except Client.DoesNotExist:
        favoris = []
        messages.error(request, 'Profil client non trouvé.')
    
    context = {
        'favoris': favoris,
    }
    
    return render(request, 'clients/mes_favoris.html', context)

@login_required
def profil(request):
    return render(request, 'clients/profil.html', {'client': request.user})

@login_required
def modifier_profil(request):
    if request.method == 'POST':
        form = ProfilForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès.')
            return redirect('clients:profil')
    else:
        form = ProfilForm(instance=request.user)
    
    return render(request, 'clients/modifier_profil.html', {'form': form})

@login_required
@require_http_methods(["POST"])
def api_ajouter_au_panier(request):
    try:
        data = json.loads(request.body)
        produit_id = data.get('produit_id')
        quantite = int(data.get('quantite', 1))
        
        produit = get_object_or_404(Produit, id=produit_id, est_actif=True)
        
        if not produit.est_en_stock:
            return JsonResponse({
                'success': False,
                'message': 'Ce produit n\'est plus en stock.'
            }, status=400)
        
        panier, created = Panier.objects.get_or_create(client=request.user.client_profile)
        
        # Vérifier si le produit est déjà dans le panier
        article, article_created = ArticlePanier.objects.get_or_create(
            panier=panier,
            produit=produit,
            defaults={'quantite': quantite}
        )
        
        if not article_created:
            nouvelle_quantite = article.quantite + quantite
            if nouvelle_quantite <= produit.stock:
                article.quantite = nouvelle_quantite
                article.save()
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'La quantité maximale disponible a été atteinte.'
                }, status=400)
        
        # Calculer le nouveau total du panier
        total_panier = panier.total
        nombre_articles = panier.items.aggregate(total=Sum('quantite'))['total'] or 0
        
        return JsonResponse({
            'success': True,
            'message': 'Produit ajouté au panier.',
            'total_panier': float(total_panier),
            'nombre_articles': nombre_articles,
            'article': {
                'id': article.id,
                'produit_nom': article.produit.nom,
                'quantite': article.quantite,
                'prix_unitaire': float(article.produit.prix_effectif),
                'sous_total': float(article.sous_total)
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Une erreur est survenue.'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def api_supprimer_du_panier(request):
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        article = get_object_or_404(ArticlePanier, id=item_id, panier__client=request.user.client_profile)
        panier = article.panier
        article.delete()
        
        total_panier = panier.total
        nombre_articles = panier.items.aggregate(total=Sum('quantite'))['total'] or 0
        
        return JsonResponse({
            'success': True,
            'message': 'Produit retiré du panier.',
            'total_panier': float(total_panier),
            'nombre_articles': nombre_articles
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Une erreur est survenue.'
        }, status=500)

@login_required
def api_infos_panier(request):
    try:
        panier, created = Panier.objects.get_or_create(client=request.user.client_profile)
        articles = panier.items.select_related('produit', 'produit__commercant')
        
        articles_data = []
        for article in articles:
            # Gérer le cas où l'image est None
            produit_image = ''
            if article.produit.photo and hasattr(article.produit.photo, 'url'):
                produit_image = article.produit.photo.url
            
            articles_data.append({
                'id': article.id,
                'produit_id': article.produit.id,
                'produit_nom': article.produit.nom,
                'produit_image': produit_image,
                'quantite': article.quantite,
                'prix_unitaire': float(article.produit.prix_effectif),
                'sous_total': float(article.sous_total),
                'stock_disponible': article.produit.stock,
                'boutique_nom': article.produit.commercant.nom_boutique,
                'est_en_promotion': article.produit.est_en_promotion,
                'prix_original': float(article.produit.prix),
                'prix_promotionnel': float(article.produit.prix_promotionnel) if article.produit.est_en_promotion else None
            })
        
        nombre_articles = panier.items.aggregate(total=Sum('quantite'))['total'] or 0
        
        return JsonResponse({
            'success': True,
            'total_panier': float(panier.total),
            'nombre_articles': nombre_articles,
            'articles': articles_data
        })
        
    except Exception as e:
        print(f"Error in api_infos_panier: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Une erreur est survenue: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def api_ajouter_favori(request):
    try:
        data = json.loads(request.body)
        produit_id = data.get('produit_id')
        
        produit = get_object_or_404(Produit, id=produit_id, est_actif=True)
        
        favori, created = Favori.objects.get_or_create(
            client=request.user.client_profile,
            produit=produit
        )
        
        if created:
            message = 'Produit ajouté aux favoris.'
        else:
            message = 'Produit déjà dans vos favoris.'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'est_favori': True
        })
        
    except Client.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Profil client non trouvé.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Une erreur est survenue.'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def api_supprimer_favori(request):
    try:
        data = json.loads(request.body)
        produit_id = data.get('produit_id')
        
        produit = get_object_or_404(Produit, id=produit_id)
        
        try:
            favori = Favori.objects.get(client=request.user.client_profile, produit=produit)
            favori.delete()
            message = 'Produit retiré des favoris.'
        except Favori.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Ce produit n\'est pas dans vos favoris.'
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'message': message,
            'est_favori': False
        })
        
    except Client.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Profil client non trouvé.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Une erreur est survenue.'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def api_ajouter_avis(request):
    try:
        data = json.loads(request.body)
        produit_id = data.get('produit_id')
        note = int(data.get('note'))
        commentaire = data.get('commentaire', '')
        
        produit = get_object_or_404(Produit, id=produit_id, est_actif=True)
        
        # Vérifier si l'utilisateur a déjà acheté ce produit
        a_achete = ArticleCommande.objects.filter(
            commande__client=request.user.client_profile,
            produit=produit,
            commande__statut='livree'
        ).exists()
        
        if not a_achete:
            return JsonResponse({
                'success': False,
                'message': 'Vous devez avoir acheté ce produit pour pouvoir le noter.'
            }, status=400)
        
        # Vérifier si l'utilisateur a déjà noté ce produit
        avis_existant = Avis.objects.filter(client=request.user.client_profile, produit=produit).first()
        
        if avis_existant:
            avis_existant.note = note
            avis_existant.commentaire = commentaire
            avis_existant.est_approuve = False
            avis_existant.save()
            avis = avis_existant
            message = 'Votre avis a été mis à jour.'
        else:
            avis = Avis.objects.create(
                client=request.user.client_profile,
                produit=produit,
                note=note,
                commentaire=commentaire
            )
            message = 'Votre avis a été ajouté.'
        
        # Recalculer la note moyenne
        note_moyenne = produit.avis.filter(est_approuve=True).aggregate(avg=Avg('note'))['avg'] or 0
        nb_avis = produit.avis.filter(est_approuve=True).count()
        
        return JsonResponse({
            'success': True,
            'message': message,
            'avis': {
                'id': avis.id,
                'note': avis.note,
                'commentaire': avis.commentaire,
                'date_creation': avis.date_creation.strftime('%d/%m/%Y'),
                'client_nom': f"{request.user.first_name} {request.user.last_name}"
            },
            'statistiques': {
                'note_moyenne': round(note_moyenne, 1),
                'nb_avis': nb_avis
            }
        })
        
    except Client.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Profil client non trouvé.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Une erreur est survenue.'
        }, status=500)

def api_produits_suggestions(request):
    try:
        produit_id = request.GET.get('produit_id')
        limit = int(request.GET.get('limit', 4))
        
        if produit_id:
            produit = get_object_or_404(Produit, id=produit_id)
            suggestions = Produit.objects.filter(
                Q(categorie=produit.categorie) | Q(commercant=produit.commercant),
                est_actif=True
            ).exclude(id=produit.id).order_by('?')[:limit]
        else:
            suggestions = Produit.objects.filter(
                est_actif=True
            ).order_by('?')[:limit]
        
        suggestions_data = []
        for produit in suggestions:
            suggestions_data.append({
                'id': produit.id,
                'nom': produit.nom,
                'prix': float(produit.prix_effectif),
                'image': produit.photo.url if produit.photo else '',
                'boutique_nom': produit.commercant.nom_boutique,
                'est_en_promotion': produit.est_en_promotion,
                'promo_prix': float(produit.prix_promotionnel) if produit.est_en_promotion else None
            })
        
        return JsonResponse({
            'success': True,
            'suggestions': suggestions_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Une erreur est survenue.'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def api_changer_statut_commande(request):
    try:
        data = json.loads(request.body)
        commande_id = data.get('commande_id')
        statut = data.get('statut')
        
        commande = get_object_or_404(Commande, id=commande_id, client=request.user.client_profile)
        
        if statut == 'annulee':
            # Vérifier si la commande peut être annulée
            if commande.statut not in ['en_attente', 'confirmee']:
                return JsonResponse({
                    'success': False,
                    'message': 'Cette commande ne peut pas être annulée.'
                }, status=400)
            
            # Restocker les produits
            for article in commande.articles.all():
                produit = article.produit
                produit.stock += article.quantite
                produit.save()
        
        commande.statut = statut
        commande.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Commande {commande.get_statut_display().lower()}.',
            'nouveau_statut': commande.statut,
            'statut_display': commande.get_statut_display()
        })
        
    except Client.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Profil client non trouvé.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Une erreur est survenue.'
        }, status=500)