from django.urls import path
from . import views

app_name = 'general'

urlpatterns = [
    path('ProspectiveConsultant/', views.ProspectiveConsultant, name='ProspectiveConsultant'),
    path('consultant/book/', views.ProspectiveConsultant, name='consultant_book'),
]
