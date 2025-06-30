from celery import shared_task
from django.core.management import call_command

@shared_task
def cleanup_redundant_files_task():
    call_command('cleanup_redundant_files')

@shared_task
def cleanup_old_logs_task():
    call_command('cleanup_old_logs')
