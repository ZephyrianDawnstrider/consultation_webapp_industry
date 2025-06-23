"""
Custom Admin Views for Consultation Web Application

This module contains all the views for the custom admin interface including:
- Consultant management (CRUD operations)
- User authentication and registration
- Invoice management
- Skills management
- Dashboard functionality
"""

import json
import logging
import random
import re
from datetime import datetime

# Django imports
from .forms import ConsultantEditForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Prefetch
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Timesheet

from django.core.files.base import ContentFile

from django.forms import modelformset_factory
# Removed import of TimesheetEntryFormSet as it is no longer used
# from .forms import TimesheetEntryFormSet
from datetime import datetime, timedelta
# Django imports


@login_required
@csrf_exempt
@require_POST
def update_timesheet_status(request, timesheetId):
    """
    View to update the status of a timesheet via AJAX POST request.
    """
    timesheet = get_object_or_404(Timesheet, id=timesheetId)
    status = request.POST.get('status')

    if status not in ['awaiting_review', 'approved', 'rejected']:
        return JsonResponse({'success': False, 'message': 'Invalid status value.'})

    timesheet.status = status
    timesheet.save()

    # Log the status update
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Timesheet ID {timesheetId} status updated to {status} by user {request.user.email}")

    return JsonResponse({'success': True, 'message': 'Timesheet status updated successfully.'})

@login_required
@csrf_exempt
@require_POST
def save_timesheet_entries(request):
    """
    Save edited timesheet entries from JSON POST data, overwrite CSV file.
    Includes server-side validation of entries.
    Deletes the timesheet file and record if entries are empty.
    """
    user = request.user
    try:
        data = json.loads(request.body)
        timesheet_id = data.get('timesheet_id')
        entries = data.get('entries')
        if not timesheet_id or entries is None:
            return JsonResponse({'success': False, 'message': 'Missing timesheet_id or entries.'})

        # Fetch the timesheet instance
        timesheet = Timesheet.objects.get(id=timesheet_id)

        # Check if user has permission (staff or owner)
        if not (user.is_staff or timesheet.consultant == user):
            return JsonResponse({'success': False, 'message': 'Permission denied.'})

        # If entries list is empty, delete the file and timesheet record
        if len(entries) == 0:
            # Delete the file from storage
            timesheet.file.delete(save=False)
            # Delete the timesheet record
            timesheet.delete()
            return JsonResponse({'success': True, 'message': 'Timesheet deleted as it was empty.'})

        # Server-side validation function
        def validate_entry(entry):
            if not entry.get('date'):
                return 'Date is required.'
            if not entry.get('start_time'):
                return 'Start Time is required.'
            if not entry.get('end_time'):
                return 'End Time is required.'
            if entry.get('start_time') >= entry.get('end_time'):
                return 'Start Time must be before End Time.'
            if not entry.get('task_name') or entry.get('task_name').strip() == '':
                return 'Task Name is required.'
            return None

        # Validate all entries
        for i, entry in enumerate(entries):
            error = validate_entry(entry)
            if error:
                return JsonResponse({'success': False, 'message': f'Error in entry {i + 1}: {error}'})

        # Prepare CSV output
        output = StringIO()
        fieldnames = ['Date', 'Start Time', 'End Time', 'Task Name', 'Description']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for entry in entries:
            writer.writerow({
                'Date': entry.get('date', ''),
                'Start Time': entry.get('start_time', ''),
                'End Time': entry.get('end_time', ''),
                'Task Name': entry.get('task_name', ''),
                'Description': entry.get('description', ''),
            })

        csv_content = output.getvalue()
        output.close()

        # Save CSV content to the file field
        timesheet.file.save(timesheet.file.name, content=ContentFile(csv_content.encode('utf-8')))
        timesheet.save()

        return JsonResponse({'success': True, 'message': 'Timesheet entries saved successfully.'})
    except Timesheet.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Timesheet not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error saving timesheet entries: {str(e)}'})
from django import forms
from django.conf import settings

# Third-party imports
from cryptography.fernet import Fernet
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response


# Removed all code related to Excel file extraction and processing as requested.


