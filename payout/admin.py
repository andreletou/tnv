# payout/admin.py
from django.contrib import admin
from .models import PayoutConfig, PayoutBatch

@admin.register(PayoutConfig)
class PayoutConfigAdmin(admin.ModelAdmin):
    list_display = ['frais_percentage', 'montant_minimum', 'montant_maximum', 'est_actif']
    list_editable = ['est_actif']

@admin.register(PayoutBatch)
class PayoutBatchAdmin(admin.ModelAdmin):
    list_display = ['reference', 'statut', 'nombre_retraits', 'succes', 'echecs', 'date_creation']
    list_filter = ['statut', 'date_creation']
    readonly_fields = ['reference', 'date_creation', 'date_debut', 'date_fin', 'logs']
    search_fields = ['reference']