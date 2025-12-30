from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from .forms import ClientInscriptionForm, ProfilForm, DemandeRetraitForm, AvisForm, DepotPayGateForm, DepotMobileMoneyForm
from .models import Client, Panier, ArticlePanier, Commande, ArticleCommande, Favori, Avis, Portefeuille, Commission, RetraitCommercant, DepotPortefeuille
from commercants.models import Commercant, Produit
from livraisons.models import Livraison
from django.urls import reverse, reverse_lazy
# csrf_exempt
from django.views.decorators.csrf import csrf_exempt
from .paygate import PayGateGlobal
import json
import uuid
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
    
    # Filtrage par recherche
    search = request.GET.get('search', '')
    if search:
        boutiques = boutiques.filter(
            Q(nom_boutique__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Précharger les produits pour optimiser les requêtes
    boutiques = boutiques.prefetch_related('produits_commercant')
    
    # Préparer les données pour chaque boutique
    boutiques_data = []
    for boutique in boutiques:
        # ⚠️ CORRECTION : Utiliser le nouveau related_name
        produits_actifs = boutique.produits_commercant.filter(est_actif=True)
        total_produits = produits_actifs.count()
        
        # Calculer la note moyenne si nécessaire
        note_moyenne = None
        if hasattr(boutique, 'produits_commercant'):
            # Logique pour calculer la note moyenne
            pass
        
        boutiques_data.append({
            'boutique': boutique,
            'total_produits': total_produits,
            'note_moyenne': note_moyenne,
        })
    
    context = {
        'boutiques_data': boutiques_data,
        'categories': Commercant.CATEGORIES,
        'categorie': categorie,
        'search': search,
    }
    
    return render(request, 'clients/liste_boutiques.html', context)

def detail_boutique(request, boutique_id):
    boutique = get_object_or_404(Commercant, id=boutique_id, est_actif=True)
    produits = boutique.produits_commercant.filter(est_actif=True)
    
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

######################################################################
######################################################################
###################################################################
from decimal import Decimal
@login_required
@require_http_methods(["POST"])
def finaliser_commande(request):
    """
    Finalise la commande avec gestion du portefeuille et des commissions
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
        
        print(f"🔍 Finalisation commande - Méthode: {methode_paiement}, Adresse: {adresse_livraison}")
        
        # Vérifier que tous les produits sont encore en stock
        for article in articles:
            if article.quantite > article.produit.stock:
                error_msg = f"Le produit {article.produit.nom} n'est plus disponible en quantité suffisante. Stock restant: {article.produit.stock}"
                print(f"❌ Stock insuffisant: {article.produit.nom}")
                return JsonResponse({
                    'success': False,
                    'message': error_msg
                }, status=400)
        
        # Vérifier l'adresse de livraison
        if not adresse_livraison or adresse_livraison.strip() == '':
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
        
        # Vérifier que les coordonnées sont valides
        try:
            lat_float = float(latitude)
            lng_float = float(longitude)
            if not (-90 <= lat_float <= 90 and -180 <= lng_float <= 180):
                return JsonResponse({
                    'success': False,
                    'message': 'Coordonnées GPS invalides.'
                }, status=400)
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'message': 'Coordonnées GPS invalides.'
            }, status=400)
        
        # Grouper les articles par commerçant
        articles_par_commercant = {}
        for article in articles:
            commercant = article.produit.commercant
            if commercant not in articles_par_commercant:
                articles_par_commercant[commercant] = []
            articles_par_commercant[commercant].append(article)
        
        # Vérifier si les commerçants sont actifs
        for commercant in articles_par_commercant.keys():
            if not commercant.est_actif:
                return JsonResponse({
                    'success': False,
                    'message': f'Le commerçant {commercant.nom_boutique} n\'est plus actif.'
                }, status=400)
        
        commandes_crees = []
        
        # Créer une commande par commerçant
        for commercant, articles_commercant in articles_par_commercant.items():
            # Calculer le total pour ce commerçant
            total_commercant = sum(article.sous_total for article in articles_commercant)
            
            print(f"🛒 Création commande pour {commercant.nom_boutique} - Total: {total_commercant} FCFA")
            
            # Créer la commande
            commande = Commande.objects.create(
                client=request.user.client_profile,
                commercant=commercant,
                total=total_commercant,
                adresse_livraison=adresse_livraison,
                instructions_livraison=instructions_livraison,
                methode_paiement=methode_paiement,
                statut_paiement='en_attente',
                statut='en_attente',
                latitude_livraison=latitude,
                longitude_livraison=longitude
            )
            
            # Créer les articles de commande
            for article in articles_commercant:
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
                
                print(f"📦 Article: {produit.nom} - Quantité: {article.quantite} - Stock restant: {produit.stock}")
            
            # GESTION DU PORTEFEUILLE ET COMMISSIONS
            if methode_paiement == 'portefeuille':
                print(f"💰 Paiement portefeuille détecté pour {commercant.nom_boutique}")
                
                # Vérifier le solde du client
                portefeuille_client, created = Portefeuille.objects.get_or_create(
                    user=request.user
                )
                
                print(f"💳 Solde client: {portefeuille_client.solde} FCFA, Total requis: {total_commercant} FCFA")
                
                if portefeuille_client.solde < total_commercant:
                    # Annuler cette commande spécifique
                    print(f"❌ Solde insuffisant pour {commercant.nom_boutique}")
                    for article_commande in commande.articles.all():
                        produit = article_commande.produit
                        produit.stock += article_commande.quantite
                        produit.save()
                    commande.delete()
                    
                    return JsonResponse({
                        'success': False,
                        'message': f'Solde insuffisant pour la commande chez {commercant.nom_boutique}. Solde disponible: {portefeuille_client.solde} FCFA, Total requis: {total_commercant} FCFA'
                    }, status=400)
                
                # Débiter le client
                print(f"💸 Débit du client: {total_commercant} FCFA")
                portefeuille_client.debiter(
                    total_commercant,
                    f"Paiement commande {commande.reference} - {commercant.nom_boutique}"
                )
                
                # CALCULER ET DISTRIBUER LES COMMISSIONS (90% commerçant, 10% plateforme)
                print(f"📊 Calcul des commissions pour {commercant.nom_boutique}")
                commission_plateforme = total_commercant * Decimal('0.10')  # 10%
                montant_commercant = total_commercant - commission_plateforme
                
                # Créer l'enregistrement de commission
                commission = Commission.objects.create(
                    commande=commande,
                    montant_commande=total_commercant,
                    commission_plateforme=commission_plateforme,
                    montant_commercant=montant_commercant,
                    taux_commission=10.00
                )
                
                # Créditer le commerçant immédiatement
                portefeuille_commercant, created = Portefeuille.objects.get_or_create(
                    user=commercant.user
                )
                portefeuille_commercant.crediter(
                    montant_commercant,
                    f"Vente commande {commande.reference}"
                )
                
                # Marquer la commission comme transférée
                commission.est_transfere = True
                commission.date_transfert = timezone.now()
                commission.save()
                
                print(f"✅ Commerçant crédité: {montant_commercant} FCFA")
                
                # Mettre à jour le statut de la commande
                commande.statut_paiement = 'paye'
                commande.statut = 'validee'
                commande.save()
                
                print(f"✅ Commande {commande.reference} validée et payée")
            
            commandes_crees.append(commande)
            print(f"✅ Commande créée: {commande.reference} pour {commercant.nom_boutique}")
        
        # Vider le panier (tous les articles, même ceux de différents commerçants)
        articles_count = articles.count()
        articles.delete()
        print(f"🗑️ Panier vidé - {articles_count} articles supprimés")
        
        # Gestion des autres méthodes de paiement
        if methode_paiement != 'portefeuille':
            print(f"🔄 Traitement méthode de paiement: {methode_paiement}")
            for commande in commandes_crees:
                if methode_paiement == 'espece':
                    commande.statut = 'validee'
                    commande.save()
                    print(f"💰 Commande {commande.reference} - Paiement à la livraison")
                elif methode_paiement == 'mobile_money':
                    # Le statut sera mis à jour après paiement via PayGate
                    print(f"📱 Commande {commande.reference} - Paiement mobile money en attente")
        
        # Préparer la réponse
        message = ""
        redirect_url = ""
        
        if methode_paiement == 'portefeuille':
            message = 'Commande(s) créée(s) avec succès ! Paiement effectué via votre portefeuille.'
            if len(commandes_crees) == 1:
                redirect_url = reverse('clients:confirmation_commande', args=[commandes_crees[0].id])
            else:
                redirect_url = reverse('clients:commandes_multiple_confirmation')
        else:
            if len(commandes_crees) == 1:
                commande = commandes_crees[0]
                if methode_paiement == 'espece':
                    message = 'Commande créée avec succès ! Paiement à la livraison.'
                    redirect_url = reverse('clients:confirmation_commande', args=[commande.id])
                else:
                    message = 'Commande créée avec succès ! Veuillez finaliser le paiement.'
                    redirect_url = reverse('clients:choix_paiement', args=[commande.id])
            else:
                message = 'Commandes créées avec succès !'
                if methode_paiement == 'espece':
                    message += ' Paiement à la livraison.'
                redirect_url = reverse('clients:commandes_multiple_confirmation')
        
        print(f"🎉 Finalisation réussie - {len(commandes_crees)} commande(s) créée(s)")
        print(f"📤 Redirection vers: {redirect_url}")
        
        return JsonResponse({
            'success': True,
            'message': message,
            'commandes_ids': [cmd.id for cmd in commandes_crees],
            'redirect_url': redirect_url
        })
            
    except Exception as e:
        print(f"❌ Error in finaliser_commande: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # En cas d'erreur, restaurer les stocks pour toutes les commandes créées
        try:
            if 'commandes_crees' in locals():
                for commande in commandes_crees:
                    print(f"🔄 Restauration du stock pour la commande {commande.reference}")
                    for article_commande in commande.articles.all():
                        produit = article_commande.produit
                        produit.stock += article_commande.quantite
                        produit.save()
                        print(f"📦 Stock restauré: {produit.nom} +{article_commande.quantite}")
                    commande.delete()
                    print(f"🗑️ Commande {commande.reference} supprimée")
        except Exception as delete_error:
            print(f"❌ Error cleaning up failed commands: {str(delete_error)}")
        
        return JsonResponse({
            'success': False,
            'message': 'Une erreur est survenue lors de la création de la commande. Veuillez réessayer.'
        }, status=500)
##########################################################################
##########################################################################
##########################################################################
# Vue API pour vérifier le statut d'une commande

@login_required
def confirmation_commande(request, commande_id):
    """
    Page de confirmation de commande
    """
    commande = get_object_or_404(Commande, id=commande_id, client=request.user.client_profile)
    
    # Préparer les données pour l'affichage
    articles = commande.articles.select_related('produit')
    total_articles = sum(article.quantite for article in articles)
    
    # Déterminer le statut d'affichage
    if commande.statut_paiement == 'paye':
        statut_message = "Paiement confirmé"
        statut_couleur = "success"
    elif commande.statut_paiement == 'en_attente' and commande.methode_paiement == 'espece':
        statut_message = "En attente de livraison - Paiement à la livraison"
        statut_couleur = "info"
    elif commande.statut_paiement == 'en_attente':
        statut_message = "En attente de paiement"
        statut_couleur = "warning"
    else:
        statut_message = commande.get_statut_paiement_display()
        statut_couleur = "secondary"
    
    context = {
        'commande': commande,
        'articles': articles,
        'total_articles': total_articles,
        'statut_message': statut_message,
        'statut_couleur': statut_couleur,
    }
    
    return render(request, 'clients/confirmation_commande.html', context)

@login_required
def annuler_commande(request, commande_id):
    """
    Annuler une commande (si elle est encore annulable)
    """
    if request.method == 'POST':
        try:
            commande = get_object_or_404(Commande, id=commande_id, client=request.user.client_profile)
            
            # Vérifier si la commande peut être annulée
            if commande.statut not in ['en_attente', 'validee']:
                messages.error(request, 'Cette commande ne peut plus être annulée.')
                return redirect('clients:detail_commande', commande_id=commande_id)
            
            # Restocker les produits
            for article in commande.articles.all():
                produit = article.produit
                produit.stock += article.quantite
                produit.save()
            
            # Marquer la commande comme annulée
            commande.statut = 'annulee'
            commande.statut_paiement = 'echec' if commande.statut_paiement == 'en_attente' else commande.statut_paiement
            commande.save()
            
            messages.success(request, 'Commande annulée avec succès.')
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Commande annulée avec succès.',
                    'redirect_url': reverse('clients:mes_commandes')
                })
                
            return redirect('clients:mes_commandes')
            
        except Exception as e:
            print(f"Error in annuler_commande: {str(e)}")
            messages.error(request, 'Erreur lors de l\'annulation de la commande.')
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Erreur lors de l\'annulation de la commande.'
                }, status=500)
                
            return redirect('clients:detail_commande', commande_id=commande_id)
    
    return redirect('clients:mes_commandes')

@login_required
def reessayer_paiement(request, commande_id):
    """
    Réessayer le paiement pour une commande en échec
    """
    commande = get_object_or_404(Commande, id=commande_id, client=request.user.client_profile)
    
    # Vérifier si la commande peut être repayée
    if commande.statut_paiement not in ['en_attente', 'echec']:
        messages.error(request, 'Cette commande ne peut pas être repayée.')
        return redirect('clients:detail_commande', commande_id=commande_id)
    
    # Rediriger vers le choix de paiement
    return redirect('clients:choix_paiement', commande_id=commande_id)

@login_required
def api_statut_commande(request, commande_id):
    """
    API pour vérifier le statut d'une commande
    """
    try:
        commande = get_object_or_404(Commande, id=commande_id, client=request.user.client_profile)
        
        return JsonResponse({
            'success': True,
            'commande': {
                'id': commande.id,
                'reference': commande.reference,
                'statut': commande.statut,
                'statut_display': commande.get_statut_display(),
                'statut_paiement': commande.statut_paiement,
                'statut_paiement_display': commande.get_statut_paiement_display(),
                'methode_paiement': commande.methode_paiement,
                'methode_paiement_display': commande.get_methode_paiement_display(),
                'total': float(commande.total),
                'date_commande': commande.date_commande.isoformat(),
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Erreur lors de la récupération du statut.'
        }, status=500)

# Webhook amélioré pour PayGate
@login_required
def api_solde_portefeuille(request):
    """API pour récupérer le solde du portefeuille"""
    try:
        portefeuille, created = Portefeuille.objects.get_or_create(user=request.user)
        return JsonResponse({
            'success': True,
            'solde': float(portefeuille.solde)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Erreur lors de la récupération du solde'
        }, status=500)

@login_required
def api_historique_portefeuille(request):
    """API pour récupérer l'historique des transactions"""
    try:
        portefeuille = get_object_or_404(Portefeuille, user=request.user)
        transactions = portefeuille.transactions.all()[:50]  # 50 dernières transactions
        
        transactions_data = []
        for transaction in transactions:
            transactions_data.append({
                'type': transaction.type_transaction,
                'montant': float(transaction.montant),
                'solde_apres': float(transaction.solde_apres),
                'description': transaction.description,
                'date': transaction.date_transaction.strftime('%d/%m/%Y %H:%M')
            })
        
        return JsonResponse({
            'success': True,
            'solde_actuel': float(portefeuille.solde),
            'transactions': transactions_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Erreur lors de la récupération de l\'historique'
        }, status=500)

#########################################################################
########################################################################
###########################################################################
############################################################################

@login_required
def portefeuille(request):
    """Page de gestion du portefeuille"""
    portefeuille, created = Portefeuille.objects.get_or_create(user=request.user)
    transactions = portefeuille.transactions.all()[:20]  # 20 dernières transactions
    
    context = {
        'portefeuille': portefeuille,
        'transactions': transactions,
    }
    
    return render(request, 'clients/portefeuille.html', context)

@login_required
def commandes_multiple_confirmation(request):
    """Page de confirmation pour les commandes multiples"""
    # Récupérer les dernières commandes de l'utilisateur
    commandes = Commande.objects.filter(
        client=request.user.client_profile
    ).order_by('-date_commande')[:5]
    
    context = {
        'commandes': commandes,
    }
    
    return render(request, 'clients/commandes_multiple_confirmation.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def webhook_paygate(request):
    """Webhook pour recevoir les confirmations de paiement de PayGate - VERSION CORRIGÉE"""
    try:
        data = json.loads(request.body)
        print(f"📩 Webhook PayGate reçu: {data}")
        
        # Extraire les données du webhook
        tx_reference = data.get('tx_reference')
        identifier = data.get('identifier')
        amount = data.get('amount')
        status = data.get('status')
        payment_method = data.get('payment_method')
        phone_number = data.get('phone_number')
        
        print(f"🔍 Détails webhook:")
        print(f"   - Identifier: {identifier}")
        print(f"   - TX Reference: {tx_reference}")
        print(f"   - Status: {status}")
        print(f"   - Amount: {amount}")
        
        # Vérifier s'il s'agit d'un dépôt (commence par DEP-)
        if identifier and identifier.startswith('DEP-'):
            print("💰 Traitement d'un dépôt...")
            try:
                # Extraire l'ID du dépôt depuis l'identifier (format: DEP-18-ABC123)
                depot_id = identifier.split('-')[1]
                depot = DepotPortefeuille.objects.get(id=depot_id)
                
                print(f"🔍 Dépôt trouvé: ID {depot.id}, Statut: {depot.statut}")
                
                if status == 0:  # Paiement réussi
                    print("✅ Paiement réçu via webhook - Validation du dépôt...")
                    if depot.valider():
                        print(f"🎉 Dépôt {depot.id} validé via webhook!")
                        return JsonResponse({
                            'status': 'success',
                            'message': 'Dépôt validé avec succès'
                        })
                    else:
                        print(f"❌ Échec validation dépôt {depot.id}")
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Erreur lors de la validation du dépôt'
                        }, status=500)
                else:
                    print(f"❌ Statut non valide dans webhook: {status}")
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Statut de paiement invalide: {status}'
                    }, status=400)
                    
            except DepotPortefeuille.DoesNotExist:
                print(f"❌ Dépôt non trouvé pour identifier: {identifier}")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Dépôt non trouvé'
                }, status=404)
            except Exception as e:
                print(f"💥 Erreur traitement dépôt: {str(e)}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'Erreur interne: {str(e)}'
                }, status=500)
        else:
            # C'est un paiement pour une commande
            try:
                if identifier and identifier.startswith('CMD-'):
                    commande_id = identifier.split('-')[1]
                    commande = Commande.objects.get(id=commande_id)
                else:
                    commande = Commande.objects.get(reference=identifier)
                
                # Mettre à jour le statut de la commande
                commande.paygate_reference = tx_reference
                commande.paygate_status = 'paye'
                commande.statut_paiement = 'paye'
                commande.statut = 'validee'
                commande.paygate_network = payment_method
                commande.paygate_phone = phone_number
                commande.save()
                
                # CALCULER ET DISTRIBUER LES COMMISSIONS
                commande.calculer_commissions()
                
                print(f"Paiement commande confirmé: {commande.reference}")
                print(f"Commissions distribuées pour le commerçant: {commande.commercant.nom_boutique}")
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Paiement enregistré avec succès'
                })
                
            except Commande.DoesNotExist:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Commande non trouvée'
                }, status=404)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Données JSON invalides'
        }, status=400)
    except Exception as e:
        print(f"💥 Erreur webhook PayGate: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Erreur interne: {str(e)}'
        }, status=500)

