# Consultation Web Application

## Overview
This is a Django-based web application designed to manage consultation services. It provides a platform for consultants to manage their profiles, timesheets, invoices, and session bookings. The application also includes a custom admin interface for managing consultants, skills, invoices, and overall system administration.

## Features

### Consultant Portal
- Dashboard displaying consultations, invoices, and calendar events.
- Upload, view, and manage timesheets (CSV format).
- Upload and track invoices.
- Manage personal profile including banking details and skills.
- Password management with OTP verification and email notifications.
- Agreement document upload and scrapping functionality.

### Admin Portal
- Dashboard with key metrics (total consultants, pending invoices, approved sessions).
- Consultant management: add, edit, delete consultants with email notifications.
- Skill management with create, update, and soft delete functionality.
- Invoice management with status updates.
- Consultant registration approval and status management.
- Password reset for consultants with email notifications.

## Technology Stack
- Python 3.x
- Django 5.0.14
- Django REST Framework
- SQLite (default, can be configured for other databases)
- Pandas and OpenPyXL for Excel and CSV processing
- Cryptography for password encryption
- Gunicorn for deployment
- Email notifications via SMTP (Gmail configured by default)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd consultaion_webapp
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Apply migrations:
   ```bash
   python manage.py migrate
   ```

5. Create a superuser (optional, for admin access):
   ```bash
   python manage.py createsuperuser
   ```

6. Run the development server:
   ```bash
   python manage.py runserver
   ```

7. Access the application at `http://127.0.0.1:8000/`

## Configuration

- **Database:** Default is SQLite. To use another database, update `DATABASES` in `consultaion_webapp/settings.py`.
- **Email:** SMTP settings are configured for Gmail by default. Update `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` in `settings.py` for your email account.
- **Media Files:** Uploaded files are stored in the `media/` directory by default. Cloud storage options (AWS S3, GCP, Azure) can be configured via environment variables.
- **Logging:** Logs are stored in the `logs/` directory with separate files for general, backend, errors, and server logs.

## Usage

### Consultant Portal
- Login as a consultant to access the dashboard.
- Upload timesheets in Excel format; they are converted to CSV automatically.
- View and manage invoices.
- Update profile information and manage password with OTP verification.
- View upcoming session bookings and calendar events.

### Admin Portal
- Login as an admin to access the dashboard.
- Manage consultants: add new consultants, edit details, reset passwords, and delete accounts.
- Manage skills used by consultants.
- Review and update invoice statuses.
- Approve or reject consultant registrations and timesheets.

## Testing
- Tests are located in the `consultation/tests.py` and `custom_admin/tests.py` files.
- Run tests using:
  ```bash
  python manage.py test
  ```

## Contributing
- Fork the repository and create a feature branch.
- Follow PEP8 coding standards.
- Write tests for new features or bug fixes.
- Submit a pull request with a clear description of changes.

## License
This project is licensed under the MIT License.

## Contact
For questions or support, contact the project maintainer at `chaturvedi1ayush@gmail.com`.
