# payout/managers.py
import logging
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from clients.models import RetraitCommercant, Portefeuille
from clients.paygate import PayGateGlobal
from .models import PayoutBatch, PayoutConfig

logger = logging.getLogger(__name__)

class PayoutManager:
    """
    Gestionnaire complet des payouts automatiques
    """
    
    @classmethod
    def creer_batch_automatique(cls, batch_size=50):
        """Créer un nouveau lot de traitement"""
        with transaction.atomic():
            # Récupérer les retraits en attente
            retraits = RetraitCommercant.objects.select_related(
                'portefeuille', 'portefeuille__user'
            ).filter(
                statut='en_attente',
                date_demande__gte=timezone.now() - timezone.timedelta(hours=24)
            )[:batch_size]
            
            if not retraits:
                return None
            
            # Créer le batch
            batch = PayoutBatch.objects.create(
                nombre_retraits=len(retraits),
                montant_total=sum(r.montant for r in retraits)
            )
            
            batch.ajouter_log(f"📦 Batch créé avec {len(retraits)} retraits")
            return batch
    
    @classmethod
    def traiter_batch(cls, batch_id):
        """Traiter un lot complet de retraits"""
        try:
            batch = PayoutBatch.objects.get(id=batch_id)
            batch.statut = 'en_cours'
            batch.date_debut = timezone.now()
            batch.save()
            
            batch.ajouter_log("🚀 Début du traitement du batch")
            
            # Récupérer les retraits du batch
            retraits = RetraitCommercant.objects.select_related(
                'portefeuille', 'portefeuille__user'
            ).filter(
                statut='en_attente',
                date_demande__gte=timezone.now() - timezone.timedelta(hours=24)
            )[:batch.nombre_retraits]
            
            resultats = {'success': 0, 'failed': 0}
            
            for retrait in retraits:
                try:
                    if cls._traiter_retrait_individuel(retrait, batch):
                        resultats['success'] += 1
                    else:
                        resultats['failed'] += 1
                        
                except Exception as e:
                    logger.error(f"Erreur traitement retrait {retrait.id}: {str(e)}")
                    resultats['failed'] += 1
                    batch.ajouter_log(f"❌ Erreur retrait {retrait.id}: {str(e)}")
            
            # Finaliser le batch
            batch.statut = 'termine'
            batch.succes = resultats['success']
            batch.echecs = resultats['failed']
            batch.date_fin = timezone.now()
            batch.ajouter_log(
                f"✅ Batch terminé: {resultats['success']} succès, {resultats['failed']} échecs"
            )
            batch.save()
            
            return resultats
            
        except Exception as e:
            logger.error(f"Erreur traitement batch {batch_id}: {str(e)}")
            if 'batch' in locals():
                batch.statut = 'erreur'
                batch.ajouter_log(f"💥 Erreur batch: {str(e)}")
                batch.save()
            return {'success': 0, 'failed': 0}
    
    @classmethod
    def _traiter_retrait_individuel(cls, retrait, batch):
        """Traiter un retrait individuel de manière transactionnelle"""
        try:
            # Vérifications préalables
            if not cls._verifications_prealables(retrait):
                return False
            
            # Calculer les frais
            config = cls._get_config()
            frais = retrait.montant * (config.frais_percentage / Decimal('100'))
            total_a_debiter = retrait.montant + frais
            
            # Vérifier le solde
            if retrait.portefeuille.solde < total_a_debiter:
                retrait.statut = 'echec'
                retrait.notes_admin = f"Solde insuffisant: {retrait.portefeuille.solde} < {total_a_debiter}"
                retrait.save()
                batch.ajouter_log(f"❌ Solde insuffisant pour retrait {retrait.id}")
                return False
            
            # Traiter selon la méthode
            if retrait.methode == 'mobile_money':
                success = cls._traiter_mobile_money(retrait, batch)
            else:
                success = cls._traiter_virement_bancaire(retrait, batch)
            
            if success:
                batch.ajouter_log(f"✅ Retrait {retrait.id} traité avec succès")
            else:
                batch.ajouter_log(f"❌ Échec traitement retrait {retrait.id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Erreur critique retrait {retrait.id}: {str(e)}")
            retrait.statut = 'echec'
            retrait.notes_admin = f"Erreur critique: {str(e)}"
            retrait.save()
            return False
    
    @classmethod
    def _traiter_mobile_money(cls, retrait, batch):
        """Traiter un retrait Mobile Money via PayGate"""
        try:
            # Générer un identifiant unique
            identifier = f"POUT-{retrait.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            
            batch.ajouter_log(f"📱 Initiation payout Mobile Money pour {retrait.numero_compte}")
            
            # Appeler PayGate
            resultat = PayGateGlobal.initier_paiement_api(
                phone_number=retrait.numero_compte,
                amount=str(int(retrait.montant_net)),  # Montant net
                description=f"Payout {retrait.portefeuille.user.commercant_profile.nom_boutique}",
                identifier=identifier,
                network=retrait.operateur
            )
            
            batch.ajouter_log(f"📥 Réponse PayGate: {resultat}")
            
            if resultat.get('status') == 0:
                # Paiement initié avec succès - Débiter le portefeuille
                frais = retrait.montant * Decimal('0.02')
                
                with transaction.atomic():
                    # Débiter le portefeuille
                    retrait.portefeuille.debiter(
                        retrait.montant + frais,
                        f"Payout Mobile Money - Ref: {resultat.get('tx_reference')}"
                    )
                    
                    # Mettre à jour le retrait
                    retrait.statut = 'traite'
                    retrait.frais_retrait = frais
                    retrait.montant_net = retrait.montant - frais
                    retrait.numero_transaction = resultat.get('tx_reference')
                    retrait.date_traitement = timezone.now()
                    retrait.save()
                
                return True
            else:
                # Échec PayGate
                error_messages = {
                    2: 'Clé API invalide',
                    4: 'Paramètres invalides', 
                    6: 'Transaction déjà existante'
                }
                error_msg = error_messages.get(resultat.get('status'), f"Code: {resultat.get('status')}")
                
                retrait.statut = 'echec'
                retrait.notes_admin = f"PayGate: {error_msg}"
                retrait.save()
                return False
                
        except Exception as e:
            logger.error(f"Erreur PayGate retrait {retrait.id}: {str(e)}")
            retrait.statut = 'echec'
            retrait.notes_admin = f"Exception PayGate: {str(e)}"
            retrait.save()
            return False
    
    @classmethod
    def _traiter_virement_bancaire(cls, retrait, batch):
        """Traiter un virement bancaire (marquer comme traité)"""
        try:
            frais = retrait.montant * Decimal('0.02')
            
            with transaction.atomic():
                # Débiter le portefeuille
                retrait.portefeuille.debiter(
                    retrait.montant + frais,
                    f"Payout virement - En attente envoi manuel"
                )
                
                # Mettre à jour le retrait
                retrait.statut = 'traite'
                retrait.frais_retrait = frais
                retrait.montant_net = retrait.montant - frais
                retrait.date_traitement = timezone.now()
                retrait.save()
            
            batch.ajouter_log(f"🏦 Virement préparé: {retrait.id} -> {retrait.numero_compte}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur virement {retrait.id}: {str(e)}")
            return False
    
    @classmethod
    def _verifications_prealables(cls, retrait):
        """Vérifications de sécurité avant traitement"""
        config = cls._get_config()
        
        # Vérifier montant minimum
        if retrait.montant < config.montant_minimum:
            retrait.statut = 'echec'
            retrait.notes_admin = f"Montant trop faible: {retrait.montant} < {config.montant_minimum}"
            retrait.save()
            return False
        
        # Vérifier montant maximum
        if retrait.montant > config.montant_maximum:
            retrait.statut = 'echec'
            retrait.notes_admin = f"Montant trop élevé: {retrait.montant} > {config.montant_maximum}"
            retrait.save()
            return False
        
        return True
    
    @classmethod
    def _get_config(cls):
        """Récupérer ou créer la configuration"""
        config, created = PayoutConfig.objects.get_or_create(
            id=1,
            defaults={
                'frais_percentage': Decimal('2.00'),
                'montant_minimum': Decimal('500.00'),
                'montant_maximum': Decimal('500000.00'),
                'plafond_quotidien': Decimal('1000000.00'),
            }
        )
        return config