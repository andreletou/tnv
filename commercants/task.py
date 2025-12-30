from tnv.celery import shared_task
from django.utils import timezone
from clients.models import RetraitCommercant
from clients.paygate import PayGateGlobal

@shared_task
def verifier_retraits_en_attente():
    """
    Tâche périodique pour vérifier les retraits en attente de confirmation PayGate
    """
    print("🔄 Début vérification automatique des retraits en attente")
    
    retraits = RetraitCommercant.objects.filter(statut='en_attente')
    print(f"📊 {retraits.count()} retrait(s) en attente à vérifier")
    
    for retrait in retraits:
        try:
            print(f"🔍 Vérification retrait {retrait.id} - Référence: {retrait.numero_transaction}")
            
            if retrait.numero_transaction:
                # Vérifier le statut via PayGate
                statut = PayGateGlobal.verifier_statut_paiement(retrait.numero_transaction)
                
                if statut.get('status') == 0:  # Paiement confirmé
                    print(f"✅ Paiement confirmé pour le retrait {retrait.id}")
                    if retrait.traiter():
                        print(f"✅ Retrait {retrait.id} traité avec succès")
                    else:
                        print(f"❌ Échec du traitement du retrait {retrait.id}")
                elif statut.get('status') in [4, 6]:  # Expiré ou annulé
                    print(f"❌ Paiement échoué pour le retrait {retrait.id}")
                    retrait.statut = 'echec'
                    retrait.notes_admin = f"Paiement {statut.get('message', 'échoué')}"
                    retrait.save()
                else:
                    print(f"⏳ Retrait {retrait.id} toujours en attente - Statut: {statut.get('status')}")
                    
        except Exception as e:
            print(f"💥 Erreur lors de la vérification du retrait {retrait.id}: {str(e)}")
            continue
    
    print("✅ Vérification automatique des retraits terminée")