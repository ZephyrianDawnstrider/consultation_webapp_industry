# Consultation Platform - Complete Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture & Structure](#architecture--structure)
3. [Installation & Setup](#installation--setup)
4. [Configuration](#configuration)
5. [Features & Modules](#features--modules)
6. [API Documentation](#api-documentation)
7. [Database Schema](#database-schema)
8. [Deployment Guide](#deployment-guide)
9. [Development Guidelines](#development-guidelines)
10. [Troubleshooting](#troubleshooting)
11. [Maintenance & Operations](#maintenance--operations)
12. [FAQ](#faq)

---

## Project Overview

### What is the Consultation Platform?
The Consultation Platform is a comprehensive Django-based web application designed to manage consultants, clients, and consultation services. It provides a complete ecosystem for:
- Consultant registration and profile management
- Client consultation booking
- Invoice generation and management
- Timesheet tracking
- Administrative oversight
- Document management

### Key Stakeholders
- **Consultants**: Register, manage profiles, track time, generate invoices
- **Clients**: Book consultations, view services
- **Administrators**: Manage the entire platform, oversee consultants and operations

---

## Architecture & Structure

### Project Structure
```
consultation_platform/
├── consultaion_webapp/          # Main Django project
│   ├── settings.py             # Project settings
│   ├── urls.py                 # Main URL configuration
│   ├── celery.py              # Celery configuration
│   ├── celery_tasks.py        # Background tasks
│   └── media/                 # User uploaded files
├── consultation/               # Consultant-facing app
├── custom_admin/              # Admin interface app
├── general/                   # General pages (landing, etc.)
├── docs/                      # Documentation files
├── logs/                      # Application logs
├── media/                     # Media files storage
├── staticfiles/              # Static files for production
└── requirements/             # Dependencies
```

### Technology Stack
- **Backend**: Django 4.x
- **Database**: SQLite (development), PostgreSQL (production)
- **Task Queue**: Celery
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **File Storage**: Local filesystem / Cloud storage
- **Deployment**: Docker, Render.com

---

## Installation & Setup

### Prerequisites
- Python 3.8+
- pip
- Git
- Docker (optional)

### Local Development Setup

1. **Clone the Repository**
```bash
git clone <repository-url>
cd consultation_platform
```

2. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment Configuration**
Create a `.env` file in the root directory:
```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

5. **Database Setup**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py create_admin_user  # Custom command
```

6. **Collect Static Files**
```bash
python manage.py collectstatic
```

7. **Run Development Server**
```bash
python manage.py runserver
```

### Docker Setup

1. **Build Docker Image**
```bash
docker build -t consultation-platform .
```

2. **Run Container**
```bash
docker run -p 8000:8000 consultation-platform
```

---

## Configuration

### Settings Overview
The project uses Django's settings system with environment-specific configurations.

#### Key Settings
- `DEBUG`: Development mode toggle
- `ALLOWED_HOSTS`: Permitted host headers
- `DATABASES`: Database configuration
- `MEDIA_ROOT`: File upload location
- `STATIC_ROOT`: Static files location
- `EMAIL_*`: Email service configuration

#### Environment Variables
```env
# Core Settings
DEBUG=False
SECRET_KEY=production-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgresql://user:password@host:port/dbname

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=your-app-password

# File Storage
MEDIA_URL=/media/
STATIC_URL=/static/

# Celery (if using background tasks)
CELERY_BROKER_URL=redis://localhost:6379/0
```

---

## Features & Modules

### 1. General Module (`general/`)
**Purpose**: Landing page and public-facing content

**Key Features**:
- Landing page with service overview
- Session booking form
- Public information display

**Files**:
- `views.py`: Public page views
- `templates/landingpage.html`: Main landing page
- `templates/Session_Booking_Form.html`: Booking interface

### 2. Consultation Module (`consultation/`)
**Purpose**: Consultant-facing functionality

**Key Features**:
- Consultant registration and profile management
- Dashboard for consultants
- Timesheet management
- Invoice generation
- Document uploads (agreements, timesheets)

**Key Files**:
- `models.py`: Consultant data models
- `views.py`: Consultant interface views
- `forms.py`: Form definitions
- `tasks.py`: Background tasks
- `templates/`: Consultant interface templates

**Management Commands**:
- `cleanup_old_logs.py`: Remove old log files
- `cleanup_redundant_files.py`: Clean unused media files

### 3. Custom Admin Module (`custom_admin/`)
**Purpose**: Administrative interface and management

**Key Features**:
- Admin dashboard
- Consultant management
- Skills management
- Invoice oversight
- User management
- System monitoring

**Key Files**:
- `models.py`: Admin-specific models
- `views.py`: Admin interface views
- `serializers.py`: API serializers
- `utils.py`: Utility functions
- `constants.py`: System constants

**Management Commands**:
- `create_admin_user.py`: Create administrative users
- `send_test_email.py`: Test email configuration
- `test_add_consultant.py`: Test consultant creation

---

## Database Schema

### Core Models

#### User Model (Extended)
```python
# Extended Django User model
- username
- email
- first_name
- last_name
- phone_number
- is_active
- date_joined
```

#### ConsultantProfile
```python
- user (OneToOne with User)
- name
- mobile
- skills (ManyToMany with Skill)
- status (Active/Inactive)
- agreement_document
- created_at
- updated_at
```

#### Skill
```python
- name
- description
- is_active
- created_at
```

#### Invoice
```python
- consultant (ForeignKey to User)
- amount
- status (Pending/Paid/Cancelled)
- invoice_date
- due_date
- description
- file_path
```

#### ConsultantStatus
```python
- consultant (ForeignKey to User)
- status
- updated_at
```

### Database Migrations
The project includes comprehensive migrations in each app's `migrations/` directory:
- Initial schema creation
- Model modifications
- Data migrations
- Index optimizations

---

## API Documentation

### Authentication
The platform uses Django's built-in authentication system with session-based auth for web interface and token-based auth for API endpoints.

### Key Endpoints

#### Consultant Endpoints
```
GET  /consultation/dashboard/          # Consultant dashboard
POST /consultation/register/           # Consultant registration
GET  /consultation/profile/            # View/edit profile
POST /consultation/timesheet/          # Submit timesheet
GET  /consultation/invoices/           # View invoices
```

#### Admin Endpoints
```
GET  /admin/dashboard/                 # Admin dashboard
GET  /admin/consultants/               # Manage consultants
POST /admin/consultants/add/           # Add new consultant
GET  /admin/skills/                    # Manage skills
GET  /admin/invoices/                  # Invoice management
```

#### General Endpoints
```
GET  /                                 # Landing page
POST /book-session/                    # Book consultation session
```

---

## Deployment Guide

### Production Deployment on Render.com

1. **Prepare render.yaml**
```yaml
services:
  - type: web
    name: consultation-platform
    env: python
    buildCommand: pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
    startCommand: gunicorn consultaion_webapp.wsgi:application
    envVars:
      - key: DEBUG
        value: False
      - key: SECRET_KEY
        generateValue: true
      - key: DATABASE_URL
        fromDatabase:
          name: consultation-db
          property: connectionString

databases:
  - name: consultation-db
    databaseName: consultation_platform
    user: consultation_user
```

2. **Environment Variables Setup**
Set the following in Render dashboard:
- `DEBUG=False`
- `SECRET_KEY` (auto-generated)
- `ALLOWED_HOSTS=your-app-name.onrender.com`
- Email configuration variables

3. **Database Migration**
```bash
python manage.py migrate
python manage.py create_admin_user
```

### Docker Deployment

1. **Dockerfile Configuration**
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "consultaion_webapp.wsgi:application", "--bind", "0.0.0.0:8000"]
```

2. **Docker Compose (Optional)**
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://user:pass@db:5432/consultation
    depends_on:
      - db
  
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: consultation
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## Development Guidelines

### Code Structure
- Follow Django best practices
- Use class-based views where appropriate
- Implement proper error handling
- Add logging for important operations
- Write tests for critical functionality

### File Organization
```
app_name/
├── models.py          # Data models
├── views.py           # View logic
├── forms.py           # Form definitions
├── urls.py            # URL patterns
├── admin.py           # Admin interface
├── tasks.py           # Background tasks
├── utils.py           # Utility functions
├── tests.py           # Test cases
├── templates/         # HTML templates
├── static/            # CSS, JS, images
└── management/        # Custom commands
```

### Best Practices
1. **Models**: Use descriptive field names, add proper constraints
2. **Views**: Keep views thin, move business logic to models/utils
3. **Templates**: Use template inheritance, avoid logic in templates
4. **Forms**: Validate data properly, use Django form features
5. **Security**: Always validate user input, use CSRF protection

### Testing
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test consultation

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors
**Problem**: `django.db.utils.OperationalError`
**Solution**:
- Check database credentials
- Ensure database server is running
- Verify network connectivity
- Check DATABASE_URL format

#### 2. Static Files Not Loading
**Problem**: CSS/JS files not found in production
**Solution**:
```bash
python manage.py collectstatic --clear
```
- Check STATIC_ROOT and STATIC_URL settings
- Ensure web server serves static files correctly

#### 3. Email Not Sending
**Problem**: Email functionality not working
**Solution**:
- Verify email settings in environment variables
- Test email configuration:
```bash
python manage.py send_test_email
```
- Check firewall/security settings

#### 4. File Upload Issues
**Problem**: Cannot upload files
**Solution**:
- Check MEDIA_ROOT permissions
- Verify file size limits
- Ensure proper form enctype: `multipart/form-data`

#### 5. Migration Errors
**Problem**: Migration conflicts or failures
**Solution**:
```bash
# Reset migrations (development only)
python manage.py migrate --fake-initial

# Or create new migration
python manage.py makemigrations --merge
```

### Debugging Tools

#### 1. Django Debug Toolbar (Development)
Add to `INSTALLED_APPS` for detailed debugging information.

#### 2. Logging Configuration
Check logs in the `logs/` directory:
- `backend.log`: General application logs
- `errors.log`: Error messages
- `server.log`: Server-related logs

#### 3. Management Commands for Debugging
```bash
# Test consultant creation
python manage.py test_add_consultant

# Clean up old files
python manage.py cleanup_old_logs
python manage.py cleanup_redundant_files
```

---

## Maintenance & Operations

### Regular Maintenance Tasks

#### 1. Database Maintenance
```bash
# Backup database
python manage.py dumpdata > backup.json

# Clean up old sessions
python manage.py clearsessions

# Optimize database (PostgreSQL)
python manage.py dbshell
VACUUM ANALYZE;
```

#### 2. File System Cleanup
```bash
# Remove old log files
python manage.py cleanup_old_logs

# Clean redundant media files
python manage.py cleanup_redundant_files

# Clear old static files
python manage.py collectstatic --clear
```

#### 3. Security Updates
- Regularly update Django and dependencies
- Monitor security advisories
- Review user permissions
- Check for unused accounts

### Monitoring

#### 1. Log Monitoring
Monitor these log files:
- `logs/backend.log`: Application events
- `logs/errors.log`: Error tracking
- `logs/general.log`: General system logs
- `logs/server.log`: Server operations

#### 2. Performance Monitoring
- Database query performance
- File upload/download speeds
- User session management
- Memory usage

#### 3. Health Checks
Create a simple health check endpoint:
```python
def health_check(request):
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now(),
        'database': 'connected' if connection.ensure_connection() else 'disconnected'
    })
```

---

## FAQ

### General Questions

**Q: What is the purpose of this platform?**
A: The Consultation Platform manages the entire lifecycle of consultant-client relationships, from registration and booking to invoicing and document management.

**Q: Who can use this platform?**
A: Three main user types: Consultants (service providers), Clients (service consumers), and Administrators (platform managers).

**Q: Is this platform scalable