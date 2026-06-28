from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '.onrender.com',      # Render deployment
    '.railway.app',       # Railway deployment (backup)
    '*',                  # temporary for testing
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rag_app',
]

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

ROOT_URLCONF = 'rag_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'rag_project.wsgi.application'

# ── Database ──────────────────────────────────────────────────────────────────
# Uses Supabase in production, SQLite locally
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     os.getenv('DB_NAME', 'postgres'),
        'USER':     os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST':     os.getenv('DB_HOST', ''),
        'PORT':     os.getenv('DB_PORT', '5432'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# ── Static Files ──────────────────────────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── App Settings ──────────────────────────────────────────────────────────────
GROQ_API_KEY     = os.getenv('GROQ_API_KEY', '')
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY', '')
PINECONE_INDEX   = os.getenv('PINECONE_INDEX', 'ragbot')
VECTORSTORE_DIR  = BASE_DIR / 'vectorstore'

# OCR Settings (local development only)
import platform

if platform.system() == "Windows":
    TESSERACT_CMD = os.getenv(
        'TESSERACT_CMD',
        r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    )
    POPPLER_PATH = os.getenv(
        'POPPLER_PATH',
        r'C:\poppler-26.02.0\Library\bin'
    )
else:
    # Linux (Render)
    TESSERACT_CMD = os.getenv('TESSERACT_CMD', '/usr/bin/tesseract')
    POPPLER_PATH  = os.getenv('POPPLER_PATH', None)

# ── Security (production) ─────────────────────────────────────────────────────
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER       = True
    SECURE_CONTENT_TYPE_NOSNIFF     = True
    X_FRAME_OPTIONS                 = 'DENY'
    SECURE_SSL_REDIRECT             = False
    SESSION_COOKIE_SECURE           = True
    CSRF_COOKIE_SECURE              = True