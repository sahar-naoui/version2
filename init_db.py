"""
Script d'initialisation de la base de données
Crée un utilisateur admin par défaut
"""

import os
from database import SessionLocal, engine, Base
from models import User, Employee
from auth import get_password_hash

# Supprimer l'ancienne base de données si elle existe (optionnel)
# Décommentez la ligne suivante si vous voulez réinitialiser complètement
# if os.path.exists("steg_parking.db"):
#     os.remove("steg_parking.db")
#     print("✓ Ancienne base de données supprimée")

# Créer les tables
Base.metadata.create_all(bind=engine)
print("✓ Tables créées")

def init_database():
    db = SessionLocal()
    try:
        # Vérifier si un admin existe déjà
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            # Créer un utilisateur admin par défaut
            admin_user = User(
                username="admin",
                email="admin@steg.tn",
                hashed_password=get_password_hash("admin123"),
                full_name="Administrateur",
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print("✓ Utilisateur admin créé (username: admin, password: admin123)")
            
            # Vérifier que le mot de passe fonctionne
            from auth import verify_password
            if verify_password("admin123", admin_user.hashed_password):
                print("✓ Vérification du mot de passe: OK")
            else:
                print("✗ ERREUR: Le mot de passe ne correspond pas!")
        else:
            print("✓ Utilisateur admin existe déjà")
            # Vérifier que le mot de passe fonctionne
            from auth import verify_password
            if verify_password("admin123", admin.hashed_password):
                print("✓ Vérification du mot de passe admin: OK")
            else:
                print("✗ ATTENTION: Le mot de passe admin ne correspond pas!")
                print("  → Le mot de passe dans la BD ne correspond pas à 'admin123'")
        
        # Créer un utilisateur RH par défaut
        rh_user = db.query(User).filter(User.username == "rh").first()
        if not rh_user:
            rh = User(
                username="rh",
                email="rh@steg.tn",
                hashed_password=get_password_hash("rh123"),
                full_name="Ressources Humaines",
                role="rh",
                is_active=True
            )
            db.add(rh)
            db.commit()
            print("✓ Utilisateur RH créé (username: rh, password: rh123)")
        else:
            print("✓ Utilisateur RH existe déjà")
        
        # Afficher tous les utilisateurs
        all_users = db.query(User).all()
        print(f"\n✓ Total utilisateurs dans la base: {len(all_users)}")
        for u in all_users:
            print(f"  - {u.username} ({u.role}) - Actif: {u.is_active}")
        
        print("\n✓ Base de données initialisée avec succès!")
        print("\nComptes par défaut:")
        print("  - Admin: admin / admin123")
        print("  - RH: rh / rh123")
        print("\n⚠️  IMPORTANT: Changez ces mots de passe en production!")
        
    except Exception as e:
        print(f"✗ Erreur lors de l'initialisation: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
