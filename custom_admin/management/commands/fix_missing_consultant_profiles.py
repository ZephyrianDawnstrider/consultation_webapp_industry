from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from custom_admin.models import ConsultantStatus

User = get_user_model()

class Command(BaseCommand):
    help = 'Create missing ConsultantStatus for consultant users'

    def handle(self, *args, **options):
        consultants = User.objects.filter(role='consultant')
        created_statuses = 0

        for consultant in consultants:
            status, status_created = ConsultantStatus.objects.get_or_create(user=consultant)
            if status_created:
                status.status = 'to_be_reviewed'
                status.save()
                self.stdout.write(f'Created ConsultantStatus for user {consultant.email}')
                created_statuses += 1

        self.stdout.write(self.style.SUCCESS(
            f'Created {created_statuses} ConsultantStatuses.'
        ))
