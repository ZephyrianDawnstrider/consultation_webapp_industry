from cryptography.fernet import Fernet
from django.conf import settings
from django.urls import reverse
from urllib.parse import urlencode

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

def get_activitylog_url(name, *args, query_params=None, **kwargs):
    """
    Utility function to generate URLs for ActivityLog entries using Django reverse.
    Usage:
        url = get_activitylog_url('custom_admin:timesheet', consultant_id=1, year=2025, month='05')
        url = get_activitylog_url('custom_admin:timesheet', query_params={'consultant_id': 1, 'year': 2025, 'month': '05'})
    """
    url = reverse(name, args=args, kwargs=kwargs)
    if query_params:
        url += '?' + urlencode(query_params)
    return url
