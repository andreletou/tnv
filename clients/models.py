from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
# postgis
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.utils import timezone
from decimal import Decimal
from django.db import models
from .paygate import PayGateGlobal
from django.contrib.auth import get_user_model

User = get_user_model()

class Client(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='client_profile'
    )
    
    class Meta:
        verbose_name = "Profil Client"
        verbose_name_plural = "Profils Clients"

    def __str__(self):
        return f"Client: {self.user.username}"

    # Propriétés pour accéder aux données utilisateur
    @property
    def username(self):
        return self.user.username
    
    @property
    def email(self):
        return self.user.email
    
    @property
    def first_name(self):
        return self.user.first_name
    
    @property
    def last_name(self):
        return self.user.last_name
    
    @property
    def telephone(self):
        return self.user.telephone
    
    @property
    def adresse(self):
        return self.user.adresse
    
    @property
    def photo_profil(self):
        return self.user.photo_profil

class Panier(models.Model):
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='panier')
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Date de modification")
    
    class Meta:
        verbose_name = "Panier"
        verbose_name_plural = "Paniers"
    
    def __str__(self):
        return f"Panier de {self.client.username}"
    
    @property
    def total(self):
        """Calcule le total du panier"""
        return sum(item.sous_total for item in self.items.all())
    
    @property
    def nombre_articles(self):
        """Retourne le nombre total d'articles dans le panier"""
        return sum(item.quantite for item in self.items.all())

