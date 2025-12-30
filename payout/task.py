# payout/tasks.py
from celery import shared_task
from .managers import PayoutManager
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def traiter_retraits_automatiques(self, batch_size=50):
    """Tâche Celery pour traitement automatique des retraits"""
    try:
        # Créer un nouveau batch
        batch = PayoutManager.creer_batch_automatique(batch_size)
        
        if not batch:
            logger.info("Aucun retrait à traiter")
            return {'status': 'no_retraits'}
        
        # Traiter le batch
        resultats = PayoutManager.traiter_batch(batch.id)
        
        logger.info(f"Traitement batch {batch.id} terminé: {resultats}")
        return {
            'status': 'success',
            'batch_id': batch.id,
            'resultats': resultats
        }
        
    except Exception as e:
        logger.error(f"Erreur tâche payout: {str(e)}")
        # Réessayer après 10 minutes
        raise self.retry(countdown=600, exc=e)

@shared_task
def nettoyer_anciens_batches():
    """Nettoyer les batches de plus de 30 jours"""
    from django.utils import timezone
    from datetime import timedelta
    from .models import PayoutBatch
    
    date_limite = timezone.now() - timedelta(days=30)
    batches_supprimes = PayoutBatch.objects.filter(
        date_creation__lt=date_limite
    ).delete()
    
    logger.info(f"Batches nettoyés: {batches_supprimes}")