@login_required
def verifier_statut_depot(request, depot_id):
    """Vérifier manuellement le statut d'un dépôt - VERSION CORRIGÉE"""
    depot = get_object_or_404(DepotPortefeuille, id=depot_id, portefeuille__user=request.user)
    
    print(f"🔍 Vérification dépôt {depot_id}: {depot.numero_transaction}")
    print(f"📊 Statut initial: {depot.statut}")
    
    # Vérifier le statut via l'API PayGate
    if depot.numero_transaction:
        try:
            statut = PayGateGlobal.verifier_statut_paiement(depot.numero_transaction)
            print(f"📊 Réponse PayGate: {statut}")
            
            if statut.get('status') == 0:  # Paiement réussi
                print("✅ Paiement confirmé - Validation en cours...")
                if depot.valider():  # Utiliser la nouvelle méthode corrigée
                    return JsonResponse({
                        'success': True, 
                        'message': 'Dépôt confirmé ! Votre portefeuille a été crédité.',
                        'statut': 'valide',
                        'nouveau_solde': float(depot.portefeuille.solde)
                    })
                else:
                    return JsonResponse({
                        'success': False, 
                        'message': 'Erreur lors du crédit du portefeuille.',
                        'statut': depot.statut,
                        'status_paygate': statut.get('status')
                    })
            else:
                # Si le paiement est en échec chez PayGate mais que le dépôt était marqué valide
                if depot.statut == 'valide' and statut.get('status') != 0:
                    return JsonResponse({
                        'success': True, 
                        'message': f'Dépôt déjà validé (statut PayGate: {statut.get("status")})',
                        'statut': 'valide',
                        'solde': float(depot.portefeuille.solde)
                    })
                else:
                    return JsonResponse({
                        'success': False, 
                        'message': f'Statut PayGate: {statut.get("status")} - {statut.get("message", "Raison inconnue")}',
                        'statut': depot.statut,
                        'status_paygate': statut.get('status')
                    })
                    
        except Exception as e:
            print(f"❌ Erreur vérification: {str(e)}")
            return JsonResponse({
                'success': False, 
                'message': f'Erreur: {str(e)}',
                'statut': 'erreur'
            })
    
    # Si déjà validé
    if depot.statut == 'valide':
        return JsonResponse({
            'success': True, 
            'message': f'Dépôt déjà validé',
            'statut': 'valide',
            'solde': float(depot.portefeuille.solde)
        })
    
    return JsonResponse({
        'success': False, 
        'message': 'Aucune référence de transaction',
        'statut': depot.statut
    })


