# consultant Platform - Developer Guide

## Table of Contents
1. [Project Architecture](#project-architecture)
2. [Development Environment Setup](#development-environment-setup)
3. [Codebase Structure](#codebase-structure)
4. [Database Design](#database-design)
5. [API Architecture](#api-architecture)
6. [Frontend Implementation](#frontend-implementation)
7. [Background Tasks & Celery](#background-tasks--celery)
8. [Testing Framework](#testing-framework)
9. [Deployment & DevOps](#deployment--devops)
10. [Security Implementation](#security-implementation)
11. [Performance Optimization](#performance-optimization)
12. [Extension & Customization](#extension--customization)
13. [Debugging & Monitoring](#debugging--monitoring)
14. [Contributing Guidelines](#contributing-guidelines)
15. [Future Roadmap](#future-roadm

---

## Project Architecture

### Technology Stack Overview

```python
# Core Technologies
Backend Framework: Django 4.x
Database: SQLite (dev) / PostgreSQL (prod)
Task Queue: Celery + Redis
Frontend: HTML5, CSS3, JavaScript, Bootstrap
File Storage: Local filesystem / Cloud storage
Deployment: Docker, Render.com
Testing: Django TestCase, pytest
Monitoring: Django logging, custom metrics
```

### System Architecture Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Django App    │    │   Database      │
│   (Templates)   │◄──►│   (Views/APIs)  │◄──►│   (Models)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Celery Tasks  │
                       │   (Background)  │
                       └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   File Storage  │
                       │   (Media/Docs)  │
                       └─────────────────┘
```

### Application Flow

```python
# Request Flow
1. User Request → Django URLs → Views
2. Views → Models (Database Operations)
3. Models → Business Logic → Response
4. Background Tasks → Celery → Redis Queue
5. Static Files → Collected Static → CDN/Server
```

---

## Development Environment Setup

### Prerequisites Installation

```bash
# System Requirements
python --version  # 3.8+
pip --version
git --version
docker --version  # Optional but recommended
```

### Local Development Setup

```bash
# 1. Clone Repository
git clone <repository-url>
cd consultant_platform

# 2. Create Virtual Environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Environment Configuration
cp .env.example .env
# Edit .env with your local settings
```

### Environment Variables Configuration

```bash:.env
# Development Settings
DEBUG=True
SECRET_KEY=your-development-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration
DATABASE_URL=sqlite:///db.sqlite3
# For PostgreSQL: postgresql://user:password@localhost:5432/consultant_db

# Email Configuration (Development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# File Storage
MEDIA_ROOT=media/
STATIC_ROOT=staticfiles/

# Celery Configuration (Optional)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Security Settings
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=0
```

### Database Setup

```bash
# Database Migrations
python manage.py makemigrations
python manage.py migrate

# Create Superuser
python manage.py createsuperuser

# Load Initial Data (if fixtures exist)
python manage.py loaddata initial_data.json

# Create Admin User (Custom Command)
python manage.py create_admin_user
```

### Development Server

```bash
# Start Development Server
python manage.py runserver

# Start with specific port
python manage.py runserver 8080

# Start Celery Worker (separate terminal)
celery -A consultaion_webapp worker --loglevel=info

# Start Celery Beat (for scheduled tasks)
celery -A consultaion_webapp beat --loglevel=info
```

---

## Codebase Structure

### Project Organization

```
consultant_platform/
├── consultaion_webapp/          # Main Django project
│   ├── __init__.py
│   ├── settings.py             # Django settings
│   ├── urls.py                 # Root URL configuration
│   ├── wsgi.py                 # WSGI application
│   ├── asgi.py                 # ASGI application
│   ├── celery.py               # Celery configuration
│   └── celery_tasks.py         # Shared Celery tasks
├── consultant/               # Consultant-facing app
├── custom_admin/              # Admin interface app
├── general/                   # Public pages app
├── requirements.txt           # Python dependencies
├── manage.py                 # Django management script
├── Dockerfile               # Docker configuration
└── render.yaml             # Render deployment config
```

### App-Level Structure

```python
# Standard Django App Structure
app_name/
├── __init__.py
├── admin.py                # Django admin configuration
├── apps.py                 # App configuration
├── models.py               # Data models
├── views.py                # View logic
├── urls.py                 # URL patterns
├── forms.py                # Form definitions
├── serializers.py          # DRF serializers (if using DRF)
├── utils.py                # Utility functions
├── constants.py            # App constants
├── tasks.py                # Celery tasks
├── tests.py                # Test cases
├── migrations/             # Database migrations
├── management/             # Custom management commands
│   └── commands/
├── templates/              # HTML templates
├── static/                 # CSS, JS, images
└── templatetags/           # Custom template tags
```

### Key Configuration Files

#### Django Settings (`consultaion_webapp/settings.py`)

```python:consultaion_webapp/settings.py
import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# Security Settings
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# Application Definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'celery',
]

LOCAL_APPS = [
    'consultant',
    'custom_admin',
    'general',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Middleware Configuration
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'consultaion_webapp.urls'

# Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Static Files Configuration
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media Files Configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email Configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'backend.log',
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'errors.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'consultant': {
            'handlers': ['file', 'error_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'custom_admin': {
            'handlers': ['file', 'error_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

#### URL Configuration (`consultaion_webapp/urls.py`)

```python:consultaion_webapp/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Admin URLs
    path('django-admin/', admin.site.urls),
    path('admin/', include('custom_admin.urls')),
    
    # App URLs
    path('consultant/', include('consultant.urls')),
    path('', include('general.urls')),
    
    # API URLs (if implementing REST API)
    path('api/v1/', include('api.urls')),
    
    # Redirect root to landing page
    path('', RedirectView.as_view(url='/landing/', permanent=False)),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

---

## Database Design

### Model Architecture

#### Core Models Overview

```python
# Model Relationships
User (Django Auth) ←→ ConsultantProfile
ConsultantProfile ←→ Skills (ManyToMany)
User ←→ Invoice (ForeignKey)
User ←→ ConsultantStatus (ForeignKey)
```

#### User Model Extension

```python:custom_admin/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """Extended User model with additional fields"""
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'auth_user'
        
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def __str__(self):
        return self.username
```

#### Consultant Profile Model

```python:custom_admin/models.py
class ConsultantProfile(models.Model):
    """Consultant profile information"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending'),
        ('suspended', 'Suspended'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='consultant_profile')
    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15, blank=True)
    bio = models.TextField(blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    skills = models.ManyToManyField('Skill', blank=True, related_name='consultants')
    agreement_document = models.FileField(upload_to='agreements/', blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'consultant_profile'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    @property
    def is_active(self):
        return self.status == 'active'
    
    def get_skills_list(self):
        return list(self.skills.values_list('name', flat=True))
```

#### Skills Model

````python:custom_admin/models.py
class Skill(models.Model):
    """Skills that consultants can have"""
    CATEGORY_CHOICES = [
        ('technical', 'Technical'),
        ('business', 'Business'),
        ('creative', 'Creative'),
        ('consulting', 'Consulting'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='technical')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'skills'
        ordering = ['category', 'name']