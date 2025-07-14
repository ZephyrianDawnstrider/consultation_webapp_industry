from celery import Celery
from celery.schedules import crontab
from django.conf import settings

app = Celery('consultant_webapp')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'cleanup-redundant-files-weekly': {
        'task': 'consultant.tasks.cleanup_redundant_files_task',
        'schedule': crontab(minute=0, hour=0, day_of_week='monday'),  # Every Monday at midnight
    },
    'cleanup-old-logs-daily': {
        'task': 'consultant.tasks.cleanup_old_logs_task',
        'schedule': crontab(minute=0, hour=0),  # Every day at midnight
    },
}