@login_required
def choix_paiement(request, commande_id):
    """
    Page de choix de méthode de paiement
    """
    commande = get_object_or_404(Commande, id=commande_id, client=request.user.client_profile)
    
    if request.method == 'POST':
        methode_paiement = request.POST.get('methode_paiement')
        network = request.POST.get('network')
        phone_number = request.POST.get('phone_number')
        
        if methode_paiement == 'mobile_money':
            return redirect('clients:paiement_mobile', commande_id=commande_id, network=network)
        
        # Pour les autres méthodes de paiement
        commande.methode_paiement = methode_paiement
        commande.save()
        
        if methode_paiement == 'espece':
            messages.success(request, 'Commande passée avec succès. Paiement à la livraison.')
            return redirect('clients:confirmation_commande', commande_id=commande_id)
    
    context = {
        'commande': commande,
    }
    return render(request, 'clients/choix_paiement.html', context)

@login_required
def paiement_mobile(request, commande_id, network):
    """
    Page de paiement mobile money
    """
    commande = get_object_or_404(Commande, id=commande_id, client=request.user.client_profile)
    
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        
        if not phone_number:
            messages.error(request, 'Veuillez saisir votre numéro de téléphone.')
            return render(request, 'clients/paiement_mobile.html', {
                'commande': commande,
                'network': network
            })
        
        # Nettoyer le numéro de téléphone
        phone_number = phone_number.replace(' ', '').replace('-', '')
        
        # Générer un identifiant unique pour la transaction
        transaction_id = f"CMD-{commande.id}-{uuid.uuid4().hex[:8].upper()}"
        
        # Méthode 1: Paiement direct via API
        resultat = PayGateGlobal.initier_paiement_api(
            phone_number=phone_number,
            amount=str(int(commande.total)),  # Montant sans décimales
            description=f"Paiement commande {commande.reference}",
            identifier=transaction_id,
            network=network.upper()
        )
        
        if resultat.get('status') == 0:
            # Paiement initié avec succès
            commande.paygate_reference = resultat.get('tx_reference')
            commande.paygate_status = 'initie'
            commande.paygate_network = network.upper()
            commande.paygate_phone = phone_number
            commande.methode_paiement = 'mobile_money'
            commande.statut_paiement = 'en_attente'
            commande.save()
            
            messages.success(request, f'Paiement initié. Un message a été envoyé au {phone_number}')
            return redirect('clients:verification_paiement', commande_id=commande_id)
        
        else:
            # Erreur lors de l'initiation du paiement
            error_messages = {
                2: 'Clé API invalide',
                4: 'Paramètres invalides',
                6: 'Transaction déjà existante'
            }
            error_msg = error_messages.get(resultat.get('status'), 'Erreur lors de l\'initiation du paiement')
            messages.error(request, f'Erreur: {error_msg}')
    
    context = {
        'commande': commande,
        'network': network,
        'network_name': 'FLOOZ' if network.upper() == 'FLOOZ' else 'T-Money'
    }
    return render(request, 'clients/paiement_mobile.html', context)

