from django.urls import path
from . import views

urlpatterns = [
    path('consultant_dashboard/', views.consultant_dashboard, name='consultant_dashboard'),
]
