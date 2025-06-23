import os
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'consultaion_webapp.settings')
django.setup()

from custom_admin.models import User
from custom_admin.utils import encrypt_password

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def encrypt_missing_passwords():
    users = User.objects.filter(role='consultant').filter(encrypted_password__isnull=True)
    logger.info(f"Found {users.count()} consultants with missing encrypted_password")

    for user in users:
        try:
            # Encrypt the user's current password hash or set a default password if not set
            # Note: Django stores hashed passwords, so we cannot decrypt them.
            # We must reset the password to a new random one or skip.
            # Here, we skip users without usable password.
            if not user.has_usable_password():
                logger.warning(f"User {user.email} has no usable password, skipping encryption")
                continue

            # We cannot decrypt the hashed password, so we must reset password.
            # For safety, we skip and log.
            logger.warning(f"User {user.email} password is hashed and cannot be encrypted for display. Manual reset needed.")
        except Exception as e:
            logger.error(f"Error processing user {user.email}: {str(e)}")

if __name__ == '__main__':
    encrypt_missing_passwords()