@login_required
def verification_paiement(request, commande_id):
    """
    Page de vérification du statut du paiement
    """
    commande = get_object_or_404(Commande, id=commande_id, client=request.user.client_profile)
    
    # Vérifier le statut du paiement
    if commande.paygate_reference:
        statut = PayGateGlobal.verifier_statut_paiement(commande.paygate_reference)
        
        if statut.get('status') == 0:  # Paiement réussi
            commande.paygate_status = 'paye'
            commande.statut_paiement = 'paye'
            commande.statut = 'validee'
            commande.save()
            messages.success(request, 'Paiement confirmé avec succès!')
            return redirect('clients:confirmation_commande', commande_id=commande_id)
        
        elif statut.get('status') in [2, 4, 6]:  # Échec, expiration ou annulation
            commande.paygate_status = 'echec'
            commande.statut_paiement = 'echec'
            commande.save()
    
    context = {
        'commande': commande,
    }
    return render(request, 'clients/verification_paiement.html', context)

########################################################################
########################################################################
########################################################################
# dépot d'argent dans le portefeuille via PayGate
#################################################################################
########################################################################################
############################################################################
@login_required
def depot_portefeuille(request):
    """Page principale des dépôts"""
    portefeuille, created = Portefeuille.objects.get_or_create(user=request.user)
    depots_recents = portefeuille.depots.all()[:5]
    
    context = {
        'portefeuille': portefeuille,
        'depots_recents': depots_recents,
    }
    return render(request, 'clients/depot_portefeuille.html', context)