class ArticlePanier(models.Model):
    panier = models.ForeignKey(Panier, on_delete=models.CASCADE, related_name='items')
    produit = models.ForeignKey('commercants.Produit', on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(default=1, verbose_name="Quantité")
    date_ajout = models.DateTimeField(auto_now_add=True, verbose_name="Date d'ajout")
    
    class Meta:
        verbose_name = "Article du panier"
        verbose_name_plural = "Articles du panier"
        unique_together = ['panier', 'produit']
    
    def __str__(self):
        return f"{self.quantite} x {self.produit.nom}"
    
    @property
    def sous_total(self):
        """Calcule le sous-total pour cet article"""
        return self.quantite * self.produit.prix_effectif

class Commande(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente de validation'),
        ('validee', 'Validée'),
        ('en_preparation', 'En préparation'),
        ('prete', 'Prête pour livraison'),
        ('en_livraison', 'En cours de livraison'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='commandes')
    commercant = models.ForeignKey('commercants.Commercant', on_delete=models.CASCADE, related_name='commandes_recues')
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    adresse_livraison = models.TextField()
    latitude_livraison = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude_livraison = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    instructions_livraison = models.TextField(blank=True)

    methode_paiement = models.CharField(
        max_length=20,
        choices=[
            ('paygate', 'PayGate'),
            ('espece', 'Espèce à la livraison'),
            ('mobile_money', 'Mobile Money'),
            ('portefeuille', 'Portefeuille'),
        ],
        default='espece'
    )

    statut_paiement = models.CharField(
        max_length=20,
        choices=[
            ('en_attente', 'En attente'),
            ('paye', 'Payé'),
            ('echec', 'Échec'),
            ('rembourse', 'Remboursé'),
        ],
        default='en_attente'
    )

    date_commande = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    reference = models.CharField(max_length=50, unique=True)

    point_livraison = gis_models.PointField(
        geography=True,
        null=True,
        blank=True,
        srid=4326
    )

    paygate_reference = models.CharField(max_length=100, blank=True, null=True, verbose_name="Référence PayGate")
    paygate_status = models.CharField(
        max_length=20,
        choices=[
            ('initie', 'Paiement initié'),
            ('en_attente', 'En attente de paiement'),
            ('paye', 'Paiement confirmé'),
            ('echec', 'Échec du paiement'),
            ('expire', 'Paiement expiré'),
            ('annule', 'Paiement annulé'),
        ],
        default='en_attente',
        verbose_name="Statut PayGate"
    )
    paygate_network = models.CharField(
        max_length=10,
        choices=[('FLOOZ', 'FLOOZ'), ('TMONEY', 'T-Money')],
        blank=True, null=True,
        verbose_name="Réseau mobile"
    )
    paygate_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Numéro de paiement")

    class Meta:
        ordering = ['-date_commande']

    def __str__(self):
        return f"Commande {self.reference} - {self.client.username}"

    # ----------------------------------------------------------------------
    # SAVE LOGIC (corrigé et sécurisé)
    # ----------------------------------------------------------------------
    def save(self, *args, **kwargs):
        # Générer une référence si pas encore définie
        if not self.reference:
            import uuid
            self.reference = f"CMD-{uuid.uuid4().hex[:8].upper()}"

        # Si point_livraison est déjà défini (depuis l'admin), ne pas le recalculer
        if self.point_livraison and hasattr(self.point_livraison, 'x'):
            # Le point est déjà défini, probablement depuis l'admin
            print(f"Point déjà défini: {self.point_livraison}")
        else:
            # Traiter le point_livraison si c'est une string GeoJSON
            self._process_point_livraison()

            # Définir correctement le point de livraison
            self._update_point_livraison()

        # Appeler le save() parent
        super().save(*args, **kwargs)

    def _process_point_livraison(self):
        """Convertit le GeoJSON string en objet Point si nécessaire"""
        if isinstance(self.point_livraison, str) and self.point_livraison.strip():
            try:
                import json
                geo_data = json.loads(self.point_livraison)
                if geo_data.get('type') == 'Point' and 'coordinates' in geo_data:
                    coords = geo_data['coordinates']
                    if len(coords) >= 2:
                        # GeoJSON: [longitude, latitude]
                        # Point: (x, y) = (longitude, latitude)
                        self.point_livraison = Point(coords[0], coords[1], srid=4326)
                        print(f"Point converti depuis GeoJSON: {self.point_livraison}")
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
                print(f"Erreur conversion GeoJSON: {e}")
                # En cas d'erreur, on laisse point_livraison vide
                self.point_livraison = None

    def _update_point_livraison(self):
        """
        Définit point_livraison dans cet ordre :
        1. Si point_livraison est déjà un objet Point → NE PAS toucher
        2. Sinon, si lat/lng fournis → créer un Point
        3. Sinon, fallback sur les coordonnées du client
        """

        # 1. Si point_livraison est déjà un objet Point valide, on ne change rien
        if self.point_livraison and hasattr(self.point_livraison, 'x'):
            return

        # 2. Lat/lng fournies → créer un point
        if self._coordonnees_valides(self.latitude_livraison, self.longitude_livraison):
            try:
                lat = float(self.latitude_livraison)
                lng = float(self.longitude_livraison)
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    self.point_livraison = Point(lng, lat, srid=4326)
                    print(f"Point créé depuis lat/lng: {self.point_livraison}")
                return
            except (ValueError, TypeError) as e:
                print(f"Erreur création Point depuis lat/lng: {e}")
                pass

        # 3. Fallback sur client
        self._set_point_from_client()

    def _set_point_from_client(self):
        """Définit point_livraison depuis les coordonnées du client"""
        try:
            user = self.client.user
            
            if self._coordonnees_valides(user.latitude, user.longitude):
                lat = float(user.latitude)
                lng = float(user.longitude)
                self.point_livraison = Point(lng, lat, srid=4326)

                # Mettre à jour les champs de livraison si absents
                if not self.latitude_livraison:
                    self.latitude_livraison = lat
                if not self.longitude_livraison:
                    self.longitude_livraison = lng

        except Exception:
            pass

    # ----------------------------------------------------------------------
    # VALIDATIONS
    # ----------------------------------------------------------------------
    def _coordonnees_valides(self, lat, lng):
        """Vérifie que lat/lng sont valides"""
        if lat is None or lng is None:
            return False

        try:
            lat = float(lat)
            lng = float(lng)
        except (TypeError, ValueError):
            return False

        return -90 <= lat <= 90 and -180 <= lng <= 180

    # ----------------------------------------------------------------------
    # PROPRIÉTÉS UTILES
    # ----------------------------------------------------------------------
    @property
    def a_coordonnees_livraison(self):
        return self.point_livraison is not None

    @property
    def source_coordonnees(self):
        """Indique si les coordonnées viennent du client ou du formulaire"""
        if not self.point_livraison:
            return "Aucune"

        try:
            if (
                self.client.user.latitude and self.client.user.longitude
                and self.latitude_livraison and self.longitude_livraison
                and abs(float(self.latitude_livraison) - float(self.client.user.latitude)) < 0.0001
                and abs(float(self.longitude_livraison) - float(self.client.user.longitude)) < 0.0001
            ):
                return "Client"
        except:
            pass

        return "Livraison"
    
    def calculer_commissions(self):
        """Calculer et distribuer les commissions pour cette commande - VERSION CORRIGÉE"""
        from decimal import Decimal
        
        print(f"💰 Calcul des commissions pour la commande {self.reference}")
        print(f"📊 Total commande: {self.total} FCFA")
        
        # Vérifier que la commande est payée
        if self.statut_paiement != 'paye':
            print(f"❌ Commande non payée - Statut: {self.statut_paiement}")
            return None
        
        # Taux de commission (10% pour la plateforme, 90% pour le commerçant)
        taux_commission_plateforme = Decimal('0.10')
        
        # Calculer la commission
        commission_plateforme = self.total * taux_commission_plateforme
        montant_commercant = self.total - commission_plateforme
        
        print(f"📈 Commission plateforme: {commission_plateforme} FCFA")
        print(f"📈 Montant commerçant: {montant_commercant} FCFA")
        
        # Créer ou mettre à jour l'enregistrement de commission
        commission, created = Commission.objects.get_or_create(
            commande=self,
            defaults={
                'montant_commande': self.total,
                'commission_plateforme': commission_plateforme,
                'montant_commercant': montant_commercant,
                'taux_commission': 10.00,
                'est_transfere': False,  # Pas encore transféré
                'date_transfert': None
            }
        )
        
        if not created:
            # Mettre à jour la commission existante
            commission.montant_commande = self.total
            commission.commission_plateforme = commission_plateforme
            commission.montant_commercant = montant_commercant
            commission.save()
        
        # Créditer le commerçant
        try:
            portefeuille_commercant, created = Portefeuille.objects.get_or_create(
                user=self.commercant.user
            )
            
            print(f"💳 Portefeuille commerçant avant: {portefeuille_commercant.solde} FCFA")
            
            # Créditer le portefeuille
            portefeuille_commercant.crediter(
                montant_commercant,
                f"Vente commande {self.reference} - Commission 90%"
            )
            
            # Marquer la commission comme transférée
            commission.est_transfere = True
            commission.date_transfert = timezone.now()
            commission.save()
            
            print(f"💳 Portefeuille commerçant après: {portefeuille_commercant.solde} FCFA")
            print(f"✅ Commerçant crédité: {montant_commercant} FCFA pour la commande {self.reference}")
            
            return commission
            
        except Exception as e:
            print(f"❌ Erreur crédit commerçant: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

class ArticleCommande(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='articles')
    produit = models.ForeignKey('commercants.Produit', on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(verbose_name="Quantité")
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix unitaire (FCFA)")
    
    class Meta:
        verbose_name = "Article de commande"
        verbose_name_plural = "Articles de commande"
    
    def __str__(self):
        return f"{self.quantite} x {self.produit.nom} - {self.commande.reference}"
    
    @property
    def sous_total(self):
        """Calcule le sous-total pour cet article"""
        return self.quantite * self.prix_unitaire

class Favori(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='favoris')
    produit = models.ForeignKey('commercants.Produit', on_delete=models.CASCADE, related_name='clients_favoris')
    date_ajout = models.DateTimeField(auto_now_add=True, verbose_name="Date d'ajout")
    
    class Meta:
        verbose_name = "Favori"
        verbose_name_plural = "Favoris"
        unique_together = ['client', 'produit']
    
    def __str__(self):
        return f"{self.client.username} - {self.produit.nom}"

class Avis(models.Model):
    NOTE_CHOICES = [
        (1, '1 étoile'),
        (2, '2 étoiles'),
        (3, '3 étoiles'),
        (4, '4 étoiles'),
        (5, '5 étoiles'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='avis')
    produit = models.ForeignKey('commercants.Produit', on_delete=models.CASCADE, related_name='avis')
    note = models.IntegerField(choices=NOTE_CHOICES, verbose_name="Note")
    commentaire = models.TextField(verbose_name="Commentaire")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    est_approuve = models.BooleanField(default=True, verbose_name="Avis approuvé")
    
    class Meta:
        verbose_name = "Avis"
        verbose_name_plural = "Avis"
        unique_together = ['client', 'produit']
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"Avis de {self.client.username} sur {self.produit.nom} - {self.note}/5"

###############################################################################
################################################################################
#################################################################################

class Portefeuille(models.Model):
    """Portefeuille virtuel pour les clients et commerçants"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='portefeuille'
    )
    solde = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Solde disponible (FCFA)"
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Portefeuille"
        verbose_name_plural = "Portefeuilles"
    
    def __str__(self):
        return f"Portefeuille {self.user.username} - {self.solde} FCFA"
    
    def crediter(self, montant, description=""):
        """Créditer le portefeuille"""
        self.solde += montant
        self.save()
        
        # Créer une transaction
        TransactionPortefeuille.objects.create(
            portefeuille=self,
            type_transaction='credit',
            montant=montant,
            solde_apres=self.solde,
            description=description
        )
    
    def debiter(self, montant, description=""):
        """Débiter le portefeuille si le solde est suffisant"""
        if self.solde >= montant:
            self.solde -= montant
            self.save()
            
            # Créer une transaction
            TransactionPortefeuille.objects.create(
                portefeuille=self,
                type_transaction='debit',
                montant=montant,
                solde_apres=self.solde,
                description=description
            )
            return True
        return False

class TransactionPortefeuille(models.Model):
    """Historique des transactions du portefeuille"""
    TYPE_TRANSACTION = [
        ('credit', 'Crédit'),
        ('debit', 'Débit'),
    ]
    
    portefeuille = models.ForeignKey(
        Portefeuille, 
        on_delete=models.CASCADE, 
        related_name='transactions'
    )
    type_transaction = models.CharField(max_length=10, choices=TYPE_TRANSACTION)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    solde_apres = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    date_transaction = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Transaction Portefeuille"
        verbose_name_plural = "Transactions Portefeuille"
        ordering = ['-date_transaction']
    
    def __str__(self):
        return f"{self.type_transaction} - {self.montant} FCFA - {self.portefeuille.user.username}"

class Commission(models.Model):
    """Commission sur les ventes"""
    commande = models.OneToOneField(
        Commande, 
        on_delete=models.CASCADE, 
        related_name='commission'
    )
    montant_commande = models.DecimalField(max_digits=10, decimal_places=2)
    commission_plateforme = models.DecimalField(max_digits=10, decimal_places=2)
    montant_commercant = models.DecimalField(max_digits=10, decimal_places=2)
    taux_commission = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    date_calcul = models.DateTimeField(auto_now_add=True)
    est_transfere = models.BooleanField(default=False)
    date_transfert = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Commission"
        verbose_name_plural = "Commissions"
    
    def __str__(self):
        return f"Commission {self.commande.reference} - {self.commission_plateforme} FCFA"

class DepotPortefeuille(models.Model):
    """Modèle pour gérer les dépôts sur les portefeuilles"""
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('valide', 'Validé'),
        ('echec', 'Échec'),
        ('annule', 'Annulé'),
    ]
    
    METHODE_CHOICES = [
        ('mobile_money', 'Mobile Money'),
        ('paygate', 'PayGate (Carte)'),
        ('virement', 'Virement Bancaire'),
        ('espece', 'Dépôt en Espèces'),
    ]
    
    portefeuille = models.ForeignKey(
        Portefeuille, 
        on_delete=models.CASCADE, 
        related_name='depots'
    )
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    methode = models.CharField(max_length=20, choices=METHODE_CHOICES)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    
    # Informations spécifiques selon la méthode
    numero_transaction = models.CharField(max_length=100, blank=True, null=True)
    operateur = models.CharField(max_length=20, blank=True, null=True)  # FLOOZ, TMONEY, etc.
    numero_telephone = models.CharField(max_length=20, blank=True, null=True)
    
    # Suivi
    date_depot = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Dépôt Portefeuille"
        verbose_name_plural = "Dépôts Portefeuille"
        ordering = ['-date_depot']
    
    def __str__(self):
        return f"Dépôt {self.montant} FCFA - {self.portefeuille.user.username} - {self.get_statut_display()}"
    
    # Dans clients/models.py - Remplacer la méthode valider de DepotPortefeuille
    def valider(self):
        """Valider le dépôt et créditer le portefeuille - VERSION CORRIGÉE AVEC RÉCUPÉRATION"""
        print(f"🔄 Validation du dépôt {self.id}")
        print(f"📊 Statut actuel: {self.statut}")
        print(f"💰 Montant: {self.montant}")
        print(f"🔖 Référence: {self.numero_transaction}")
        
        # Vérifier si le dépôt peut être validé (en attente OU échec mais paiement confirmé)
        if self.statut in ['en_attente', 'echec']:
            try:
                # Vérifier le statut via PayGate
                print(f"🔍 Vérification PayGate pour: {self.numero_transaction}")
                statut = PayGateGlobal.verifier_statut_paiement(self.numero_transaction)
                print(f"📊 Statut PayGate: {statut}")
                
                if statut.get('status') == 0:  # Paiement confirmé
                    print("✅ Paiement confirmé - Crédit du portefeuille...")
                    
                    # Vérifier si le portefeuille n'a pas déjà été crédité
                    if self.statut != 'valide':
                        # CRÉDITER LE PORTEFEUILLE
                        self.portefeuille.crediter(
                            self.montant,
                            f"Dépôt {self.get_methode_display()} - Ref: {self.numero_transaction}"
                        )
                    
                    # Mettre à jour le statut
                    self.statut = 'valide'
                    self.date_validation = timezone.now()
                    self.notes = f"Validé - {statut.get('message', 'Paiement confirmé')}"
                    self.save()
                    
                    print(f"✅ Dépôt {self.id} validé avec succès!")
                    print(f"💰 Nouveau solde: {self.portefeuille.solde} FCFA")
                    return True
                    
                else:
                    error_messages = {
                        2: 'En attente',
                        4: 'Paiement expiré', 
                        6: 'Paiement annulé'
                    }
                    error_msg = error_messages.get(statut.get('status'), f'Statut {statut.get("status")}')
                    print(f"❌ Paiement non confirmé: {error_msg}")
                    
                    # Ne marquer comme échec que si c'était en attente
                    if self.statut == 'en_attente' and statut.get('status') in [4, 6]:
                        self.statut = 'echec'
                        self.notes = f"Échec PayGate: {error_msg}"
                        self.save()
                    
                    return False
                    
            except Exception as e:
                print(f"💥 Erreur lors de la validation: {str(e)}")
                import traceback
                traceback.print_exc()
                
                if self.statut == 'en_attente':
                    self.statut = 'echec'
                    self.notes = f"Erreur validation: {str(e)}"
                    self.save()
                return False
        else:
            print(f"ℹ️ Dépôt {self.id} déjà {self.statut}")
            return self.statut == 'valide'
    
    def annuler(self):
        """Annuler le dépôt"""
        if self.statut == 'en_attente':
            self.statut = 'annule'
            self.save()
            return True
        return False

class RetraitCommercant(models.Model):
    """Modèle pour gérer les retraits des commerçants"""
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('valide', 'Validé'),
        ('echec', 'Échec'),
        ('traite', 'Traité'),
    ]
    
    METHODE_CHOICES = [
        ('mobile_money', 'Mobile Money'),
        ('virement', 'Virement Bancaire'),
        ('espece', 'Retrait en Espèces'),
    ]
    OPERATEUR_CHOICES = [
        ('FLOOZ', 'FLOOZ'),
        ('TMONEY', 'T-Money'),
    ]
    
    portefeuille = models.ForeignKey(
        Portefeuille, 
        on_delete=models.CASCADE, 
        related_name='retraits'
    )
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    methode = models.CharField(max_length=20, choices=METHODE_CHOICES)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    
    # Informations de retrait
    numero_transaction = models.CharField(max_length=100, blank=True, null=True) 
    numero_compte = models.CharField(max_length=100, blank=True, null=True)
    operateur = models.CharField(max_length=20, choices=OPERATEUR_CHOICES, blank=True, null=True)
    nom_beneficiaire = models.CharField(max_length=100, blank=True, null=True)
    
    # Frais de retrait (2%)
    frais_retrait = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    montant_net = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Suivi
    date_demande = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    notes_admin = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Retrait Commerçant"
        verbose_name_plural = "Retraits Commerçants"
        ordering = ['-date_demande']
    
    def __str__(self):
        return f"Retrait {self.montant} FCFA - {self.portefeuille.user.username}"
    
    def calculer_frais(self):
        """Calculer les frais de retrait (2%)"""
        self.frais_retrait = self.montant * Decimal('0.02')
        self.montant_net = self.montant - self.frais_retrait
    
    def traiter(self):
        """Traiter le retrait - VERSION COMPLÈTEMENT CORRIGÉE"""
        print(f"🔄 Traitement du retrait {self.id}, statut actuel: {self.statut}")
        
        if self.statut == 'en_attente':
            try:
                # VÉRIFICATION PAYGATE OBLIGATOIRE AVANT TRAITEMENT
                if self.numero_transaction:
                    print(f"🔍 Vérification PayGate pour le retrait: {self.numero_transaction}")
                    statut_paygate = PayGateGlobal.verifier_statut_paiement(self.numero_transaction)
                    
                    print(f"📊 Statut PayGate: {statut_paygate}")
                    
                    # Vérifier que le paiement est confirmé (statut 0)
                    if statut_paygate.get('status') != 0:
                        self.statut = 'echec'
                        self.notes_admin = f"Paiement non confirmé par PayGate. Statut: {statut_paygate.get('status')} - {statut_paygate.get('message', 'Raison inconnue')}"
                        self.save()
                        print(f"❌ Retrait {self.id} échoué - Paiement non confirmé")
                        return False
                
                # CALCUL DES FRAIS (2%)
                frais = self.montant * Decimal('0.02')
                total_a_debiter = self.montant + frais
                
                print(f"💰 Calcul frais: Montant={self.montant}, Frais={frais}, Total={total_a_debiter}")
                print(f"💳 Solde actuel portefeuille: {self.portefeuille.solde} FCFA")
                
                # VÉRIFICATION SOLDE SUFFISANT
                if self.portefeuille.solde < total_a_debiter:
                    self.statut = 'echec'
                    self.notes_admin = f"Solde insuffisant. Solde disponible: {self.portefeuille.solde} FCFA, Total requis: {total_a_debiter} FCFA"
                    self.save()
                    print(f"❌ Solde insuffisant pour le retrait {self.id}")
                    return False
                
                # DÉBIT DU PORTEFEUILLE
                if self.portefeuille.debiter(
                    total_a_debiter,
                    f"Retrait {self.get_methode_display()} - Montant: {self.montant} FCFA, Frais: {frais} FCFA"
                ):
                    # MISE À JOUR DU STATUT
                    self.statut = 'traite'
                    self.frais_retrait = frais
                    self.montant_net = self.montant - frais
                    self.date_traitement = timezone.now()
                    self.save()
                    
                    print(f"✅ Retrait {self.id} traité avec succès!")
                    print(f"📊 Détails: Montant brut={self.montant}, Frais={self.frais_retrait}, Net={self.montant_net}")
                    print(f"💳 Nouveau solde: {self.portefeuille.solde} FCFA")
                    return True
                else:
                    print(f"❌ Échec du débit du portefeuille pour le retrait {self.id}")
                    return False
                    
            except Exception as e:
                print(f"💥 Erreur lors du traitement du retrait {self.id}: {str(e)}")
                import traceback
                traceback.print_exc()
                
                self.statut = 'echec'
                self.notes_admin = f"Erreur traitement: {str(e)}"
                self.save()
                return False
        else:
            print(f"ℹ️ Retrait {self.id} déjà traité - Statut: {self.statut}")
            return False

    # AJOUTER une méthode pour initier le paiement PayGate pour les retraits
    def initier_paiement_retrait(self, phone_number, operateur):
        """Initier le paiement PayGate pour un retrait"""
        from .paygate import PayGateGlobal
        import uuid
        
        try:
            # Générer un identifiant unique pour la transaction
            identifier = f"RET-{self.id}-{uuid.uuid4().hex[:8].upper()}"
            
            print(f"🔄 Initiation paiement retrait {self.id}")
            print(f"📱 Détails: Téléphone={phone_number}, Opérateur={operateur}, Montant={self.montant}")
            
            # Appeler PayGate
            resultat = PayGateGlobal.initier_paiement_api(
                phone_number=phone_number,
                amount=str(int(self.montant)),
                description=f"Retrait commerçant {self.portefeuille.user.commercant_profile.nom_boutique}",
                identifier=identifier,
                network=operateur.upper()
            )
            
            print(f"📥 Réponse PayGate: {resultat}")
            
            if resultat.get('status') == 0:
                # Succès - sauvegarder la référence
                self.numero_transaction = resultat.get('tx_reference')
                self.save()
                print(f"✅ Paiement initié avec succès. Référence: {self.numero_transaction}")
                return True
            else:
                # Échec
                error_messages = {
                    2: 'Clé API invalide',
                    4: 'Paramètres invalides',
                    6: 'Transaction déjà existante'
                }
                error_msg = error_messages.get(resultat.get('status'), 'Erreur inconnue')
                self.notes_admin = f"Erreur PayGate: {error_msg}"
                self.statut = 'echec'
                self.save()
                print(f"❌ Échec initiation paiement: {error_msg}")
                return False
                
        except Exception as e:
            print(f"💥 Erreur lors de l'initiation du paiement: {str(e)}")
            self.notes_admin = f"Erreur initiation: {str(e)}"
            self.statut = 'echec'
            self.save()
            return False
    
        
    def get_statut_badge_class(self):
        """Retourne la classe CSS pour le badge de statut"""
        classes = {
            'en_attente': 'statut-en_attente',
            'traite': 'statut-traite', 
            'echec': 'statut-echec',
            'valide': 'statut-traite',
            'annule': 'statut-echec'
        }
        return classes.get(self.statut, 'statut-en_attente')

    def get_icon_statut(self):
        """Retourne l'icône correspondant au statut"""
        icons = {
            'en_attente': '⏳',
            'traite': '✅',
            'echec': '❌',
            'valide': '✅',
            'annule': '🚫'
        }
        return icons.get(self.statut, '⏳')

    def get_details_display(self):
        """Retourne les détails formatés pour l'affichage"""
        return {
            'montant': f"{self.montant:.0f} FCFA",
            'frais': f"{self.frais_retrait:.0f} FCFA",
            'net': f"{self.montant_net:.0f} FCFA",
            'methode': self.get_methode_display(),
            'operateur': self.get_operateur_display() if self.operateur else 'N/A',
            'date_demande': self.date_demande.strftime("%d/%m/%Y à %H:%M"),
            'date_traitement': self.date_traitement.strftime("%d/%m/%Y à %H:%M") if self.date_traitement else 'En attente'
        }

    def peut_etre_annule(self):
        """Vérifie si le retrait peut être annulé"""
        return self.statut in ['en_attente']