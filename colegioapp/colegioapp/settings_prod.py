# settings_prod.py
from .settings import *  # Importa toda la configuración base (local)

# ---------- Modo producción ----------
DEBUG = False

# Cuando tengas el servidor:
# - reemplaza "TU_IP_PUBLICA" por la IP del Droplet
# - si tienes dominio, agrégalo aquí también
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "TU_IP_PUBLICA",   # ejemplo: "157.230.123.45"
    "TU_DOMINIO.com",  # ejemplo: "colegio.g-devsolutions.com"
]

# ---------- Base de datos producción ----------
# Cuando elijas la BD del VPS, ajustamos esto.
# De momento lo dejo igual pero con host 'localhost'
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "colegio_db",
        "USER": "root",          # cambia esto en el VPS por un usuario seguro
        "PASSWORD": "Spot2022",  # cambia esto también en el VPS
        "HOST": "localhost",     # en el Droplet la DB estará en el mismo servidor
        "PORT": "3306",
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES', innodb_strict_mode=1",
        },
    }
}

# ---------- Archivos estáticos / media en producción ----------
# En producción, collectstatic va a llenar esta carpeta:
STATIC_ROOT = BASE_DIR / "staticfiles"

# Si quieres, puedes dejar STATICFILES_DIRS como en settings.py
# (se mantiene porque lo importamos arriba)

# Media (subidas) — normalmente igual en prod
MEDIA_ROOT = BASE_DIR / "media"

# ---------- Opciones de seguridad recomendadas (para cuando tengas HTTPS) ----------
# Las puedes activar luego cuando tengas certificado SSL
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_HSTS_SECONDS = 31536000  # 1 año
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True