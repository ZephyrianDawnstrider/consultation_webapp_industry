import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'consultant_webapp.settings')

app = Celery('consultant_webapp')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
