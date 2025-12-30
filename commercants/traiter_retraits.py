# management/commands/traiter_retraits.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from clients.models import RetraitCommercant

class Command(BaseCommand):
    help = 'Traiter les retraits des commerçants automatiquement'

    def handle(self, *args, **options):
        retraits_en_attente = RetraitCommercant.objects.filter(
            statut='en_attente'
        )
        
        for retrait in retraits_en_attente:
            if retrait.traiter():
                self.stdout.write(
                    self.style.SUCCESS(f'Retrait traité: {retrait.id} - {retrait.montant} FCFA')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Échec retrait: {retrait.id}')
                )