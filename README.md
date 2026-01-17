# API Backend FastAPI - Système de Gestion de Parking STEG

## Description

Backend FastAPI pour la gestion du parking STEG avec système d'alertes automatiques, gestion des réclamations, absences et sanctions.

## Installation

1. Installer les dépendances:
```bash
pip install -r requirements.txt
```

2. Initialiser la base de données:
```bash
python init_db.py
```

Cela créera un utilisateur admin par défaut:
- Username: `admin`
- Password: `admin123`

3. Lancer le serveur:
```bash
python main.py
```

Ou avec uvicorn:
```bash
uvicorn main:app --reload
```

L'API sera accessible sur `http://localhost:8000`

4. Tester le login:
```bash
python test_login.py
```

## Documentation API

Une fois le serveur lancé, la documentation interactive est disponible sur:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Structure du Projet

```
version2/
├── main.py              # Application FastAPI principale
├── database.py          # Configuration de la base de données
├── models.py            # Modèles SQLAlchemy
├── schemas.py           # Schémas Pydantic
├── auth.py              # Authentification et permissions
├── services.py          # Services (alertes, sanctions, etc.)
├── requirements.txt     # Dépendances Python
└── uploads/             # Dossier pour les fichiers uploadés
    ├── complaints/      # Photos de réclamations
    └── absences/        # Justificatifs d'absence
```

## Fonctionnalités

### Endpoints Publics (Guest)
- `GET /api/public/work-schedules` - Consulter les horaires de travail
- `GET /api/public/steg-phone` - Consulter le numéro d'appel STEG

### Authentification
- `POST /api/auth/login` - Se connecter (Admin, RH, Employee) - Format JSON: `{"username": "admin", "password": "admin123"}`
- `POST /api/auth/register` - Créer un nouvel utilisateur
- `POST /api/auth/create-admin` - Créer un utilisateur admin (si la base est vide)
- `GET /api/auth/me` - Obtenir les infos de l'utilisateur connecté
- `PUT /api/auth/profile` - Modifier son profil

### Endpoints Employee (Employee, RH, Admin)
- `GET /api/employee/parking-spot` - Consulter son numéro de place
- `POST /api/employee/complaints` - Ajouter une réclamation avec photo
- `GET /api/employee/absences` - Consulter ses absences
- `POST /api/employee/absences` - Ajouter une justification d'absence
- `GET /api/employee/alerts` - Consulter ses alertes

### Endpoints Admin + RH
- Gestion des employés (CRUD)
- Gestion des véhicules (CRUD)
- Gestion des réclamations
- Vérification des justifications d'absence
- Sanctionner un employé
- Gestion des profils utilisateurs

### Endpoints Admin uniquement
- Gestion des utilisateurs RH
- Gestion des horaires de travail
- Déclencher la vérification des alertes

### Système d'Alertes Automatiques

Le système vérifie automatiquement:
1. **Absences/Retards**: Si un véhicule n'est pas présent à 9:01 (ou à l'heure de début prévue), une alerte est envoyée par email et SMS
2. **Véhicules ÉTAT la nuit**: Les véhicules de classe ÉTAT doivent être présents la nuit (20h-8h)

### Système de Sanctions

1. **Première réclamation**: Avertissement envoyé à l'employé
2. **Deuxième réclamation**: Bannissement du parking pour 3 jours

## Configuration

### Email et SMS

Modifier les paramètres dans `services.py`:
- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` pour l'email
- `SMS_API_URL`, `SMS_API_KEY` pour le SMS

### Base de Données

Par défaut, SQLite est utilisé (`steg_parking.db`). Pour utiliser PostgreSQL ou MySQL, modifier `database.py`.

## Rôles

- **admin**: Accès complet à toutes les fonctionnalités
- **rh**: Gestion des employés, véhicules, réclamations, absences
- **employee**: Consultation et ajout de réclamations/absences
- **guest**: Accès public aux horaires et numéro STEG

## Notes

- Les fichiers uploadés (photos de réclamations, justificatifs) sont stockés dans le dossier `uploads/`
- Le système d'alertes peut être déclenché manuellement via `/api/admin/check-alerts`
- Les sanctions désactivent automatiquement l'autorisation du véhicule pendant la période de sanction
