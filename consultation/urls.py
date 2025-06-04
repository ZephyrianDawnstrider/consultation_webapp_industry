from django.urls import path
from . import views

app_name = 'consultation'

urlpatterns = [
    path('consultant_dashboard/', views.consultant_dashboard, name='consultant_dashboard'),
    path('consultant_timesheet/', views.consultant_timesheet, name='consultant_timesheet'),
    path('consultant_profile/<int:consultant_id>/', views.consultant_profile, name='consultant_profile'),
    path('consultant_registration/', views.consultant_registration, name='consultant_registration'),
    path('consultant_invoice/', views.consultant_invoice, name='consultant_invoice'),
]