@login_required
def depot_mobile_money(request):
    """Dépôt via Mobile Money"""
    portefeuille, created = Portefeuille.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = DepotMobileMoneyForm(request.POST)
        if form.is_valid():
            # Créer le dépôt en attente
            depot = DepotPortefeuille.objects.create(
                portefeuille=portefeuille,
                montant=form.cleaned_data['montant'],
                methode='mobile_money',
                operateur=form.cleaned_data['operateur'],
                numero_telephone=form.cleaned_data['numero_telephone'],
                statut='en_attente'
            )
            
            # Initier le paiement via PayGate
            transaction_id = f"DEP-{depot.id}-{uuid.uuid4().hex[:8].upper()}"
            
            resultat = PayGateGlobal.initier_paiement_api(
                phone_number=form.cleaned_data['numero_telephone'],
                amount=str(int(form.cleaned_data['montant'])),
                description=f"Dépôt portefeuille {request.user.username}",
                identifier=transaction_id,
                network=form.cleaned_data['operateur']
            )
            
            if resultat.get('status') == 0:
                # Paiement initié avec succès
                depot.numero_transaction = resultat.get('tx_reference')
                depot.save()
                
                messages.success(
                    request, 
                    f'Dépôt initié. Un message a été envoyé au {form.cleaned_data["numero_telephone"]}. '
                    f'Votre portefeuille sera crédité après confirmation du paiement.'
                )
                return redirect('clients:verification_depot', depot_id=depot.id)
            else:
                # Erreur lors de l'initiation
                depot.statut = 'echec'
                depot.notes = f"Erreur PayGate: {resultat.get('status')}"
                depot.save()
                
                error_messages = {
                    2: 'Clé API invalide',
                    4: 'Paramètres invalides',
                    6: 'Transaction déjà existante'
                }
                error_msg = error_messages.get(resultat.get('status'), 'Erreur lors de l\'initiation du paiement')
                messages.error(request, f'Erreur: {error_msg}')
    else:
        # Pré-remplir avec le numéro de l'utilisateur si disponible
        initial_data = {}
        if request.user.telephone:
            initial_data['numero_telephone'] = request.user.telephone
        
        form = DepotMobileMoneyForm(initial=initial_data)
    
    context = {
        'form': form,
        'portefeuille': portefeuille,
    }
    return render(request, 'clients/depot_mobile_money.html', context)

