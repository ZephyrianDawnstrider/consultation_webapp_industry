from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from consultant.models import ConsultantProfile
from custom_admin.models import ConsultantStatus

User = get_user_model()

class Command(BaseCommand):
    help = 'Automatically create missing ConsultantProfile for consultant users'

    def handle(self, *args, **options):
        consultants = User.objects.filter(role='consultant')
        created_profiles = 0

        for consultant in consultants:
            try:
                profile = ConsultantProfile.objects.get(user=consultant)
            except ConsultantProfile.DoesNotExist:
                # Create or get ConsultantStatus
                status, status_created = ConsultantStatus.objects.get_or_create(user=consultant)
                if status_created:
                    status.status = 'to_be_reviewed'
                    status.save()
                profile = ConsultantProfile.objects.create(
                    user=consultant,
                    status=status,
                    name=consultant.email,  # Default name as email if missing
                    mobile='',
                    bank_account_name='',
                    bank_account_number='',
                    bank_ifsc='',
                    bank_branch_name='',
                    bank_name='',
                    cost_per_hour=0  # Default value to avoid null error
                )
                self.stdout.write(f'Created ConsultantProfile for user {consultant.email}')
                created_profiles += 1

        self.stdout.write(self.style.SUCCESS(
            f'Created {created_profiles} ConsultantProfiles.'
        ))
