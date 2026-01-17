"""
Script pour vérifier si un utilisateur existe dans la base de données
"""

from database import SessionLocal
from models import User
from auth import verify_password

def check_user(username: str, password: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"✗ Utilisateur '{username}' n'existe pas dans la base de données")
            print("  → Exécutez 'python init_db.py' pour créer les utilisateurs par défaut")
            return False
        
        print(f"✓ Utilisateur '{username}' trouvé")
        print(f"  - Email: {user.email}")
        print(f"  - Rôle: {user.role}")
        print(f"  - Actif: {user.is_active}")
        
        if verify_password(password, user.hashed_password):
            print(f"✓ Mot de passe correct pour '{username}'")
            return True
        else:
            print(f"✗ Mot de passe incorrect pour '{username}'")
            return False
            
    except Exception as e:
        print(f"✗ Erreur: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python check_user.py <username> <password>")
        print("\nExemple:")
        print("  python check_user.py admin admin123")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    check_user(username, password)