@login_required
def depot_paygate(request):
    """Dépôt via PayGate (carte bancaire)"""
    portefeuille, created = Portefeuille.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = DepotPayGateForm(request.POST)
        if form.is_valid():
            # Créer le dépôt en attente
            depot = DepotPortefeuille.objects.create(
                portefeuille=portefeuille,
                montant=form.cleaned_data['montant'],
                methode='paygate',
                statut='en_attente'
            )
            
            # Générer un lien de paiement PayGate
            transaction_id = f"DEP-{depot.id}-{uuid.uuid4().hex[:8].upper()}"
            payment_url = PayGateGlobal.generer_lien_paiement(
                amount=str(int(form.cleaned_data['montant'])),
                description=f"Dépôt portefeuille {request.user.username}",
                identifier=transaction_id,
                redirect_url=request.build_absolute_uri(
                    reverse('clients:verification_depot', args=[depot.id])
                )
            )
            
            depot.numero_transaction = transaction_id
            depot.save()
            
            # Rediriger vers la page de paiement PayGate
            return redirect(payment_url)
    else:
        form = DepotPayGateForm()
    
    context = {
        'form': form,
        'portefeuille': portefeuille,
    }
    return render(request, 'clients/depot_paygate.html', context)

# Dans clients/views.py - Remplacer verification_depot
@login_required
def verification_depot(request, depot_id):
    """Page de vérification du statut d'un dépôt - VERSION CORRIGÉE"""
    depot = get_object_or_404(DepotPortefeuille, id=depot_id, portefeuille__user=request.user)
    
    print(f"🔍 Vérification dépôt {depot_id}")
    print(f"📊 Statut actuel: {depot.statut}")
    print(f"💰 Montant: {depot.montant}")
    print(f"🔖 Référence: {depot.numero_transaction}")
    
    # Vérification automatique si en attente ou échec
    if depot.statut in ['en_attente', 'echec']:
        if depot.numero_transaction:
            try:
                print(f"🔍 Vérification automatique PayGate: {depot.numero_transaction}")
                statut = PayGateGlobal.verifier_statut_paiement(depot.numero_transaction)
                print(f"📊 Réponse PayGate: {statut}")
                
                if statut.get('status') == 0:  # Paiement réussi
                    print("✅ Paiement confirmé - Validation automatique...")
                    if depot.valider():
                        messages.success(request, 'Dépôt confirmé automatiquement ! Votre portefeuille a été crédité.')
                        print(f"💰 Nouveau solde: {depot.portefeuille.solde} FCFA")
                    else:
                        messages.error(request, 'Erreur lors du crédit automatique du portefeuille.')
                else:
                    # Mettre à jour le message sans changer le statut
                    status_messages = {
                        2: 'Paiement en attente de confirmation...',
                        4: 'Paiement expiré',
                        6: 'Paiement annulé'
                    }
                    msg = status_messages.get(statut.get('status'), 'Statut inconnu')
                    messages.info(request, msg)
                    
            except Exception as e:
                print(f"❌ Erreur vérification automatique: {str(e)}")
                messages.error(request, 'Erreur lors de la vérification automatique.')
    
    context = {
        'depot': depot,
    }
    return render(request, 'clients/verification_depot.html', context)

