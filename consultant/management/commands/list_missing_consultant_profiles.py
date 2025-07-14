from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from consultant.models import ConsultantProfile

User = get_user_model()

class Command(BaseCommand):
    help = 'List consultant users missing ConsultantProfile'

    def handle(self, *args, **options):
        consultants = User.objects.filter(role='consultant')
        missing_profiles = []

        for consultant in consultants:
            try:
                profile = ConsultantProfile.objects.get(user=consultant)
            except ConsultantProfile.DoesNotExist:
                missing_profiles.append(consultant.email)

        if missing_profiles:
            self.stdout.write('Consultants missing profiles:')
            for email in missing_profiles:
                self.stdout.write(f'- {email}')
        else:
            self.stdout.write('No consultants are missing profiles.')
