from cryptography.fernet import Fernet
from django.conf import settings

def get_fernet():
    key = settings.FERNET_KEY
    return Fernet(key)

def encrypt_password(plain_password: str) -> str:
    fernet = get_fernet()
    encrypted = fernet.encrypt(plain_password.encode())
    return encrypted.decode()

def decrypt_password(encrypted_password: str) -> str:
    fernet = get_fernet()
    decrypted = fernet.decrypt(encrypted_password.encode())
    return decrypted.decode()