def notifications(request):
    pass

def parametres(request):
    pass
def api_panier_info(request):
    pass

@login_required
def demande_retrait(request):
    """Demande de retrait pour les commerçants"""
    # Vérifier que l'utilisateur est un commerçant
    if not hasattr(request.user, 'commercant_profile'):
        messages.error(request, 'Cette fonctionnalité est réservée aux commerçants.')
        return redirect('clients:accueil')
    
    portefeuille, created = Portefeuille.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = DemandeRetraitForm(request.POST, portefeuille=portefeuille)
        if form.is_valid():
            retrait = form.save(commit=False)
            retrait.portefeuille = portefeuille
            retrait.calculer_frais()  # Calculer les frais de 2%
            retrait.save()
            
            messages.success(
                request, 
                f'Demande de retrait de {retrait.montant} FCFA envoyée. '
                f'Frais: {retrait.frais_retrait} FCFA, Montant net: {retrait.montant_net} FCFA. '
                f'Votre demande sera traitée sous 24-48h.'
            )
            return redirect('clients:historique_retraits')
    else:
        form = DemandeRetraitForm(portefeuille=portefeuille)
    
    context = {
        'form': form,
        'portefeuille': portefeuille,
    }
    return render(request, 'clients/demande_retrait.html', context)

@login_required
def historique_retraits(request):
    """Historique des retraits"""
    portefeuille, created = Portefeuille.objects.get_or_create(user=request.user)
    retraits = portefeuille.retraits.all().order_by('-date_demande')
    
    context = {
        'portefeuille': portefeuille,
        'retraits': retraits,
    }
    return render(request, 'clients/historique_retraits.html', context)


@login_required
def api_historique_depots(request):
    """API pour récupérer l'historique des dépôts"""
    try:
        portefeuille = get_object_or_404(Portefeuille, user=request.user)
        depots = portefeuille.depots.all().order_by('-date_depot')[:50]
        
        depots_data = []
        for depot in depots:
            depots_data.append({
                'id': depot.id,
                'montant': float(depot.montant),
                'methode': depot.get_methode_display(),
                'statut': depot.get_statut_display(),
                'date': depot.date_depot.strftime('%d/%m/%Y %H:%M'),
                'numero_transaction': depot.numero_transaction
            })
        
        return JsonResponse({
            'success': True,
            'depots': depots_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Erreur lors de la récupération de l\'historique'
        }, status=500)

#########################################################################
# les importations nécessaires pour la vue portefeuille
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum
#########################################################################
@login_required
def portefeuille(request):
    """Page de gestion du portefeuille"""
    portefeuille, created = Portefeuille.objects.get_or_create(user=request.user)
    
    # Transactions du portefeuille (paginées)
    transactions_page = request.GET.get('page_transactions', 1)
    transactions = portefeuille.transactions.all().order_by('-date_transaction')
    paginator_transactions = Paginator(transactions, 10)
    
    try:
        transactions = paginator_transactions.page(transactions_page)
    except PageNotAnInteger:
        transactions = paginator_transactions.page(1)
    except EmptyPage:
        transactions = paginator_transactions.page(paginator_transactions.num_pages)
    
    # Dépôts récents
    depots = portefeuille.depots.all().order_by('-date_depot')[:10]
    
    # Retraits (pour commerçants)
    retraits = []
    if hasattr(request.user, 'commercant_profile'):
        retraits = portefeuille.retraits.all().order_by('-date_demande')[:10]
    
    # Statistiques
    total_depots = portefeuille.depots.filter(statut='valide').aggregate(
        total=Sum('montant')
    )['total'] or 0
    
    # Calcul des achats totaux (pour clients)
    total_achats = 0
    commandes_count = 0
    if hasattr(request.user, 'client_profile'):
        total_achats = Commande.objects.filter(
            client=request.user.client_profile,
            statut_paiement='paye'
        ).aggregate(total=Sum('total'))['total'] or 0
        commandes_count = Commande.objects.filter(
            client=request.user.client_profile
        ).count()
    
    # Calcul des ventes totales (pour commerçants)
    total_ventes = 0
    total_retraits = 0
    if hasattr(request.user, 'commercant_profile'):
        total_ventes = Commission.objects.filter(
            commande__commercant=request.user.commercant_profile,
            est_transfere=True
        ).aggregate(total=Sum('montant_commercant'))['total'] or 0
        
        total_retraits = portefeuille.retraits.filter(
            statut='traite'
        ).aggregate(total=Sum('montant'))['total'] or 0
    
    # Statistiques du mois
    from datetime import datetime, timedelta
    debut_mois = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    depots_mois = portefeuille.depots.filter(
        statut='valide',
        date_depot__gte=debut_mois
    ).aggregate(total=Sum('montant'))['total'] or 0
    
    retraits_mois = portefeuille.retraits.filter(
        statut='traite',
        date_demande__gte=debut_mois
    ).aggregate(total=Sum('montant'))['total'] or 0
    
    achats_mois = 0
    if hasattr(request.user, 'client_profile'):
        achats_mois = Commande.objects.filter(
            client=request.user.client_profile,
            statut_paiement='paye',
            date_commande__gte=debut_mois
        ).aggregate(total=Sum('total'))['total'] or 0
    
    # Pourcentages (simplifiés)
    pourcentage_depots_mois = min(int((depots_mois / (total_depots or 1)) * 100), 100)
    pourcentage_retraits_mois = min(int((retraits_mois / (total_retraits or 1)) * 100), 100)
    pourcentage_achats_mois = min(int((achats_mois / (total_achats or 1)) * 100), 100)
    
    context = {
        'portefeuille': portefeuille,
        'transactions': transactions,
        'depots': depots,
        'retraits': retraits,
        'total_depots': total_depots,
        'total_achats': total_achats,
        'total_ventes': total_ventes,
        'total_retraits': total_retraits,
        'commandes_count': commandes_count,
        'transactions_count': portefeuille.transactions.count(),
        'depots_mois': depots_mois,
        'retraits_mois': retraits_mois,
        'achats_mois': achats_mois,
        'pourcentage_depots_mois': pourcentage_depots_mois,
        'pourcentage_retraits_mois': pourcentage_retraits_mois,
        'pourcentage_achats_mois': pourcentage_achats_mois,
    }
    
    return render(request, 'clients/portefeuille.html', context)

