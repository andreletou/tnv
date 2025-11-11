import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-your-secret-key-here'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition
INSTALLED_APPS = [
    'tnv',
    'core.apps.CoreConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'widget_tweaks',
    'django.contrib.humanize',
    'leaflet',
    'clients',
    'commercants',
    'livraisons',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tnv.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'tnv.wsgi.application'

import os

# Configuration GDAL forcée pour Windows
if os.name == 'nt':
    # Utiliser explicitement le GDAL de Conda
    GDAL_LIBRARY_PATH = r'C:\Users\DRAMTECH\miniconda3\envs\gis_env\Library\bin\gdal.dll'
    GEOS_LIBRARY_PATH = r'C:\Users\DRAMTECH\miniconda3\envs\gis_env\Library\bin\geos_c.dll'
    
    # Variables d'environnement
    os.environ['GDAL_DATA'] = r'C:\Users\DRAMTECH\miniconda3\envs\gis_env\Library\share\gdal'
    os.environ['PROJ_LIB'] = r'C:\Users\DRAMTECH\miniconda3\envs\gis_env\Library\share\proj'
    
    # Ajouter au PATH
    os.environ['PATH'] = r'C:\Users\DRAMTECH\miniconda3\envs\gis_env\Library\bin;' + os.environ['PATH']

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.spatialite',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

LEAFLET_CONFIG = {
    'DEFAULT_CENTER': (6.1375, 1.2125),  # Lomé, Togo
    'DEFAULT_ZOOM': 12,
    'MIN_ZOOM': 3,
    'MAX_ZOOM': 18,
    'RESET_VIEW': False,
    'SCALE': 'metric',
    'ATTRIBUTION_PREFIX': 'LiveDelivery',
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Lome'
USE_I18N = True
USE_TZ = True

#permission user
AUTH_USER_MODEL = 'core.User'


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication settings
LOGIN_URL = 'clients:connexion'
LOGIN_REDIRECT_URL = 'clients:accueil'
LOGOUT_REDIRECT_URL = 'clients:accueil'

# Messages
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
}