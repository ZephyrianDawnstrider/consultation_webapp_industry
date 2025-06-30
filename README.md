
# Consultation Web Application

## Overview
This Django-based web application is designed to efficiently manage consultation services by providing a robust platform for both consultants and administrators. It facilitates seamless management of consultant profiles, timesheets, invoices, and session bookings, while offering administrators comprehensive tools for consultant oversight, skill management, invoice processing, and system administration.

## Features

### Consultant Portal
- Interactive dashboard displaying consultations, invoices, and calendar events.
- Upload and manage timesheets in Excel and CSV formats with automatic processing.
- Upload, track, and manage invoices with status updates.
- Manage personal profiles including banking details and skill sets.
- Secure password management with OTP verification and email notifications.
- Upload and manage agreement documents with scrapping functionality.

### Admin Portal
- Comprehensive dashboard with key metrics such as total consultants, pending invoices, and approved sessions.
- Consultant management including adding, editing, deleting, and approving registrations.
- Skill management with create, update, and soft delete capabilities.
- Invoice management with status tracking and automated notifications.
- Secure password reset functionality for consultants with email alerts.

## Technology Stack
- Python 3.x, Django 5.0.14, Django REST Framework
- SQLite (default), Pandas, OpenPyXL, Cryptography
- Gunicorn for deployment, SMTP email notifications

## Installation & Setup
1. Clone the repository and navigate to the project directory.
2. Create and activate a virtual environment.
3. Install dependencies from requirements.txt.
4. Apply database migrations.
5. Create a superuser for admin access.
6. Run the development server.
7. Access the app at `https://consultaion-webapp.onrender.com`.

## Configuration
- Database settings in `consultaion_webapp/settings.py`.
- Email SMTP settings for notifications.
- Media files stored in `media/` directory.
- Logs stored in `logs/` directory.

## Usage

### Consultant Portal
- Login to access dashboard.
- Upload and manage timesheets and invoices.
- Update profile and banking details.
- Change password securely with OTP.
- View upcoming sessions and calendar events.

### Admin Portal
- Login to access admin dashboard.
- Manage consultants, skills, and invoices.
- Approve or reject registrations and timesheets.
- Reset consultant passwords securely.

## Testing
- Tests located in `consultation/tests.py` and `custom_admin/tests.py`.
- Run tests with `python manage.py test`.

## Contributing
- Fork and create feature branches.
- Follow PEP8 standards.
- Write tests for new features.
- Submit pull requests with clear descriptions.

## Contact
For support, contact `chaturvedi1ayush@gmail.com`.
