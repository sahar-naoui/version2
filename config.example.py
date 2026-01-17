"""
Fichier de configuration d'exemple
Copiez ce fichier en config.py et modifiez les valeurs selon votre environnement
"""

# Configuration Email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "saharnaoui92@gmail.com"
SMTP_PASSWORD = "pgou ujow mwtd szmv"

# Configuration SMS (exemple avec différents fournisseurs)
# Option 1: Twilio
SMS_PROVIDER = "twilio"
SMS_ACCOUNT_SID = "votre-account-sid"
SMS_AUTH_TOKEN = "votre-auth-token"
SMS_FROM_NUMBER = "+1234567890"

# Option 2: Autre fournisseur
# SMS_PROVIDER = "custom"
# SMS_API_URL = "https://api.sms-provider.com/send"
# SMS_API_KEY = "votre-api-key"

# Configuration Base de Données
# SQLite (par défaut)
DATABASE_URL = "sqlite:///./steg_parking.db"

# PostgreSQL (exemple)
# DATABASE_URL = "postgresql://user:password@localhost/steg_parking"

# MySQL (exemple)
# DATABASE_URL = "mysql+pymysql://user:password@localhost/steg_parking"

# Configuration JWT
SECRET_KEY = "changez-ceci-en-production-avec-une-cle-secrete-forte"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Numéro d'appel STEG par défaut
DEFAULT_STEG_PHONE = "+216 71 340 211"
