# management/commands/verifier_depots.py
from django.core.management.base import BaseCommand
from clients.models import DepotPortefeuille
from clients.paygate import PayGateGlobal

class Command(BaseCommand):
    help = 'Vérifie les dépôts en attente et les valide si payés'

    def handle(self, *args, **options):
        depots_en_attente = DepotPortefeuille.objects.filter(statut='en_attente')
        
        self.stdout.write(f"Vérification de {depots_en_attente.count()} dépôts en attente...")
        
        for depot in depots_en_attente:
            if depot.numero_transaction:
                statut = PayGateGlobal.verifier_statut_paiement(depot.numero_transaction)
                
                if statut.get('status') == 0:  # Paiement réussi
                    if depot.valider():
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Dépôt {depot.id} validé - {depot.montant} FCFA'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f'Erreur validation dépôt {depot.id}'
                            )
                        )
                elif statut.get('status') in [2, 4, 6]:  # Échec
                    depot.statut = 'echec'
                    depot.save()
                    self.stdout.write(
                        self.style.WARNING(
                            f'Dépôt {depot.id} marqué comme échec'
                        )
                    )