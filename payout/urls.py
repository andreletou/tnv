from django.urls import path
from . import views

app_name = 'payout'

urlpatterns = [
    path('dashboard/', views.dashboard_payout, name='dashboard'),
    path('api/lancer-traitement/', views.api_lancer_traitement, name='api_lancer_traitement'),
    path('api/statistiques/', views.api_statistiques, name='api_statistiques'),
]

# python manage.py process_payouts --auto --batch-size 25

# celery -A tnv worker --queues=payout -l info
# celery -A tnv beat -l info