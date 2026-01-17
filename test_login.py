"""
Script de test pour vérifier le login
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_login(username: str, password: str):
    """Teste le login avec username et password"""
    url = f"{BASE_URL}/api/auth/login"
    data = {
        "username": username,
        "password": password
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"\n=== Test Login: {username} ===")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Login réussi!")
            print(f"Token: {result.get('access_token', '')[:50]}...")
            return True
        else:
            print(f"✗ Login échoué")
            print(f"Réponse: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Erreur: {e}")
        return False

def test_health():
    """Teste l'endpoint health"""
    url = f"{BASE_URL}/health"
    try:
        response = requests.get(url)
        print(f"\n=== Test Health ===")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✓ Health check OK")
            print(f"Réponse: {response.json()}")
            return True
        else:
            print(f"✗ Health check échoué")
            return False
    except Exception as e:
        print(f"✗ Erreur: {e}")
        print("  → Assurez-vous que le serveur est lancé (python main.py)")
        return False

def test_create_admin():
    """Teste la création d'un admin"""
    url = f"{BASE_URL}/api/auth/create-admin"
    try:
        response = requests.post(url)
        print(f"\n=== Test Create Admin ===")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 201:
            print("✓ Admin créé avec succès")
            print(f"Réponse: {response.json()}")
            return True
        else:
            print(f"✗ Échec de création")
            print(f"Réponse: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Erreur: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Tests de l'API STEG Parking")
    print("=" * 50)
    
    # Test health
    test_health()
    
    # Test création admin
    test_create_admin()
    
    # Test login admin
    test_login("admin", "admin123")
    
    # Test login avec mauvais mot de passe
    test_login("admin", "wrongpassword")
    
    print("\n" + "=" * 50)
