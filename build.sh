#!/usr/bin/env bash
set -o errexit

# Mise à jour de pip
pip install --upgrade pip

# Installation des dépendances Python sans GDAL pour le moment
pip install -r requirements.txt

# Appliquer les migrations
python manage.py migrate

# Collecter les fichiers statiques
python manage.py collectstatic --no-input
