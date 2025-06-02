from django.core.management.base import BaseCommand
from admin.models import User

class Command(BaseCommand):
    help = 'Create an admin user with predefined credentials'

    def handle(self, *args, **kwargs):
        email = 'admin@example.com'
        password = 'adminpassword123'
        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f'Admin user created with email: {email}'))
        else:
            self.stdout.write(self.style.WARNING('Admin user already exists'))
