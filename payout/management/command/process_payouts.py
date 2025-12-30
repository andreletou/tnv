# management/commands/process_payouts.py
from django.core.management.base import BaseCommand
from payout.managers import PayoutManager

class Command(BaseCommand):
    help = 'Traiter les retraits en attente'
    
    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=50, help='Taille du lot')
        parser.add_argument('--auto', action='store_true', help='Créer et traiter automatiquement')
    
    def handle(self, *args, **options):
        batch_size = options['batch_size']
        
        if options['auto']:
            # Mode automatique
            batch = PayoutManager.creer_batch_automatique(batch_size)
            if batch:
                self.stdout.write(f"🎯 Traitement batch {batch.reference}...")
                resultats = PayoutManager.traiter_batch(batch.id)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Terminé: {resultats['success']} succès, {resultats['failed']} échecs"
                    )
                )
            else:
                self.stdout.write("ℹ️ Aucun retrait à traiter")
        else:
            # Mode manuel
            self.stdout.write("📋 Retraits en attente:")
            retraits = PayoutManager.get_retraits_en_attente()[:10]
            for r in retraits:
                self.stdout.write(f"  - {r.id}: {r.montant}F -> {r.numero_compte}")