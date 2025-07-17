from django.core.management.base import BaseCommand
from custom_admin.models import ActivityLog

class Command(BaseCommand):
    help = 'Fix ActivityLog URLs by replacing /custom_admin/ with /auth/'

    def handle(self, *args, **options):
        logs = ActivityLog.objects.filter(url__startswith='/custom_admin/')
        count = logs.count()
        self.stdout.write(f'Found {count} ActivityLog entries with /custom_admin/ URLs.')

        for log in logs:
            old_url = log.url
            new_url = old_url.replace('/custom_admin/', '/auth/')
            log.url = new_url
            log.save()
            self.stdout.write(f'Updated ActivityLog id={log.id} URL from {old_url} to {new_url}')

        self.stdout.write('ActivityLog URL fix completed.')
