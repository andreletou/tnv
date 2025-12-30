import os
from pathlib import Path
import dj_database_url
from django.core.management.utils import get_random_secret_key

# Configuration GDAL pour Windows avec OSGeo4W
if os.name == 'nt':  # Windows
    OSGEO4W_PATH = r'C:\OSGeo4W'
    
    if os.path.exists(OSGEO4W_PATH):
        # Ajouter OSGeo4W au PATH
        os.environ['PATH'] = OSGEO4W_PATH + r'\bin;' + os.environ['PATH']
        
        # Configuration pour GDAL 3.11.5
        os.environ['GDAL_LIBRARY_PATH'] = OSGEO4W_PATH + r'\bin\gdal311.dll'
        os.environ['GEOS_LIBRARY_PATH'] = OSGEO4W_PATH + r'\bin\geos_c.dll'
        
        # Configurer les données
        os.environ['PROJ_LIB'] = OSGEO4W_PATH + r'\share\proj'
        os.environ['GDAL_DATA'] = OSGEO4W_PATH + r'\share\gdal'
        
        print("✅ OSGeo4W configuré avec GDAL 3.11.5")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', get_random_secret_key())

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*','https://unmulish-macrosporic-betsey.ngrok-free.dev/',]
# csrf trusted origins
CSRF_TRUSTED_ORIGINS = ['https://unmulish-macrosporic-betsey.ngrok-free.dev']
INSTALLED_APPS = [
    'tnv',
    'core.apps.CoreConfig',
    "unfold",
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
    'payout',
    'whitenoise.runserver_nostatic',
]

UNFOLD = {
    "SITE_HEADER": "Admin Panel",
    "SITE_TITLE": "Admin",
    "SITE_URL": "/",
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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

# Configuration de la base de données pour le développement
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.contrib.gis.db.backends.spatialite',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'local_links',
        'USER': 'postgres',
        'PASSWORD': 'Elom1234@',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

LEAFLET_CONFIG = {
    'DEFAULT_CENTER': (6.1375, 1.2125),
    'DEFAULT_ZOOM': 12,
    'MIN_ZOOM': 3,
    'MAX_ZOOM': 18,
    'RESET_VIEW': False,
    'SCALE': 'metric',
    'ATTRIBUTION_PREFIX': 'Local-Links',
}
API_SECRET_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImE0ZGJjNjk5M2ZjNDQ3NDI4MDQ1NjMxMzRhNTU5YmQ4IiwiaCI6Im11cm11cjY0In0='
GOOGLE_MAPS_API_KEY = "AIzaSyCT58ApU8KaL53EZzFl2EEW2iCQOgv96Rw"

# PayGate Configuration
PAYGATE_AUTH_TOKEN = "9498ec13-33e9-4f53-bfa2-66e95e5bdc08"
PAYGATE_WEBHOOK_URL = "https://votredomaine.com/clients/webhook/paygate/"

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

# Permission user
AUTH_USER_MODEL = 'core.User'

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Optimisation des fichiers statiques avec WhiteNoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication settings
LOGIN_URL = 'clients:connexion'
LOGIN_REDIRECT_URL = 'clients:redirection_apres_connexion'
LOGOUT_REDIRECT_URL = 'home'


# Messages
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
}

# Configuration pour le développement
if DEBUG:
    # Outils de débogage
    INSTALLED_APPS += [
        'debug_toolbar',
    ]
    
    MIDDLEWARE += [
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    ]
    
    # Configuration pour Django Debug Toolbar
    INTERNAL_IPS = [
        '127.0.0.1',
        'localhost',
    ]
    
    # Email backend pour développement
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    
    # Désactiver la sécurité HTTPS en développement
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
else:
    # Configuration de sécurité pour la production
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True


# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Lome'

CELERY_BEAT_SCHEDULE = {
    'process-payouts-every-30-min': {
        'task': 'payout.tasks.traiter_retraits_automatiques',
        'schedule': 1800.0,  # Toutes les 30 minutes
        'kwargs': {'batch_size': 25}
    },
}