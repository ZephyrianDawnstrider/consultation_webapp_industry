from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from consultant.models import ConsultantProfile
from custom_admin.models import ConsultantStatus

User = get_user_model()

class Command(BaseCommand):
    help = 'Create missing ConsultantProfile for consultant users'

    def handle(self, *args, **options):
        consultants = User.objects.filter(role='consultant')
        created_profiles = 0

        for consultant in consultants:
            profile, profile_created = ConsultantProfile.objects.get_or_create(user=consultant)
            if profile_created:
                # Create or get ConsultantStatus
                status, status_created = ConsultantStatus.objects.get_or_create(user=consultant)
                if status_created:
                    status.status = 'to_be_reviewed'
                    status.save()
                profile.status = status
                profile.name = consultant.email  # Default name as email if missing
                profile.save()
                self.stdout.write(f'Created ConsultantProfile for user {consultant.email}')
                created_profiles += 1

        self.stdout.write(self.style.SUCCESS(
            f'Created {created_profiles} ConsultantProfiles.'
        ))
