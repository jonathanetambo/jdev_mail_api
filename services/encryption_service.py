# services/encryption_service.py
from cryptography.fernet import Fernet
import os
import json
from config import Config

class EncryptionService:
    def __init__(self):
        key = Config.ENCRYPTION_KEY
        if not key:
            key = Fernet.generate_key().decode()
            print(f"Generate ENCRYPTION_KEY={key} in .env file")
        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
    
    def encrypt_log(self, data: dict) -> bytes:
        json_str = json.dumps(data)
        return self.cipher.encrypt(json_str.encode())
    
    def decrypt_log(self, encrypted_data: bytes) -> dict:
        decrypted = self.cipher.decrypt(encrypted_data)
        return json.loads(decrypted.decode())