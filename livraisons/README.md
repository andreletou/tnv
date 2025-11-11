# Application Livraisons - Django

Une application Django complète pour la gestion des livraisons avec suivi en temps réel, géolocalisation et interface interactive.

## 🚀 Fonctionnalités

### Pour les livreurs
- **Inscription complète** avec validation des documents (permis, carte grise)
- **Tableau de bord** avec statistiques en temps réel
- **Carte interactive** montrant les boutiques et livraisons disponibles
- **Suivi d'itinéraire** en temps réel avec GPS
- **Gestion des disponibilités** (en ligne/hors ligne)
- **Historique des livraisons** avec filtres
- **Évaluations et notes** des clients
- **Notifications push** pour nouvelles livraisons
- **Système d'urgence** pour signaler des problèmes

### Fonctionnalités techniques
- **Géolocalisation** avec Django GIS et PostGIS
- **API REST** pour la communication en temps réel
- **Carte interactive** avec Leaflet.js
- **Design responsive** avec Bootstrap 5
- **Suivi en temps réel** des positions
- **Calcul d'itinéraires** et distances
- **Système de notifications** automatiques

## 📋 Prérequis

- Python 3.8+
- Django 4.0+
- PostgreSQL avec PostGIS
- Dependencies GIS (GDAL, GEOS, PROJ)

## 🛠️ Installation

### 1. Cloner et installer les dépendances

```bash
pip install django
pip install psycopg2-binary
pip install django-contrib-gis
pip install pillow
```

### 2. Configuration de la base de données

Ajoutez à votre `settings.py` :

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'votre_db',
        'USER': 'votre_user',
        'PASSWORD': 'votre_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 3. Ajouter l'application

Dans `settings.py` :

```python
INSTALLED_APPS = [
    # ... vos autres apps
    'django.contrib.gis',
    'livraisons',
]
```

### 4. Configurer les URLs

Dans votre `urls.py` principal :

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('livraisons/', include('livraisons.urls')),
    # ... vos autres URLs
]
```

### 5. Créer les tables

```bash
python manage.py makemigrations livraisons
python manage.py migrate
```

### 6. Créer un superutilisateur

```bash
python manage.py createsuperuser
```

## 🗂️ Structure des fichiers

```
livraisons/
├── models.py              # Modèles de données (Livreur, Livraison, etc.)
├── views.py               # Vues principales et API
├── forms.py               # Formulaires (inscription, profil, etc.)
├── urls.py                # Configuration des URLs
├── apps.py                # Configuration de l'application
├── signals.py             # Signaux Django pour notifications
├── templates/livraisons/  # Templates HTML
│   ├── base.html          # Template de base
│   ├── inscription.html   # Formulaire d'inscription
│   ├── tableau_de_bord.html # Espace principal
│   ├── carte_interactive.html # Carte des livraisons
│   └── itineraire.html    # Suivi en temps réel
└── static/livraisons/     # Fichiers statiques (CSS, JS, images)
```

## 🎯 Utilisation

### 1. Inscription d'un livreur

Accédez à `/livraisons/inscription/` pour créer un compte livreur avec :
- Informations personnelles
- Photo de profil
- Type de véhicule et immatriculation
- Documents (permis, carte grise)

### 2. Tableau de bord

Le tableau de bord (`/livraisons/tableau-de-bord/`) affiche :
- Statistiques en temps réel
- Carte des livraisons disponibles
- Livraisons récentes
- Actions rapides

### 3. Carte interactive

La carte (`/livraisons/carte/`) permet de :
- Voir toutes les boutiques enregistrées
- Consulter les livraisons disponibles
- Filtrer par distance et type de véhicule
- Accepter les livraisons directement

### 4. Suivi de livraison

Pendant une livraison (`/livraisons/livraisons/{id}/itineraire/`) :
- Suivi GPS en temps réel
- Itinéraire optimisé
- Temps de livraison
- Communication avec le client
- Système d'urgence

## 🔧 API Endpoints

### Gestion de position
- `POST /livraisons/api/position/mettre-a-jour/` - Mettre à jour la position
- `GET /livraisons/api/position/historique/` - Historique des positions

### Livraisons
- `GET /livraisons/api/livraisons/disponibles/` - Livraisons disponibles
- `GET /livraisons/api/livraisons/proches/` - Livraisons à proximité
- `GET /livraisons/api/itineraire/{id}/` - Itinéraire d'une livraison

### Carte
- `GET /livraisons/api/boutiques/carte/` - Boutiques pour la carte
- `GET /livraisons/api/livraisons/carte/` - Livraisons pour la carte

### Statistiques
- `GET /livraisons/api/statistiques/` - Statistiques du livreur
- `GET /livraisons/api/notifications/` - Notifications

## 📱 Fonctionnalités mobiles

L'application est entièrement responsive et fonctionne sur :
- Smartphones Android
- iPhones
- Tablettes

Les fonctionnalités GPS et géolocalisation sont optimisées pour mobile.

## 🔔 Notifications

Le système de notifications inclut :
- Nouvelles livraisons disponibles
- Changements de statut
- Messages système
- Alertes d'urgence

## 📊 Statistiques et rapports

- Nombre de livraisons effectuées
- Revenus générés
- Note moyenne des clients
- Temps moyen de livraison
- Distance parcourue

## 🛡️ Sécurité

- Validation des documents lors de l'inscription
- Suivi en temps réel des positions
- Système d'alerte d'urgence
- Chiffrement des données sensibles

## 🚨 Gestion des urgences

Les livreurs peuvent signaler :
- Accidents
- Pannes véhicule
- Problèmes de sécurité
- Autres urgences

## 🔄 Intégration avec les autres applications

Cette application s'intègre parfaitement avec :
- **clients/** : Gestion des commandes clients
- **commercants/** : Gestion des boutiques et produits

## 📝 Notes importantes

1. **Configuration GIS** : Assurez-vous d'avoir correctement configuré PostGIS
2. **Permissions** : Configurez les permissions des fichiers médias pour les uploads
3. **HTTPS** : Utilisez HTTPS en production pour la géolocalisation
4. **Performance** : Optimisez les requêtes GIS pour de meilleures performances

## 🐛 Dépannage

### Problèmes courants

**Erreur GDAL** :
```bash
# Sur Ubuntu/Debian
sudo apt-get install gdal-bin
sudo apt-get install libgdal-dev
pip install GDAL==$(gdal-config --version)
```

**Problèmes de migration** :
```bash
python manage.py migrate livraisons --fake
```

**Position non mise à jour** :
- Vérifiez les permissions HTTPS
- Assurez-vous que le navigateur autorise la géolocalisation

## 📞 Support

Pour toute question ou problème, consultez la documentation ou contactez l'équipe de développement.

---

**Développé avec ❤️ pour les livreurs professionnels**