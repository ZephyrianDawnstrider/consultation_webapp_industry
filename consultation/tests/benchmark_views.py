import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'consultaion_webapp.settings')

import django
django.setup()

import pytest
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from consultation.views import (
    consultant_dashboard,
    consultant_timesheet,
    save_timesheet_entries,
    upload_timesheet,
    delete_timesheet,
    consultant_profile,
)
from custom_admin.models import User
import json


@pytest.mark.django_db
def benchmark_consultant_dashboard(benchmark):
    factory = RequestFactory()
    user = User.objects.filter(role='consultant').first()
    request = factory.get('/consultant/dashboard')
    request.user = user
    benchmark(consultant_dashboard, request)

@pytest.mark.django_db
def benchmark_consultant_timesheet(benchmark):
    factory = RequestFactory()
    user = User.objects.filter(role='consultant').first()
    request = factory.get('/consultant/timesheet')
    request.user = user
    benchmark(consultant_timesheet, request)

@pytest.mark.django_db
def benchmark_save_timesheet_entries(benchmark):
    factory = RequestFactory()
    user = User.objects.filter(role='consultant').first()
    data = {
        "timesheet_id": None,
        "entries": [
            {
                "date": "2025-04-01",
                "start_time": "09:00",
                "end_time": "17:00",
                "hours_worked": "8",
                "task_name": "Task 1",
                "description": "Description 1"
            }
        ],
        "selected_year": "2025",
        "selected_month": "04"
    }
    request = factory.post('/consultant/save_timesheet_entries', data=json.dumps(data), content_type='application/json')
    request.user = user
    benchmark(save_timesheet_entries, request)

# Note: upload_timesheet and delete_timesheet require file uploads and permissions, so benchmarking them requires more setup.
# For now, we benchmark only the above simpler views.

@pytest.mark.django_db
def benchmark_consultant_profile(benchmark):
    factory = RequestFactory()
    user = User.objects.filter(role='consultant').first()
    request = factory.get(f'/consultant/profile/{user.id}')
    request.user = user
    benchmark(consultant_profile, request)