# Local imports
from .models import User, Skill, Invoice, SessionBooking, Timesheet
from consultation.models import ConsultantProfile
import csv
from io import StringIO
from django.core.serializers.json import DjangoJSONEncoder
import logging
import io
from datetime import datetime

from .serializers import SkillSerializer

# Configure logging
logger = logging.getLogger(__name__)
User = get_user_model()

# =============================================================================
# FORMS
# =============================================================================

class ConsultantRegistrationForm(forms.Form):
    """Form for consultant registration with all required fields"""
    
    # Personal Information
    name = forms.CharField(max_length=255, label="Full Name")
    mobile = forms.CharField(max_length=20, label="Mobile Number")
    email = forms.EmailField(label="Email Address")
    agreement = forms.BooleanField(label="Agreement Accepted")
    
    # Banking Information
    bank_account_name = forms.CharField(max_length=255, label="Account Holder Name")
    bank_account_number = forms.CharField(max_length=50, label="Account Number")
    bank_ifsc = forms.CharField(max_length=20, label="IFSC Code")
    bank_branch_name = forms.CharField(max_length=255, label="Branch Name")
    bank_name = forms.CharField(max_length=255, label="Bank Name")
    
    # Professional Information
    cost_per_hour = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        label="Cost Per Hour"
    )
    skills = forms.ModelMultipleChoiceField(
        queryset=None, 
        widget=forms.CheckboxSelectMultiple,
        label="Skills"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['skills'].queryset = Skill.objects.all()
        
from custom_admin.forms import ConsultantEditForm as ImportedConsultantEditForm

# Use the imported ConsultantEditForm in the view function

@login_required
@csrf_exempt
@require_http_methods(["GET", "POST"])
def edit_consultant(request, consultant_id):
    """
    Edit consultant profile information, including password change with email notification
    """
    user = get_object_or_404(User, id=consultant_id, role='consultant')
    
    # Get or create consultant profile
    try:
        profile = user.consultant_profile
    except ConsultantProfile.DoesNotExist:
        profile = ConsultantProfile(user=user)

    if request.method == 'POST':
        logger.info(f"Received POST data: {request.POST}")
        form = ImportedConsultantEditForm(request.POST, request.FILES, instance=profile)
        logger.info(f"Form fields: {form.fields.keys()}")
        if form.is_valid():
            logger.info("Form is valid")
            try:
                # Save profile fields
                form.save()
                profile.save()

                # Handle password change if password field is filled
                new_password = form.cleaned_data.get('password')
                logger.info(f"Password field value: {new_password}")
                if new_password:
                    try:
                        from custom_admin.utils import encrypt_password
                        encrypted_password = encrypt_password(new_password)
                        user.encrypted_password = encrypted_password
                        user.set_password(new_password)
                        user.save()

                        # Send email with new login credentials
                        from django.conf import settings
                        email_message = (
                            f"Dear {user.email},\n\n"
                            f"Your password has been changed by the admin.\n"
                            f"Your new login credentials are:\n"
                            f"Email: {user.email}\n"
                            f"Password: {new_password}\n\n"
                            f"Please login using these credentials.\n\n"
                            f"Regards,\n"
                            f"Consultation Team"
                        )
                        send_mail(
                            subject='Your Login Credentials Have Been Updated',
                            message=email_message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[user.email],
                            fail_silently=False,
                        )
                        logger.info(f"Password changed and email sent for user {user.email}")
                    except Exception as e:
                        logger.error(f"Error changing password or sending email for user {user.email}: {str(e)}")

                logger.info(f"Consultant details updated successfully for user {user.email}")
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': 'Consultant details updated successfully.'})
                else:
                    messages.success(request, 'Consultant details updated successfully.')
                    return redirect('custom_admin:consultant_profile', consultant_id=consultant_id)
            except Exception as e:
                logger.error(f"Error saving consultant details for user {user.email}: {str(e)}")
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': 'Error saving consultant details.'}, status=500)
                else:
                    messages.error(request, 'An error occurred while saving consultant details.')
                    return redirect('custom_admin:consultant_profile', consultant_id=consultant_id)
        else:
            logger.error(f"Form validation errors: {form.errors}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = form.errors.as_json()
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            else:
                messages.error(request, 'Please correct the errors below.')
                return redirect('custom_admin:consultant_profile', consultant_id=consultant_id)
    else:
        # Redirect GET requests to consultant_detail page
        logger.info(f"Redirecting GET request to consultant_profile for user {user.email}")
        return redirect('custom_admin:consultant_profile', consultant_id=consultant_id)

# =============================================================================
# AUTHENTICATION VIEWS
# =============================================================================

from django.shortcuts import redirect

@login_required
def logout_view(request):
    """Handle user logout and redirect to login page"""
    logout(request)
    return redirect('login')


# =============================================================================
# DASHBOARD VIEWS
# =============================================================================

@login_required
def admin_dashboard(request):
    """
    Admin dashboard with key metrics and statistics
    """
    # Calculate dashboard metrics
    total_consultants = User.objects.filter(role='consultant').count()
    pending_invoices = Invoice.objects.filter(status='pending').count()
    approved_sessions = SessionBooking.objects.count()

    context = {
        'total_consultants': total_consultants,
        'pending_invoices': pending_invoices,
        'approved_sessions': approved_sessions,
        'current_page': 'Dashboard',
    }
    return render(request, 'admin_dashboard.html', context)

# =============================================================================
# CONSULTANT MANAGEMENT VIEWS
# =============================================================================

@login_required
def consultant_management(request):
    """
    Display list of all consultants with their profiles
    """
    consultants = User.objects.filter(role='consultant').select_related('consultant_profile')
    
    context = {
        'consultants': consultants,
        'current_page': 'Consultant Management',
    }
    return render(request, 'consultant_managment.html', context)

@login_required
@csrf_exempt
def add_consultant(request):
    """
    Add new consultant with email notification
    Generates random password and sends login credentials via email
    """
    if request.method == 'POST':
        try:
            # Extract form data
            name = request.POST.get('name', '').strip()
            mobile = request.POST.get('mobile', '').strip()
            email = request.POST.get('email', '').strip()
            agreement = request.FILES.get('agreement')

            logger.info(f"Received add_consultant POST request with name={name}, mobile={mobile}, email={email}, agreement={agreement}")

            # Server-side validation
            if not name:
                logger.warning("Name is required.")
                return JsonResponse({'success': False, 'message': 'Name is required.'})
            
            if not re.fullmatch(r'\d{10}', mobile):
                logger.warning("Mobile number must be exactly 10 digits.")
                return JsonResponse({'success': False, 'message': 'Mobile number must be exactly 10 digits.'})
            
            email_regex = r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'
            if not re.fullmatch(email_regex, email, re.IGNORECASE):
                logger.warning("Invalid email address.")
                return JsonResponse({'success': False, 'message': 'Invalid email address.'})

            # Check for existing user
            if User.objects.filter(email=email).exists():
                logger.warning(f"User with email {email} already exists.")
                return JsonResponse({'success': False, 'message': 'User with this email already exists.'})

            # Generate random password
            autogenerated_password = ''.join(
                random.choices(string.ascii_letters + string.digits, k=10)
            )
            logger.info(f"Generated password for new user: {autogenerated_password}")

            # Create new user
            new_user = User.objects.create_user(
                email=email, 
                role='consultant', 
                password=autogenerated_password
            )
            logger.info(f"Created new user with email {email}")

            # Create consultant status
            from .models import ConsultantStatus
            consultant_status = ConsultantStatus.objects.create(user=new_user, status='to_be_reviewed')
            logger.info(f"Created consultant status 'to_be_reviewed' for user {email}")

            # Create consultant profile with minimal fields
            profile = ConsultantProfile(user=new_user)
            profile.name = name
            profile.mobile = mobile
            profile.status = consultant_status
            profile.cost_per_hour = 0  # Set default cost_per_hour to avoid NOT NULL constraint error
            if agreement:
                profile.agreement_document = agreement
            profile.save()
            logger.info(f"Created consultant profile for user {email}")

            # Send welcome email with credentials
            # login_url = request.build_absolute_uri('/auth/login/')
            email_message = (
                f"Dear {name},\n\n"
                f"Thank you for registering as a consultant.\n"
                f"Your login details are as follows:\n"
                f"Email: {email}\n"
                f"Password: {autogenerated_password}\n\n"
                # f"Please login at: {login_url}\n\n"  # Login URL hidden as per request
                f"Regards,\n"
                f"Consultation Team"
            )

            try:
                send_mail(
                    subject='Consultant Registration Received - Login Details',
                    message=email_message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com'),
                    recipient_list=[email],
                    fail_silently=False,
                )
                logger.info(f"Registration email sent to {email}")
            except Exception as e:
                logger.error(f"Error sending registration email to {email}: {str(e)}")
                return JsonResponse({'success': False, 'message': f'Error sending email: {str(e)}'})

            return JsonResponse({'success': True, 'message': 'Consultant added successfully and email sent.'})
        except Exception as e:
            logger.error(f"Unexpected error in add_consultant: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'message': 'An unexpected error occurred.'})
    
    # GET request - show add consultant form
    return render(request, 'add_consultant.html', {'current_page': 'Add Consultant'})


from .models import ConsultantStatus

@login_required
def consultant_profile(request, consultant_id):
    """
    Display detailed consultant profile with invoices, timesheets, and timesheet entries
    Also handle CSV timesheet upload and processing
    """
    from custom_admin.utils import decrypt_password

    consultant = get_object_or_404(User, id=consultant_id, role='consultant')
    
    # Get consultant profile with skills
    try:
        profile = ConsultantProfile.objects.prefetch_related(
            Prefetch('skills', queryset=Skill.objects.filter(is_active=True))
        ).get(user=consultant)
        logger.info(f"ConsultantProfile found for user {consultant.email} with {profile.skills.count()} skills")
    except ConsultantProfile.DoesNotExist:
        profile = None
        logger.warning(f"ConsultantProfile does not exist for user {consultant.email}")
    
    # Handle CSV upload POST
    upload_message = None
    if request.method == 'POST' and 'timesheet_file' in request.FILES:
        csv_file = request.FILES.get('timesheet_file')
        month_str = request.POST.get('month')
        if not month_str:
            upload_message = 'Month is required for timesheet upload.'
        else:
            try:
                month = datetime.strptime(month_str, '%Y-%m')
                # Create Timesheet record
                timesheet = Timesheet.objects.create(
                    consultant=consultant,
                    month=month,
                    file=csv_file,
                    status='awaiting_review'
                )
                # No longer create TimesheetEntry records, just save CSV file
                upload_message = 'Timesheet uploaded successfully and awaiting review.'
            except Exception as e:
                upload_message = f'Error processing timesheet: {str(e)}'
                logger.error(upload_message)

    # Get related data
    invoices = Invoice.objects.filter(consultant=consultant).order_by('-month')
    timesheets = Timesheet.objects.filter(consultant=consultant).order_by('-month')
    all_skills = Skill.objects.filter(is_active=True).order_by('name')

    # Determine selected timesheet for editing entries
    selected_timesheet_id = request.GET.get('timesheet_id')
    if selected_timesheet_id:
        try:
            selected_timesheet = timesheets.get(id=selected_timesheet_id)
        except Timesheet.DoesNotExist:
            selected_timesheet = timesheets.first()
    else:
        selected_timesheet = timesheets.first()

    # Read timesheet entries from CSV file for selected timesheet
    timesheet_entries = []
    if selected_timesheet:
        try:
            csv_file = selected_timesheet.file.open('r')
            csv_data = csv_file.read()
            csv_file.close()
            f = StringIO(csv_data)
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize keys to lowercase and strip spaces for flexible matching
                normalized_row = {k.strip().lower(): v for k, v in row.items()}
                # Possible keys for task name
                task_name_keys = ['task name', 'task_name', 'task', 'name']
                task_name_value = ''
                for key in task_name_keys:
                    if key in normalized_row:
                        task_name_value = normalized_row[key]
                        break
                entry = {
                    'date': normalized_row.get('date') or normalized_row.get('date'),
                    'start_time': normalized_row.get('start time') or normalized_row.get('start_time'),
                    'end_time': normalized_row.get('end time') or normalized_row.get('end_time'),
                    'task_name': task_name_value,
                    'description': normalized_row.get('description'),
                }
                timesheet_entries.append(entry)
        except Exception as e:
            logger.error(f"Error reading timesheet CSV file: {str(e)}")

    # Editing timesheet entries is no longer supported
    upload_message_edit = None
    if request.method == 'POST' and 'edit_timesheet_entries' in request.POST:
        upload_message_edit = 'Editing timesheet entries is no longer supported.'

    # Prepare form for editing consultant profile
    form = ConsultantEditForm(instance=profile)

    # Decrypt password for display in template
    decrypted_password = ''
    try:
        if consultant.encrypted_password:
            decrypted_password = decrypt_password(consultant.encrypted_password)
    except Exception as e:
        logger.error(f"Error decrypting password for user {consultant.email}: {str(e)}")

    context = {
        'consultant': consultant,
        'profile': profile,
        'invoices': invoices,
        'timesheets': timesheets,
        'all_skills': all_skills,
        'form': form,
        'timesheet_entries': timesheet_entries,
        'selected_timesheet': selected_timesheet,
        'upload_message': upload_message,
        'upload_message_edit': upload_message_edit,
        'decrypted_password': decrypted_password,
    }
    return render(request, 'consultant_detail.html', context)


@login_required

@csrf_exempt
@require_http_methods(["GET", "POST"])
def edit_consultant(request, consultant_id):
    """
    Edit consultant profile information
    """
    user = get_object_or_404(User, id=consultant_id, role='consultant')
    
    # Get or create consultant profile
    try:
        profile = user.consultant_profile
    except ConsultantProfile.DoesNotExist:
        profile = ConsultantProfile(user=user)

    if request.method == 'POST':
        form = ConsultantEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            try:
                form.save()
                profile.save()
                logger.info(f"Consultant details updated successfully for user {user.email}")
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': 'Consultant details updated successfully.'})
                else:
                    messages.success(request, 'Consultant details updated successfully.')
                    return redirect('custom_admin:consultant_profile', consultant_id=consultant_id)
            except Exception as e:
                logger.error(f"Error saving consultant details for user {user.email}: {str(e)}")
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': 'Error saving consultant details.'}, status=500)
                else:
                    messages.error(request, 'An error occurred while saving consultant details.')
                    return redirect('custom_admin:consultant_profile', consultant_id=consultant_id)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = form.errors.as_json()
                logger.error(f"Form validation errors: {form.errors}")
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            else:
                logger.error(f"Form validation errors for user {user.email}: {form.errors}")
                messages.error(request, 'Please correct the errors below.')
                return redirect('custom_admin:consultant_profile', consultant_id=consultant_id)
    else:
        # Redirect GET requests to consultant_detail page
        logger.info(f"Redirecting GET request to consultant_profile for user {user.email}")
        return redirect('custom_admin:consultant_profile', consultant_id=consultant_id)


@login_required
@csrf_exempt
@require_POST
def update_consultant_field(request, consultant_id):
    """
    API endpoint to update a single field of consultant profile via POST JSON
    """
    try:
        user = User.objects.get(id=consultant_id, role='consultant')
        profile = user.consultant_profile
    except (User.DoesNotExist, ConsultantProfile.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'Consultant not found.'}, status=404)

    try:
        data = json.loads(request.body)
        field_name = data.get('field_name')
        field_value = data.get('field_value')

        # Validate allowed fields
        allowed_fields = [
            'bank_account_name', 'bank_account_number', 'bank_ifsc', 
            'bank_branch_name', 'bank_name', 'cost_per_hour', 'status'
        ]
        
        if field_name not in allowed_fields:
            return JsonResponse({'success': False, 'message': 'Invalid field name.'}, status=400)

        if field_name == 'status':
            from .models import ConsultantStatus
            try:
                status_instance = ConsultantStatus.objects.get(user=user)
                status_instance.status = field_value
                status_instance.save()
            except ConsultantStatus.DoesNotExist:
                status_instance = ConsultantStatus.objects.create(user=user, status=field_value)
            profile.status = status_instance
        else:
            setattr(profile, field_name, field_value)

        profile.save()
        
        return JsonResponse({'success': True, 'message': f'{field_name} updated successfully.'})
    
    except Exception as e:
        logger.error(f"Error updating consultant field: {str(e)}")
        return JsonResponse({'success': False, 'message': 'Error updating field.'}, status=500)


@login_required
@csrf_exempt
@require_POST
def delete_consultant(request, consultant_id):
    """
    Delete consultant account
    """
    try:
        consultant = User.objects.get(id=consultant_id, role='consultant')
        consultant.delete()
        logger.info(f"Consultant {consultant.email} deleted successfully")
    except User.DoesNotExist:
        return HttpResponseBadRequest("Consultant not found")

    return redirect('custom_admin:consultant_management')

@login_required
@csrf_exempt
@require_http_methods(["GET", "POST"])
def change_consultant_status(request, consultant_id):
    """
    Change consultant approval status
    """
    def is_ajax(req):
        return req.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

    try:
        consultant = User.objects.get(id=consultant_id, role='consultant')
        profile = consultant.consultant_profile
        from .models import ConsultantStatus
        status_instance, created = ConsultantStatus.objects.get_or_create(user=consultant)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Consultant not found'}, status=404)
    except ConsultantProfile.DoesNotExist:
        return JsonResponse({'error': 'Consultant profile not found'}, status=404)

    try:
        if request.method == "POST":
            new_status = request.POST.get('status')
            if new_status not in dict(ConsultantStatus.STATUS_CHOICES):
                return JsonResponse({'error': 'Invalid status value'}, status=400)
            status_instance.status = new_status
            status_instance.save()
            profile.status = status_instance
            profile.save()
            logger.info(f"Consultant {consultant.email} status changed to {new_status}")
            if is_ajax(request):
                return JsonResponse({'message': 'Status updated successfully'})
            else:
                return redirect('custom_admin:consultant_management')

        # GET request: return current status and status choices as JSON
        status_choices = ConsultantStatus.STATUS_CHOICES
        if is_ajax(request):
            return JsonResponse({
                'current_status': status_instance.status,
                'status_choices': [{'value': choice[0], 'display': choice[1]} for choice in status_choices]
            })
        else:
            return redirect('custom_admin:consultant_management')
    except Exception as e:
        logger.error(f"Exception in change_consultant_status: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
def reset_consultant_password(request, consultant_id):
    """
    Reset consultant password with encryption
    """
    from django.contrib import messages
    from django.http import HttpResponseBadRequest
    from cryptography.fernet import Fernet
    from custom_admin.utils import encrypt_password
    from django.conf import settings

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        
        if not new_password:
            messages.error(request, 'New password cannot be empty.')
            return redirect('custom_admin:admin_dashboard')
        
        try:
            consultant = User.objects.get(id=consultant_id, role='consultant')
            
            # Encrypt password using utility function
            encrypted_password = encrypt_password(new_password)
            
            consultant.encrypted_password = encrypted_password
            consultant.set_password(new_password)
            consultant.save()
            
            messages.success(request, 'Password reset successfully')
            logger.info(f"Password reset for consultant {consultant.email}")
            
            # Send email with new login credentials to consultant only (no OTP)
            email_message = (
                f"Dear {consultant.email},\n\n"
                f"Your password has been changed by the admin.\n"
                f"Your new login credentials are:\n"
                f"Email: {consultant.email}\n"
                f"Password: {new_password}\n\n"
                f"Please login using these credentials.\n\n"
                f"Regards,\n"
                f"Consultation Team"
            )
            
            send_mail(
                subject='Your Login Credentials Have Been Updated',
                message=email_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[consultant.email],
                fail_silently=False,
            )
            
            # Send internal notification email to admin about password change
            admin_email = settings.EMAIL_HOST_USER
            send_mail(
                subject='Password Changed by Admin',
                message=f'Admin has changed the password for consultant {consultant.email} (ID: {consultant.id}).',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin_email],
                fail_silently=False,
            )
            
            # Explicitly ensure no OTP is triggered here
            
        except User.DoesNotExist:
            messages.error(request, 'Consultant not found')
            
        return redirect('custom_admin:admin_dashboard')
    else:
        return HttpResponseBadRequest("Method not allowed")


# =============================================================================
# CONSULTANT REGISTRATION VIEWS
# =============================================================================

@csrf_exempt
@require_http_methods(["GET", "POST"])
def consultant_registration(request, user_id):
    """
    Handle consultant self-registration process
    """
    user = get_object_or_404(User, id=user_id, role='consultant')
    
    # Check if profile already exists
    try:
        profile = user.consultant_profile
    except ConsultantProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        form = ConsultantRegistrationForm(request.POST)
        
        if form.is_valid():
            data = form.cleaned_data
            
            # Create new profile if doesn't exist
            if not profile:
                profile = ConsultantProfile(user=user)
            
            # Create or update ConsultantStatus
            from custom_admin.models import ConsultantStatus
            consultant_status, created = ConsultantStatus.objects.get_or_create(user=user)
            consultant_status.status = 'to_be_reviewed'
            consultant_status.save()
            
            # Update all fields including name and mobile and status FK
            profile.name = data['name']
            profile.mobile = data['mobile']
            profile.bank_account_name = data['bank_account_name']
            profile.bank_account_number = data['bank_account_number']
            profile.bank_ifsc = data['bank_ifsc']
            profile.bank_branch_name = data['bank_branch_name']
            profile.bank_name = data['bank_name']
            profile.cost_per_hour = data['cost_per_hour']
            profile.status = consultant_status
            profile.save()
            
            # Set skills
            profile.skills.set(data['skills'])
            profile.save()
            
            messages.success(request, 'Registration completed successfully.')
            logger.info(f"Registration completed for user {user.email}")
                
            return redirect('registration_success')
    else:
        # Pre-populate form with user data
        initial_data = {
            'name': user.consultant_profile.name if profile else '',
            'mobile': user.consultant_profile.mobile if profile else '',
            'email': user.email,
            'agreement': True,
        }
        form = ConsultantRegistrationForm(initial=initial_data)

    return render(request, 'consultant_registration.html', {'form': form, 'user': user})


def registration_success(request):
    """
    Display registration success page
    """
    return render(request, 'registration_success.html')


# =============================================================================
# SKILLS MANAGEMENT
# =============================================================================

@login_required
def admin_skills(request):
    """
    Display and manage skills master data
    """
    skills = Skill.objects.all().order_by('name')
    return render(request, 'admin_skills.html', {
        'skills': skills, 
        'current_page': 'Skill Master'
    })


class SkillViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for managing skills with soft delete functionality
    """
    serializer_class = SkillSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        """Return only active skills"""
        return Skill.objects.filter(is_active=True)

    def create(self, request, *args, **kwargs):
        """Create new skill with error handling"""
        try:
            # Validate skill name in request data
            skill_name = request.data.get('name', '').strip()
            if not skill_name:
                return Response(
                    {'detail': 'Skill name is required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Check if skill with same name exists
            if Skill.objects.filter(name__iexact=skill_name).exists():
                return Response(
                    {'detail': 'Skill with this name already exists.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            response = super().create(request, *args, **kwargs)
            logger.info(f"Skill created successfully: {response.data}")
            return response
        except Exception as e:
            logger.error(f"Error creating skill: {str(e)}", exc_info=True)
            return Response(
                {'detail': 'Error creating skill'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """Perform soft delete instead of hard delete"""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        logger.info(f"Skill soft deleted: {instance.id}")
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# INVOICE MANAGEMENT
# =============================================================================

from custom_admin.constants import INVOICE_STATUS_CHOICES

@login_required
def admin_invoices(request):
    """
    Display invoice management interface with list of invoices
    """
    invoices = Invoice.objects.select_related('consultant').order_by('-month')
    return render(request, 'admin_invoices.html', {
        'current_page': 'Invoice Management',
        'invoices': invoices,
        'status_choices': INVOICE_STATUS_CHOICES,
    })

@login_required
@csrf_exempt
@require_POST
def update_invoice_status(request, invoice_id):
    """
    View to update the status of an invoice via AJAX POST request.
    """
    from django.http import JsonResponse
    from .models import Invoice

    try:
        invoice = Invoice.objects.get(id=invoice_id)
    except Invoice.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invoice not found.'}, status=404)

    new_status = request.POST.get('status')
    valid_statuses = ['approved', 'pending', 'rejected', 'awaiting_review']

    if new_status not in valid_statuses:
        return JsonResponse({'success': False, 'message': 'Invalid status value.'}, status=400)

    invoice.status = new_status
    invoice.save()

    return JsonResponse({'success': True, 'message': 'Invoice status updated successfully.'})
    
def consultant_autofill(request):
    """
    API endpoint for consultant autocomplete functionality
    Supports search by ID or name
    """
    query_id = request.GET.get('id', '').strip()
    query_name = request.GET.get('name', '').strip()

    results = []

    if query_id:
        consultants = User.objects.filter(
            role='consultant', 
            id__startswith=query_id
        ).values('id', 'email')[:10]
        
        results = [{'id': c['id'], 'name': c['email']} for c in consultants]
        
    elif query_name:
        consultants = User.objects.filter(
            role='consultant'
        ).filter(email__istartswith=query_name)[:10]
        
        results = [{'id': c.id, 'name': c.email} for c in consultants]

    return JsonResponse({'results': results})


@login_required
@csrf_exempt
@require_POST
def add_invoice(request):
    """
    Add new invoice for a consultant
    """
    try:
        # Extract form data
        consultant_id = request.POST.get('consultant_id')
        name = request.POST.get('name')
        month_str = request.POST.get('month')
        status = request.POST.get('status')
        invoice_file = request.FILES.get('invoice_file')

        # Validate required fields
        if not all([consultant_id, name, month_str, status, invoice_file]):
            return JsonResponse({
                'success': False, 
                'message': 'All fields are required.'
            })

        # Parse and validate month
        try:
            month = parse_date(month_str + '-01')  # Convert YYYY-MM to date
            if month is None:
                raise ValidationError('Invalid month format.')
        except ValidationError:
            return JsonResponse({
                'success': False, 
                'message': 'Invalid month format.'
            })

        # Validate consultant exists
        consultant = User.objects.filter(id=consultant_id, role='consultant').first()
        if not consultant:
            return JsonResponse({
                'success': False, 
                'message': 'Consultant not found.'
            })

        # Create invoice with transaction
        with transaction.atomic():
            invoice = Invoice.objects.create(
                consultant=consultant,
                name=name,
                month=month,
                file=invoice_file,
                status=status
            )
            
        logger.info(f"Invoice created successfully for consultant {consultant.email}")
        return JsonResponse({
            'success': True, 
            'message': 'Invoice added successfully.'
        })
        
    except Exception as e:
        logger.error(f"Error adding invoice: {str(e)}")
        return JsonResponse({
            'success': False, 
            'message': f'Error adding invoice: {str(e)}'
        })


# =============================================================================
# UTILITY VIEWS
# =============================================================================

@login_required
def consultation_list(request):
    """
    Display consultation list (redirects to consultant management)
    """
    logger.info("consultation_list view called")
    
    consultants = User.objects.filter(role='consultant').select_related('consultant_profile')
    
    context = {
        'consultants': consultants,
        'current_page': 'Consultation List',
    }
    
    logger.info(f"consultation_list rendering with {consultants.count()} consultants")
    return render(request, 'consultant_managment.html', context)


# =============================================================================
# ERROR HANDLERS AND FALLBACKS
# =============================================================================

def handle_404(request, exception):
    "Custom 404 error handler"
    return render(request, '404.html', status=404)


def handle_500(request):
    "Custom 500 error handler"
    return render(request, '500.html', status=500)


# =============================================================================
# DEPRECATED/LEGACY VIEWS
# =============================================================================

# Note: The following views might be deprecated or need refactoring
# Consider reviewing their usage and updating as needed

# TODO: Review if these views are still needed
# TODO: Add proper error handling and validation
# TODO: Consider moving to separate modules for better organization

from django.contrib.auth.decorators import user_passes_test
from consultation.models import Timesheet
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@login_required
@user_passes_test(lambda u: u.is_staff)
@csrf_exempt
@require_POST
def update_timesheet_status(request, timesheetId):
    """
    View to update the status of a timesheet via AJAX POST request.
    """
    try:
        timesheet = Timesheet.objects.get(id=timesheetId)
    except Timesheet.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Timesheet not found.'}, status=404)

    new_status = request.POST.get('status')
    valid_statuses = ['awaiting_review', 'approved', 'rejected']

    if new_status not in valid_statuses:
        return JsonResponse({'success': False, 'message': 'Invalid status value.'}, status=400)

    timesheet.status = new_status
    timesheet.save()

    return JsonResponse({'success': True, 'message': 'Timesheet status updated successfully.'})