@login_required
def api_verification_paiement(request, commande_id):
    """
    API pour vérifier le statut du paiement - VERSION CORRIGÉE
    """
    try:
        commande = get_object_or_404(Commande, id=commande_id, client=request.user.client_profile)
        
        print(f"🔍 Vérification paiement commande {commande_id}")
        print(f"📊 Statut actuel: {commande.statut_paiement}")
        print(f"💰 Méthode paiement: {commande.methode_paiement}")
        print(f"🔖 Référence PayGate: {commande.paygate_reference}")
        
        # Vérifier le statut via PayGate si nécessaire
        if commande.paygate_reference and commande.statut_paiement == 'en_attente':
            print(f"🔍 Vérification PayGate: {commande.paygate_reference}")
            try:
                statut = PayGateGlobal.verifier_statut_paiement(commande.paygate_reference)
                print(f"📊 Réponse PayGate: {statut}")
                
                if statut.get('status') == 0:  # Paiement réussi
                    commande.paygate_status = 'paye'
                    commande.statut_paiement = 'paye'
                    commande.statut = 'validee'
                    commande.save()
                    
                    # CALCULER ET DISTRIBUER LES COMMISSIONS
                    commission_plateforme = commande.total * Decimal('0.10')
                    montant_commercant = commande.total - commission_plateforme
                    
                    commission = Commission.objects.create(
                        commande=commande,
                        montant_commande=commande.total,
                        commission_plateforme=commission_plateforme,
                        montant_commercant=montant_commercant,
                        taux_commission=10.00,
                        est_transfere=True,
                        date_transfert=timezone.now()
                    )
                    
                    # Créditer le commerçant
                    portefeuille_commercant, created = Portefeuille.objects.get_or_create(
                        user=commande.commercant.user
                    )
                    portefeuille_commercant.crediter(
                        montant_commercant,
                        f"Vente commande {commande.reference}"
                    )
                    
                    print("✅ Paiement confirmé via PayGate et commerçant crédité")
                    
                    return JsonResponse({
                        'paid': True,
                        'failed': False,
                        'message': 'Paiement confirmé avec succès!',
                        'statut_paiement': commande.statut_paiement,
                        'statut_commande': commande.statut
                    })
                    
                elif statut.get('status') in [2, 4, 6]:  # Échec
                    commande.paygate_status = 'echec'
                    commande.statut_paiement = 'echec'
                    commande.save()
                    print("❌ Paiement échoué via PayGate")
                    
                    return JsonResponse({
                        'paid': False,
                        'failed': True,
                        'message': 'Paiement échoué',
                        'statut_paiement': commande.statut_paiement,
                        'statut_commande': commande.statut
                    })
                    
            except Exception as e:
                print(f"❌ Erreur vérification PayGate: {str(e)}")
                # Continuer avec le statut actuel en cas d'erreur API
        
        # Retourner le statut actuel de la commande
        response_data = {
            'paid': commande.statut_paiement == 'paye',
            'failed': commande.statut_paiement == 'echec',
            'statut_paiement': commande.statut_paiement,
            'statut_commande': commande.statut,
            'message': f'Statut: {commande.get_statut_paiement_display()}'
        }
        
        print(f"📤 Réponse API: {response_data}")
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"❌ Erreur API vérification paiement: {str(e)}")
        return JsonResponse({
            'paid': False,
            'failed': False,
            'error': str(e),
            'message': 'Erreur lors de la vérification du paiement'
        }, status=500)


# # EXÉCUTEZ CE CODE MAINTENANT dans le shell Django
# from clients.models import DepotPortefeuille

# # Trouvez le dépôt
# depot = DepotPortefeuille.objects.get(numero_transaction="5192288")
# print(f"📊 Dépôt trouvé: ID {depot.id}, Statut: {depot.statut}")

# # Validez-le manuellement
# if depot.valider():
#     print("🎉 Dépôt validé avec succès !")
#     print(f"💰 Nouveau solde: {depot.portefeuille.solde} FCFA")
# else:
#     print("❌ Échec de la validation")
#     print(f"📝 Notes: {depot.notes}")