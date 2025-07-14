from django.urls import path
from . import views

app_name = 'general'

urlpatterns = [
    path('book-consultant/', views.book_consultant, name='book_consultant'),
]
