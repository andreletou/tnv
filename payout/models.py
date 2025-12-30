# payout/models.py
from django.db import models
from django.utils import timezone
from decimal import Decimal
import uuid

class PayoutConfig(models.Model):
    """Configuration des paramètres de payout"""
    frais_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)
    montant_minimum = models.DecimalField(max_digits=10, decimal_places=2, default=500.00)
    montant_maximum = models.DecimalField(max_digits=10, decimal_places=2, default=500000.00)
    plafond_quotidien = models.DecimalField(max_digits=10, decimal_places=2, default=1000000.00)
    est_actif = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Configuration Payout"
        verbose_name_plural = "Configurations Payout"
    
    def __str__(self):
        return f"Config Payout ({self.frais_percentage}%)"

class PayoutBatch(models.Model):
    """Lot de traitement des retraits"""
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('erreur', 'Erreur'),
    ]
    
    reference = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    nombre_retraits = models.IntegerField(default=0)
    succes = models.IntegerField(default=0)
    echecs = models.IntegerField(default=0)
    montant_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_debut = models.DateTimeField(null=True, blank=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    logs = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Lot de Payout"
        verbose_name_plural = "Lots de Payout"
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"Batch {self.reference} - {self.get_statut_display()}"
    
    def ajouter_log(self, message):
        """Ajouter un message de log"""
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logs += f"\n[{timestamp}] {message}"
        self.save()