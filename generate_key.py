# generate_key.py
from cryptography.fernet import Fernet

# Générer une clé Fernet
key = Fernet.generate_key()
print("=" * 50)
print("AJOUTEZ CE CI DANS VOTRE FICHIER .env:")
print("=" * 50)
print(f"ENCRYPTION_KEY={key.decode()}")
print("=" * 50)