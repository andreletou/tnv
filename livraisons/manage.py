import django
from django.conf import settings
import os

# Configurer les settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

# Initialiser Django
django.setup()

# Import des modèles après la configuration
from livraisons.models import Livreur, Livraison, PositionLivreur, EvaluationLivreur, NotificationLivreur
from clients.models import Client, Commande
from commercants.models import Commercant

def main():
    print("Application Livraisons - Gestion des livreurs et livraisons")
    print("=" * 60)
    
    # Vérifier les modèles
    print("\nModèles disponibles:")
    print("- Livreur: Gestion des comptes livreurs")
    print("- Livraison: Suivi des livraisons")
    print("- PositionLivreur: Historique des positions")
    print("- EvaluationLivreur: Évaluations des livreurs")
    print("- NotificationLivreur: Système de notifications")
    
    print("\nFonctionnalités principales:")
    print("✓ Inscription et authentification des livreurs")
    print("✓ Géolocalisation en temps réel")
    print("✓ Carte interactive avec les boutiques")
    print("✓ Système d'acceptation des livraisons")
    print("✓ Suivi d'itinéraire en temps réel")
    print("✓ Évaluations et statistiques")
    print("✓ Notifications push")
    print("✓ Gestion des disponibilités")
    
    print("\nAPI Endpoints:")
    print("- PUT /api/position/mettre-a-jour/: Mise à jour position")
    print("- POST /api/disponibilite/: Gestion disponibilité")
    print("- GET /api/livraisons/disponibles/: Livraisons disponibles")
    print("- GET /api/itineraire/{id}/: Itinéraire livraison")
    print("- GET /api/statistiques/: Statistiques livreur")
    
    print("\nTemplates créés:")
    print("- base.html: Template de base")
    print("- inscription.html: Formulaire d'inscription")
    print("- tableau_de_bord.html: Espace principal")
    print("- carte_interactive.html: Carte des livraisons")
    print("- itineraire.html: Suivi en temps réel")
    
    print("\nPour intégrer cette application:")
    print("1. Ajouter 'livraisons' à INSTALLED_APPS")
    print("2. Inclure les URLs dans urls.py principal")
    print("3. Configurer les dépendances GIS (PostGIS, GDAL)")
    print("4. Exécuter les migrations")
    print("5. Créer un superutilisateur pour tester")

if __name__ == '__main__':
    main()