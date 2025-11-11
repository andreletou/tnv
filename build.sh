#!/usr/bin/env bash
set -o errexit

echo "=== Mise à jour de pip ==="
pip install --upgrade pip

echo "=== Installation des dépendances de base ==="
pip install Django==4.2.7
pip install djangorestframework==3.14.0
pip install psycopg2-binary==2.9.9
pip install Pillow==10.1.0
pip install gunicorn==21.2.0
pip install whitenoise==6.6.0

echo "=== Installation des autres dépendances une par une ==="
pip install django-cors-headers==4.3.1
pip install django-environ==0.11.2
pip install celery==5.3.4
pip install redis==5.0.1
pip install channels==4.0.0
pip install channels-redis==4.1.0
pip install daphne==4.0.0
pip install django-extensions==3.2.3
pip install drf-spectacular==0.26.5
pip install python-decouple==3.8
pip install requests==2.31.0
pip install stripe==7.5.0
pip install geopy==2.4.1
pip install django-phonenumber-field==7.3.0
pip install phonenumbers==8.13.25
pip install django-allauth==0.57.0
pip install dj-rest-auth==5.0.2
pip install reportlab==4.0.7
pip install openpyxl==3.1.2
pip install python-dateutil==2.8.2
pip install pytz==2023.3

echo "=== Application des migrations ==="
python manage.py migrate

echo "=== Collecte des fichiers statiques ==="
python manage.py collectstatic --no-input

echo "✅ Build terminé avec succès !"
