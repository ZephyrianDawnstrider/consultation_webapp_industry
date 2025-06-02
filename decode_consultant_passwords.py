import os
import django
import base64
from cryptography.fernet import Fernet

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'consultaion_webapp.settings')
django.setup()

from custom_admin.models import User
from django.conf import settings

def decode_passwords():
    fernet_key = settings.FERNET_KEY
    fernet = Fernet(fernet_key)
    consultants = User.objects.filter(role='consultant')
    for consultant in consultants:
        encrypted_password = consultant.encrypted_password
        if encrypted_password:
            try:
                decrypted_password = fernet.decrypt(encrypted_password.encode()).decode()
            except Exception as e:
                decrypted_password = f"Error decrypting: {str(e)}"
        else:
            decrypted_password = "No encrypted password"
        print(f"Consultant ID: {consultant.id}, Email: {consultant.email}, Decrypted Password: {decrypted_password}")

if __name__ == "__main__":
    decode_passwords()
