"""
Custom Admin Views for consultant Web Application

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
import string
import re
import logging
from datetime import datetime
from django.utils import timezone

# Django imports
from .forms import ConsultantEditForm
from general.forms import ProspectiveConsultantForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from .models import ConsultantStatus

@login_required
def admin_invoice_detail(request, invoice_id):
    """
    View to display details of a single invoice.
    """
    from .models import Invoice
    invoice = get_object_or_404(Invoice, id=invoice_id)
    context = {
        'invoice': invoice,
        'current_page': 'Invoice Detail',
    }
    return render(request, 'admin_invoice_detail.html', context)
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Timesheet, ActivityLog


from django.core.files.base import ContentFile

from django.forms import modelformset_factory
# Removed import of TimesheetEntryFormSet as it is no longer used
# from .forms import TimesheetEntryFormSet
from datetime import datetime, timedelta
# Django imports

@login_required
def timesheet(request):
    """
    View to render the timesheet page where user can select consultant, year, and month,
    and view/edit/save timesheet entries.
    """
    from consultant.models import ConsultantProfile
    from custom_admin.utils import decrypt_password
    import csv
    from io import StringIO

    consultants = User.objects.filter(role='consultant').select_related('consultant_profile').order_by('consultant_profile__name')

    # Prepare year and month options for selectors
    today = datetime.today()
    current_year = today.year
    year_options = [year for year in range(current_year - 10, current_year + 1)]
    month_options = [
        {'value': '01', 'name': 'January'},
        {'value': '02', 'name': 'February'},
        {'value': '03', 'name': 'March'},
        {'value': '04', 'name': 'April'},
        {'value': '05', 'name': 'May'},
        {'value': '06', 'name': 'June'},
        {'value': '07', 'name': 'July'},
        {'value': '08', 'name': 'August'},
        {'value': '09', 'name': 'September'},
        {'value': '10', 'name': 'October'},
        {'value': '11', 'name': 'November'},
        {'value': '12', 'name': 'December'},
    ]

    # Get selected consultant, year and month from request GET params
    consultant_id = request.GET.get('consultant_id')
    selected_year_str = request.GET.get('year') or str(current_year)
    selected_month_str = request.GET.get('month') or today.strftime('%m')

    selected_consultant = None
    timesheets = []
    selected_timesheet = None
    timesheet_entries = []

    if consultant_id:
        try:
            selected_consultant = User.objects.get(id=consultant_id, role='consultant')
            timesheets = Timesheet.objects.filter(consultant=selected_consultant).order_by('-month')

            try:
                selected_month = datetime.strptime(f"{selected_year_str}-{selected_month_str}", '%Y-%m').date()
                selected_timesheet = timesheets.filter(month__year=selected_month.year, month__month=selected_month.month).first()
            except ValueError:
                selected_timesheet = timesheets.first()
        except User.DoesNotExist:
            selected_consultant = None

    if selected_timesheet:
        try:
            with selected_timesheet.file.open('r') as csv_file:
                csv_data = csv_file.read()
            f = StringIO(csv_data)
            reader = csv.DictReader(f)
            rows_found = False
            timesheet_entries = []
            for row in reader:
                rows_found = True
                normalized_row = {k.strip().lower(): v for k, v in row.items()}
                task_name_keys = ['task name', 'task_name', 'task', 'name']
                task_name_value = ''
                for key in task_name_keys:
                    if key in normalized_row:
                        task_name_value = normalized_row[key]
                        break
                raw_date = normalized_row.get('date')
                iso_date = ''
                if raw_date:
                    try:
                        parsed_date = None
                        for fmt in ('%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y'):
                            try:
                                parsed_date = datetime.strptime(raw_date, fmt).date()
                                break
                            except ValueError:
                                continue
                        if parsed_date:
                            iso_date = parsed_date.isoformat()
                        else:
                            iso_date = raw_date
                    except Exception:
                        iso_date = raw_date
                raw_hours = normalized_row.get('hours worked')
                start_time_str = normalized_row.get('start time') or normalized_row.get('start_time')
                end_time_str = normalized_row.get('end time') or normalized_row.get('end_time')
                hours_worked = 0.0
                try:
                    if raw_hours not in (None, ''):
                        hours_worked = float(raw_hours)
                    else:
                        from datetime import datetime as dt
                        fmt_24 = '%H:%M'
                        fmt_12 = '%I:%M %p'
                        def parse_time(t):
                            for fmt in (fmt_24, fmt_12):
                                try:
                                    return dt.strptime(t, fmt)
                                except Exception:
                                    continue
                            return None
                        start_dt = parse_time(start_time_str) if start_time_str else None
                        end_dt = parse_time(end_time_str) if end_time_str else None
                        if start_dt and end_dt:
                            delta = end_dt - start_dt
                            hours_worked = delta.total_seconds() / 3600
                            if hours_worked < 0:
                                hours_worked += 24
                except (ValueError, TypeError):
                    logger.warning(f"Invalid hours_worked value '{raw_hours}' in timesheet CSV, defaulting to 0")
                    hours_worked = 0.0
                entry = {
                    'date': iso_date,
                    'start_time': start_time_str,
                    'end_time': end_time_str,
                    'project_name': normalized_row.get('project name') or normalized_row.get('project_name') or '',
                    'hours_worked': hours_worked,
                    'task_name': task_name_value,
                    'description': normalized_row.get('description'),
                }
                timesheet_entries.append(entry)
            if not rows_found:
                # Provide default sample data if CSV is empty
                timesheet_entries = [
                    {
                        'date': datetime.today().date().isoformat(),
                        'start_time': '09:00',
                        'end_time': '17:00',
                        'task_name': 'Sample Task 1',
                        'description': 'Sample description 1',
                    },
                    {
                        'date': datetime.today().date().isoformat(),
                        'start_time': '10:00',
                        'end_time': '18:00',
                        'task_name': 'Sample Task 2',
                        'description': 'Sample description 2',
                    },
                ]
        except Exception as e:
            logger.error(f"Error reading timesheet CSV file: {str(e)}")
            timesheet_entries = []
            upload_error_message = "Timesheet CSV file is missing or could not be read."
        except User.DoesNotExist:
            selected_consultant = None

    # Calculate total hours per project
    project_hours_summary = {}
    for entry in timesheet_entries:
        project = entry.get('project_name') or ''
        try:
            raw_hours = entry.get('hours_worked')
            if isinstance(raw_hours, str):
                raw_hours = raw_hours.replace(',', '').strip()
            hours = float(raw_hours) if raw_hours not in (None, '') else 0
        except (ValueError, TypeError):
            logger.warning(f"Invalid hours_worked value '{entry.get('hours_worked')}' for project '{project}', defaulting to 0")
            hours = 0
        project_hours_summary[project] = project_hours_summary.get(project, 0) + hours

    # Convert to list of dicts for template
    project_hours_list = [{'project_name': k, 'total_hours': v} for k, v in project_hours_summary.items() if k]

    context = {
        'consultants': consultants,
        'selected_consultant': selected_consultant,
        'timesheets': timesheets,
        'timesheet_entries': timesheet_entries,
        'selected_timesheet': selected_timesheet,
        'selected_year': int(selected_year_str),
        'selected_month': selected_month_str,
        'year_options': year_options,
        'month_options': month_options,
        'project_hours_summary': project_hours_list,
    }
    return render(request, 'timesheet.html', context)

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
from consultant.models import ConsultantProfile
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
    # cost_per_hour = forms.DecimalField(
    #     max_digits=10, 
    #     decimal_places=2, 
    #     label="Cost Per Hour"
    # )
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
        logger.info(f"🔥 ===== FORM SUBMISSION DEBUG =====")
        logger.info(f"📥 POST data keys: {list(request.POST.keys())}")
        logger.info(f"📥 POST data: {dict(request.POST)}")
        
        # Handle availability data specifically
        availability_data = request.POST.get('availability')
        logger.info(f"🎯 Availability data received: '{availability_data}'")
        logger.info(f"🎯 Availability data type: {type(availability_data)}")
        logger.info(f"🎯 Availability data length: {len(availability_data) if availability_data else 0}")
        
        form = ImportedConsultantEditForm(request.POST, request.FILES, instance=profile)
        logger.info(f"📝 Form fields: {list(form.fields.keys())}")
        logger.info(f"📝 Form has availability field: {'availability' in form.fields}")
        
        if form.is_valid():
            logger.info("Form is valid")
            try:
                # Save profile fields
                saved_profile = form.save()
                
                # Manually handle availability data if it's not being processed by the form
                logger.info(f"💾 Attempting to save availability data...")
                if availability_data:
                    try:
                        import json
                        import ast
                        # Validate JSON format
                        try:
                            parsed_availability = json.loads(availability_data)
                        except json.JSONDecodeError:
                            # Fallback to parse Python literal string
                            parsed_availability = ast.literal_eval(availability_data)
                        logger.info(f"✅ Parsed availability data: {parsed_availability}")
                        
                        # Check current availability before saving
                        logger.info(f"📄 Profile availability before save: {saved_profile.availability}")
                        
                        saved_profile.availability = parsed_availability
                        saved_profile.save()
                        
                        # Verify save was successful
                        saved_profile.refresh_from_db()
                        logger.info(f"📄 Profile availability after save: {saved_profile.availability}")
                        logger.info(f"✅ Availability data successfully saved to database!")
                    except Exception as e:
                        logger.error(f"❌ Error parsing or saving availability: {e}")
                else:
                    logger.warning("⚠️  No availability data received in POST request")
                
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
                            f"consultant Team"
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

                # Ensure encrypted_password is always set
                else:
                    if not user.encrypted_password or user.encrypted_password.strip() == '':
                        try:
                            from custom_admin.utils import encrypt_password
                            encrypted_password = encrypt_password(new_password)
                            user.encrypted_password = encrypted_password
                            user.save()
                            logger.info(f"Encrypted password set for user {user.email} after save")
                        except Exception as e:
                            logger.error(f"Error setting encrypted_password for user {user.email}: {str(e)}")

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
            logger.error(f"Form cleaned_data: {form.cleaned_data if hasattr(form, 'cleaned_data') else 'No cleaned_data'}")
            # Check specifically for availability field issues
            if 'availability' in form.errors:
                logger.error(f"Availability field error: {form.errors['availability']}")
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
    try:
        from django.db.models.functions import TruncMonth
        from django.db.models import Count
        from general.models import ProspectiveConsultant

        # Calculate dashboard metrics
        total_consultants = User.objects.filter(role='consultant').count()

        # Calculate pending invoices count and monthly counts for last 6 months
        pending_invoices = Invoice.objects.filter(status='awaiting_review').count()

        # Monthly counts for pending invoices for last 6 months
        from datetime import datetime, timedelta
        today = datetime.today()
        six_months_ago = today - timedelta(days=180)

        monthly_pending_invoices_qs = Invoice.objects.filter(
            status='awaiting_review',
            month__gte=six_months_ago
        ).annotate(month_only=TruncMonth('month')).values('month_only').annotate(count=Count('id')).order_by('month_only')

        monthly_pending_invoices = {entry['month_only'].strftime('%Y-%m'): entry['count'] for entry in monthly_pending_invoices_qs}

        # Calculate approved invoices count and monthly counts for last 6 months
        approved_invoices = ProspectiveConsultant.objects.count()

        monthly_approved_invoices_qs = ProspectiveConsultant.objects.filter(
            created_at__gte=six_months_ago
        ).annotate(month_only=TruncMonth('created_at')).values('month_only').annotate(count=Count('id')).order_by('month_only')

        monthly_approved_invoices = {entry['month_only'].strftime('%Y-%m'): entry['count'] for entry in monthly_approved_invoices_qs}

        # Calculate percentage changes for pending invoices and approved invoices (month over month)
        def calculate_percentage_change(data_dict):
            sorted_months = sorted(data_dict.keys())
            percentage_changes = {}
            for i in range(1, len(sorted_months)):
                prev = data_dict[sorted_months[i-1]]
                curr = data_dict[sorted_months[i]]
                if prev == 0:
                    change = 100.0 if curr > 0 else 0.0
                else:
                    change = ((curr - prev) / prev) * 100
                percentage_changes[sorted_months[i]] = round(change, 2)
            return percentage_changes

        pending_invoices_pct_change = calculate_percentage_change(monthly_pending_invoices)
        approved_invoices_pct_change = calculate_percentage_change(monthly_approved_invoices)

        # Fetch recent activities from ActivityLog (last 5) without filtering by user role (for debugging)
        recent_activities = ActivityLog.objects.order_by('-timestamp')[:5]

        # Debug logging for recent activities count and descriptions
        logger.info(f"Admin dashboard: Found {recent_activities.count()} recent activities for consultants")
        for act in recent_activities:
            logger.info(f"Activity: {act.action_type} - {act.description} - User: {act.user.email if act.user else 'None'}")

        # Prepare recent activities data for template
        activities_data = []
        for activity in recent_activities:
            icon_map = {
                'prospective_consultant': 'fa-user-plus',
                'timesheet_upload': 'fa-clock',
                'invoice_upload': 'fa-file-invoice-dollar',
                # Add more mappings as needed
            }
            icon = icon_map.get(activity.action_type, 'fa-info-circle')
            activities_data.append({
            'icon': icon,
            'description': activity.description,
            'url': activity.url,
            # Pass ISO 8601 formatted timestamp for client-side parsing
            'timestamp': activity.timestamp.isoformat(),
            'time_ago': (timezone.now() - activity.timestamp).total_seconds(),  # For possible JS formatting
        })

        context = {
            'total_consultants': total_consultants,
            'pending_invoices': pending_invoices,
            'approved_invoices': approved_invoices,
            'monthly_pending_invoices': monthly_pending_invoices,
            'monthly_approved_invoices': monthly_approved_invoices,
            'pending_invoices_pct_change': pending_invoices_pct_change,
            'approved_invoices_pct_change': approved_invoices_pct_change,
            'current_page': 'Dashboard',
            'recent_activities': activities_data,
        }
        return render(request, 'admin_dashboard.html', context)
    except Exception as e:
        logger.error(f"Error in admin_dashboard view: {str(e)}")
        from django.http import HttpResponseServerError
        return HttpResponseServerError("Internal Server Error")

@login_required
def all_activities(request):
    """
    View to display all activities with pagination (20 per page)
    """
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    activities_list = ActivityLog.objects.order_by('-timestamp')

    page = request.GET.get('page', 1)
    paginator = Paginator(activities_list, 20)  # 20 activities per page

    try:
        activities = paginator.page(page)
    except PageNotAnInteger:
        activities = paginator.page(1)
    except EmptyPage:
        activities = paginator.page(paginator.num_pages)

    # Prepare activities data for template
    activities_data = []
    icon_map = {
        'prospective_consultant': 'fa-user-plus',
        'timesheet_upload': 'fa-clock',
        'invoice_upload': 'fa-file-invoice-dollar',
        # Add more mappings as needed
    }
    for activity in activities:
        icon = icon_map.get(activity.action_type, 'fa-info-circle')
        activities_data.append({
            'icon': icon,
            'description': activity.description,
            'url': activity.url,
            'timestamp': activity.timestamp.isoformat(),
            'time_ago': (timezone.now() - activity.timestamp).total_seconds(),
        })

    context = {
        'activities': activities_data,
        'page_obj': activities,
        'paginator': paginator,
        'current_page': 'All Activities',
    }
    return render(request, 'all_activities.html', context)

# =============================================================================
# CONSULTANT MANAGEMENT VIEWS
# =============================================================================

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

@login_required
def consultant_management(request):
    """
    Display list of all consultants with their profiles, with pagination and search filter
    """
    search_query = request.GET.get('search', '').strip()
    consultants_list = User.objects.filter(role='consultant').select_related('consultant_profile')
    if search_query:
        consultants_list = consultants_list.filter(
            Q(consultant_profile__name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    consultants_list = consultants_list.order_by('consultant_profile__name')
    
    page = request.GET.get('page', 1)
    paginator = Paginator(consultants_list, 10)  # Show 10 consultants per page
    
    try:
        consultants = paginator.page(page)
    except PageNotAnInteger:
        consultants = paginator.page(1)
    except EmptyPage:
        consultants = paginator.page(paginator.num_pages)
    
    context = {
        'consultants': consultants,
        'paginator': paginator,
        'current_page': 'Consultant Management',
        'search_query': search_query,
    }
    return render(request, 'consultant_managment.html', context)

@login_required
@csrf_exempt
def add_consultant(request):
    """
    Add new consultant with email notification
    Generates random password and sends login credentials via email
    """
    from custom_admin.utils import encrypt_password
    from .models import Skill
    import json
    if request.method == 'POST':
        try:
            # Extract form data
            name = request.POST.get('name', '').strip()
            mobile = request.POST.get('mobile', '').strip()
            email = request.POST.get('email', '').strip()
            linkedin_profile = request.POST.get('linkedin_profile', '').strip()
            total_experience = request.POST.get('total_experience', '').strip()
            cost = request.POST.get('cost', '').strip()
            weekly_commitment = request.POST.get('weekly_commitment', '').strip()
            availability_raw = request.POST.get('availability', '').strip()
            agreement = request.FILES.get('agreement')

            logger.info(f"Received add_consultant POST request with name={name}, mobile={mobile}, email={email}, linkedin_profile={linkedin_profile}, total_experience={total_experience}, cost={cost}, weekly_commitment={weekly_commitment}, availability={availability_raw}, agreement={agreement}")

            # Server-side validation
            if not name:
                return JsonResponse({'success': False, 'message': 'Name is required.'})
            
            if not re.fullmatch(r'\d{10}', mobile):
                return JsonResponse({'success': False, 'message': 'Mobile number must be exactly 10 digits.'})
            
            email_regex = r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'
            if not re.fullmatch(email_regex, email, re.IGNORECASE):
                skills = Skill.objects.filter(is_active=True).order_by('name')
                return JsonResponse({'success': False, 'message': 'Invalid email address.'})

            # Check for existing user
            if User.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'message': 'User with this email already exists.'})

            # Generate random password
            autogenerated_password = ''.join(
                random.choices(string.ascii_letters + string.digits, k=10)
            )
    
            # Create new user
            new_user = User.objects.create_user(
                email=email, 
                role='consultant', 
                password=autogenerated_password
            )
            logger.info(f"Created new user with email {email}")

            # Encrypt and set encrypted_password
            encrypted_password = encrypt_password(autogenerated_password)
            new_user.encrypted_password = encrypted_password
            new_user.save()
            logger.info(f"Set encrypted_password for new user {email}")

            # Create consultant status
            from .models import ConsultantStatus
            consultant_status = ConsultantStatus.objects.create(user=new_user, status='to_be_reviewed')
            logger.info(f"Created consultant status 'to_be_reviewed' for user {email}")

            # Parse availability JSON string safely
            try:
                availability = json.loads(availability_raw) if availability_raw else None
            except json.JSONDecodeError:
                availability = None
                logger.warning(f"Invalid availability JSON: {availability_raw}")

            # Create consultant profile with all fields
            profile = ConsultantProfile(user=new_user)
            profile.name = name
            profile.mobile = mobile
            profile.linkedin_profile = linkedin_profile
            profile.total_experience = total_experience if total_experience else None
            profile.cost = cost if cost else None
            profile.weekly_commitment = weekly_commitment if weekly_commitment else None
            profile.availability = availability
            profile.status = consultant_status
            profile.cost_type = request.POST.get('cost_type', 'hourly')
            if agreement:
                profile.agreement_document = agreement
            profile.save()
            logger.info(f"Created consultant profile for user {email}")

            # Save skills ManyToMany
            skill_ids = request.POST.getlist('skills')
            if skill_ids:
                skills = Skill.objects.filter(id__in=skill_ids)
                profile.skills.set(skills)
            else:
                profile.skills.clear()
                
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
                f"consultant Team"
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

            return JsonResponse({
                'success': True,
                'message': 'Consultant added successfully and email sent.',
                'consultant': {
                    'id': new_user.id,
                    'name': profile.name,
                    'email': new_user.email,
                }
            })
        except Exception as e:  # Handle unexpected errors in the view
            logger.error(f"Error in add_consultant view: {str(e)}")
            return JsonResponse({'success': False, 'message': 'An unexpected error occurred.'})
    else:
        # Handle GET request - render add consultant form
        skills = Skill.objects.filter(is_active=True).order_by('name')
        return render(request, 'add_consultant.html', {'current_page': 'Add Consultant', 'skills': skills})

@login_required
def consultant_profile(request, consultant_id):
    """
    Display detailed consultant profile with invoices, timesheets, and timesheet entries
    Also handle CSV timesheet upload and processing
    """
    from custom_admin.utils import decrypt_password
    from django.http import HttpResponseServerError

    try:
        consultant = get_object_or_404(User, id=consultant_id, role='consultant')
        
        # Log encrypted_password for debugging
        logger.info(f"Encrypted password for user {consultant.email}: {consultant.encrypted_password}")

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
        form = ConsultantEditForm(instance=profile, initial={'skills': profile.skills.all()})
        form.fields['skills'].queryset = Skill.objects.filter(is_active=True).order_by('name')

        # Populate initial_skill_experiences for the form
        from consultant.models import ConsultantSkillExperience
        skill_experiences = ConsultantSkillExperience.objects.filter(consultant_profile=profile)
        initial_skill_experiences = []
        for se in skill_experiences:
            initial_skill_experiences.append({
                'skill_id': se.skill.id,
                'experience_years': float(se.experience_years) if se.experience_years else None,
            })
        form.initial_skill_experiences = initial_skill_experiences

        # Debug logging to verify data consistency
        logger.info(f"ConsultantProfile ID: {profile.id} for user {profile.user.email}")
        logger.info(f"Skill experiences count: {len(initial_skill_experiences)}")
        for se in initial_skill_experiences:
            logger.info(f"Skill ID: {se['skill_id']}, Experience: {se['experience_years']}")

        # Decrypt password for display in template
        decrypted_password = ''
        try:
            if consultant.encrypted_password:
                decrypted_password = decrypt_password(consultant.encrypted_password)
                logger.info(f"Decrypted password for user {consultant.email}: {decrypted_password}")
            else:
                logger.warning(f"No encrypted_password set for user {consultant.email}")
                decrypted_password = '[Password not set]'
        except Exception as e:
            logger.error(f"Error decrypting password for user {consultant.email}: {str(e)}")
            decrypted_password = '[Error decrypting password]'
        logger.debug(f"Final decrypted_password value for user {consultant.email}: {decrypted_password}")

        # Debug availability data for template
        logger.info(f"🎯 DEBUG: Profile availability for template: {profile.availability}")
        logger.info(f"🎯 DEBUG: Availability type: {type(profile.availability)}")
        
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
            'skill_experiences': json.dumps(initial_skill_experiences),
        }
        return render(request, 'consultant_detail.html', context)
    except Exception as e:
        logger.error(f"Exception in consultant_profile view: {str(e)}", exc_info=True)
        return HttpResponseServerError("Internal Server Error")


@login_required
@csrf_exempt
@require_http_methods(["GET", "POST"])
def edit_consultant(request, consultant_id):
    """
    Edit consultant profile information, including password change with email notification
    """
    user = get_object_or_404(User, id=consultant_id, role='consultant')
    logger.info(f"Editing consultant with id: {consultant_id}, user id: {user.id}, email: {user.email}")
    
    # Get or create consultant profile
    try:
        profile = user.consultant_profile
        logger.info(f"Consultant profile found for user {user.email}")
    except ConsultantProfile.DoesNotExist:
        profile = ConsultantProfile(user=user)
        logger.info(f"Consultant profile created for user {user.email}")

    if request.method == 'POST':
        form = ConsultantEditForm(request.POST, request.FILES, instance=profile)
        logger.info(f"Received POST data: {request.POST}")
        logger.info(f"Form fields: {form.fields.keys()}")
        if form.is_valid():
            logger.info("Form is valid")
            try:
                instance = form.save(commit=False)
                # Save cost_type from POST data explicitly
                cost_type = request.POST.get('cost_type')
                if cost_type in ['hourly', 'monthly']:
                    instance.cost_type = cost_type
                instance.save()
                form.save_m2m()

                # Process skills_data from POST
                skills_data_json = request.POST.get('skills_data', '[]')
                import json
                try:
                    skills_data = json.loads(skills_data_json)
                except json.JSONDecodeError:
                    skills_data = []
                    logger.error(f"Invalid skills_data JSON for user {user.email}: {skills_data_json}")

                # Current skill ids submitted
                submitted_skill_ids = set()
                for skill_entry in skills_data:
                    skill_id = skill_entry.get('skill_id')
                    experience_years = skill_entry.get('experience_years')
                    if skill_id is None:
                        continue
                    submitted_skill_ids.add(int(skill_id))
                    # Update or create ConsultantSkillExperience
                    try:
                        from consultant.models import ConsultantSkillExperience
                        from custom_admin.models import Skill
                        skill_obj = Skill.objects.get(id=skill_id)
                        cse, created = ConsultantSkillExperience.objects.update_or_create(
                            consultant_profile=instance,
                            skill=skill_obj,
                            defaults={'experience_years': experience_years}
                        )
                    except Skill.DoesNotExist:
                        logger.error(f"Skill with id {skill_id} does not exist for user {user.email}")

                # Remove ConsultantSkillExperience not in submitted skills
                from consultant.models import ConsultantSkillExperience
                ConsultantSkillExperience.objects.filter(
                    consultant_profile=instance
                ).exclude(
                    skill_id__in=submitted_skill_ids
                ).delete()

                new_password = form.cleaned_data.get('password')
                logger.info(f"Password field value: {new_password}")
                if new_password:
                    try:
                        from custom_admin.utils import encrypt_password
                        encrypted_password = encrypt_password(new_password)
                        user.encrypted_password = encrypted_password
                        user.set_password(new_password)
                        user.save()
                        logger.info(f"User password updated and encrypted_password set for user {user.email}")

                        from django.conf import settings
                        email_message = (
                            f"Dear {user.email},\n\n"
                            f"Your password has been changed by the admin.\n"
                            f"Your new login credentials are:\n"
                            f"Email: {user.email}\n"
                            f"Password: {new_password}\n\n"
                            f"Please login using these credentials.\n\n"
                            f"Regards,\n"
                            f"consultant Team"
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
                logger.error(f"Form validation errors: {form.errors}")
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            else:
                logger.error(f"Form validation errors for user {user.email}: {form.errors}")
                messages.error(request, 'Please correct the errors below.')
                return redirect('custom_admin:consultant_profile', consultant_id=consultant_id)
    else:
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
    logger.info(f"change_consultant_status called with method={request.method} and consultant_id={consultant_id}")
    def is_ajax(req):
        return req.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

    try:
        consultant = User.objects.get(id=consultant_id, role='consultant')
        profile = consultant.consultant_profile
        from .models import ConsultantStatus
        status_instance, created = ConsultantStatus.objects.get_or_create(user=consultant)
    except User.DoesNotExist:
        logger.error(f"Consultant with id {consultant_id} not found")
        return JsonResponse({'error': 'Consultant not found'}, status=404)
    except ConsultantProfile.DoesNotExist:
        logger.error(f"Consultant profile for user id {consultant_id} not found")
        return JsonResponse({'error': 'Consultant profile not found'}, status=404)

    try:
        if request.method == "POST":
            new_status = request.POST.get('status')
            if new_status not in dict(ConsultantStatus.STATUS_CHOICES):
                logger.error(f"Invalid status value received: {new_status}")
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
            logger.info(f"Returning status choices for consultant {consultant.email}")
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
                f"consultant Team"
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
            # profile.cost_per_hour = data['cost_per_hour']
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

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

@login_required
def admin_invoices(request):
    """
    Display invoice management interface with list of invoices with pagination and filtering by month and consultant name
    """
    from django.db.models import Q
    invoices_list = Invoice.objects.select_related('consultant').order_by('-month')

    # Get filter parameters from GET request
    filter_month = request.GET.get('month', '').strip()
    filter_name = request.GET.get('name', '').strip()

    # Filter by month if provided (expecting format 'YYYY-MM')
    if filter_month:
        try:
            year, month = map(int, filter_month.split('-'))
            invoices_list = invoices_list.filter(month__year=year, month__month=month)
        except ValueError:
            pass  # Ignore invalid month format

    # Filter by consultant name or email if provided
    if filter_name:
        invoices_list = invoices_list.filter(
            Q(consultant__consultant_profile__name__icontains=filter_name) |
            Q(consultant__email__icontains=filter_name)
        )

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(invoices_list, 10)  # Show 10 invoices per page

    try:
        invoices = paginator.page(page)
    except PageNotAnInteger:
        invoices = paginator.page(1)
    except EmptyPage:
        invoices = paginator.page(paginator.num_pages)

    return render(request, 'admin_invoices.html', {
        'current_page': 'Invoice Management',
        'invoices': invoices,
        'status_choices': INVOICE_STATUS_CHOICES,
        'paginator': paginator,
        'filter_month': filter_month,
        'filter_name': filter_name,
    })

@login_required
@csrf_exempt
@require_POST
def edit_invoice(request, invoice_id):
    """
    Edit invoice file by replacing the existing file
    """
    try:
        invoice = Invoice.objects.get(id=invoice_id)
    except Invoice.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invoice not found.'}, status=404)

    if 'invoice_file' not in request.FILES:
        return JsonResponse({'success': False, 'message': 'No file uploaded.'}, status=400)

    invoice_file = request.FILES['invoice_file']
    invoice.file.delete(save=False)  # Delete old file
    invoice.file = invoice_file
    invoice.save()

    # Return new file name and URL for UI update
    return JsonResponse({
        'success': True,
        'message': 'Invoice updated successfully.',
        'file_name': invoice.name,
        'file_url': invoice.file.url,
    })

from django.http import JsonResponse, HttpResponseForbidden

@login_required
@csrf_exempt
@require_POST
def delete_invoice(request, invoice_id):
    """
    Delete an invoice
    """
    if not (request.user.is_staff or getattr(request.user, 'role', None) == 'admin'):
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)

    try:
        invoice = Invoice.objects.get(id=invoice_id)
    except Invoice.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invoice not found.'}, status=404)

    invoice.file.delete(save=False)
    invoice.delete()

    return JsonResponse({'success': True, 'message': 'Invoice deleted successfully.'})

@login_required
@csrf_exempt
@require_POST
def update_invoice_status(request, invoice_id):
    """
    View to update the status of an invoice via AJAX POST request.
    Sends email notification to consultant on status change.
    """
    from django.http import JsonResponse
    from .models import Invoice
    from django.core.mail import send_mail
    from django.conf import settings
    import logging

    logger = logging.getLogger(__name__)

    try:
        invoice = Invoice.objects.get(id=invoice_id)
    except Invoice.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invoice not found.'}, status=404)

    from custom_admin.constants import INVOICE_STATUS_CHOICES

    new_status = request.POST.get('status')
    valid_statuses = [choice[0] for choice in INVOICE_STATUS_CHOICES]

    if new_status not in valid_statuses:
        return JsonResponse({'success': False, 'message': 'Invalid status value.'}, status=400)

    invoice.status = new_status
    invoice.save()

    # Send email notification to consultant
    try:
        logger.info(f"Preparing to send invoice status update email to {invoice.consultant.email} for invoice {invoice.id}")
        subject = f"Invoice Status Updated: {invoice.name}"
        message = (
            f"Dear {invoice.consultant.consultant_profile.name or invoice.consultant.email},\n\n"
            f"The status of your invoice '{invoice.name}' for {invoice.month.strftime('%B %Y')} has been updated to '{new_status}'.\n\n"
            f"Please log in to your account to view more details.\n\n"
            f"Regards,\n"
            f"Consultant Team"
        )
        recipient_list = [invoice.consultant.email]
        logger.info(f"Email details - Subject: {subject}, Recipients: {recipient_list}, Message: {message}")
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com'),
            recipient_list=recipient_list,
            fail_silently=False,
        )
        logger.info(f"Invoice status update email sent to {invoice.consultant.email} for invoice {invoice.id}")
    except Exception as e:
        logger.error(f"Failed to send invoice status update email for invoice {invoice.id}: {str(e)}")

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
def consultant_list(request):
    """
    Display consultant list (redirects to consultant management)
    """
    logger.info("consultant_list view called")
    
    consultants = User.objects.filter(role='consultant').select_related('consultant_profile')
    
    context = {
        'consultants': consultants,
        'current_page': 'consultant List',
    }
    
    logger.info(f"consultant_list rendering with {consultants.count()} consultants")
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
from consultant.models import Timesheet
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

from .forms import AdminProfileForm

def admin_profile(request, admin_id):
    """View and edit admin profile."""
    try:
        admin_user = User.objects.get(id=admin_id, is_staff=True)
    except User.DoesNotExist:
        logger.error(f"Admin user with id {admin_id} not found")
        raise Http404("Admin user not found")

    if request.method == 'POST':
        if 'scrap_agreement' in request.POST:
            return _handle_scrap_agreement(request, admin_user)
        
        # Handle profile update
        form = AdminProfileForm(request.POST, request.FILES, instance=admin_user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Admin profile updated successfully.')
            return redirect('custom_admin:admin_profile', admin_id=admin_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AdminProfileForm(instance=admin_user)

    # Decrypt password if exists
    decrypted_password = None
    if hasattr(admin_user, 'encrypted_password') and admin_user.encrypted_password:
        try:
            decrypted_password = decrypt_password(admin_user.encrypted_password)
        except Exception as e:
            logger.error(f"Error decrypting password for user {admin_user.email}: {str(e)}")

    context = {
        'admin_user': admin_user,
        'form': form,
        'current_page': 'Admin Profile',
        'decrypted_password': decrypted_password,
    }
    return render(request, 'admin_profile.html', context)

@require_http_methods(["GET", "POST"])
def new_consultant_details(request):
    from custom_admin.models import ActivityLog
    from custom_admin.models import Skill
    if request.method == "POST":
        form = ProspectiveConsultantForm(request.POST)
        if form.is_valid():
            prospective_consultant = form.save()

            # Send email notification to original email and all superadmin/admin users
            from django.core.mail import send_mail
            from custom_admin.models import User

            subject = "New Prospective Consultant Request"
            message = (
                f"New prospective consultant request received:\n\n"
                f"Name: {prospective_consultant.name}\n"
                f"Email: {prospective_consultant.email}\n"
                f"Phone: {prospective_consultant.phone}\n"
                f"Consultant Field: {prospective_consultant.skills}\n"
                f"LinkedIn Profile: {prospective_consultant.linkedin}\n"
            )
            # Original email used for credentials (assuming settings.DEFAULT_FROM_EMAIL)
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
            recipient_list = []

            if from_email:
                recipient_list.append(from_email)

            # Add all superadmin/admin emails
            admin_users = User.objects.filter(role__in=['superadmin', 'admin'], is_active=True)
            admin_emails = [user.email for user in admin_users if user.email]
            recipient_list.extend(admin_emails)

            # Remove duplicates
            recipient_list = list(set(recipient_list))
            
            # Add the specific email for confirmation
            recipient_list.append("chaturvedi1ayush@gmail.com")
            recipient_list = list(set(recipient_list))  # Remove duplicates again

            if recipient_list:
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)

            from django.urls import reverse
            # Create ActivityLog entry for prospective consultant submission
            # Only create ActivityLog if user is authenticated
            if request.user.is_authenticated:
                ActivityLog.objects.create(
                    user=request.user,
                    action_type='prospective_consultant',
                    description=f"New prospective consultant submitted: {prospective_consultant.name} ({prospective_consultant.email})",
                    content_object=prospective_consultant,
                    url=reverse('custom_admin:prospective_consultant_detail', args=[prospective_consultant.id])
                )

            messages.success(request, "Your prospective consultant request has been submitted successfully.")
            return redirect('landing_page')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProspectiveConsultantForm()
        form.fields['skills'].queryset = Skill.objects.filter(is_active=True).order_by('name')
    return render(request, 'new_consultant_details.html', {'form': form, 'user': request.user if request.user.is_authenticated else None})

@login_required
def prospective_consultants_management(request):
    """
    View to list all prospective consultants in the custom admin interface with pagination.
    """
    from general.models import ProspectiveConsultant
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    prospective_consultants_list = ProspectiveConsultant.objects.all().order_by('-created_at')
    page = request.GET.get('page', 1)
    paginator = Paginator(prospective_consultants_list, 10)  # 10 per page

    try:
        prospective_consultants = paginator.page(page)
    except PageNotAnInteger:
        prospective_consultants = paginator.page(1)
    except EmptyPage:
        prospective_consultants = paginator.page(paginator.num_pages)

    context = {
        'prospective_consultants': prospective_consultants,
        'paginator': paginator,
        'current_page': 'Prospective Consultants Management',
    }
    return render(request, 'prospective_consultants.html', context)

@login_required
def prospective_consultant_detail(request, prospective_consultant_id):
    """
    View to show detailed information of a single prospective consultant.
    """
    from general.models import ProspectiveConsultant
    prospective_consultant = get_object_or_404(ProspectiveConsultant, id=prospective_consultant_id)
    context = {
        'prospective_consultant': prospective_consultant,
        'current_page': 'Prospective Consultant Detail',
    }
    return render(request, 'prospective_consultant_detail.html', context)

@login_required
@csrf_exempt
@require_POST
def delete_prospective_consultant(request, prospective_consultant_id):
    """
    Delete a prospective consultant by ID.
    """
    from general.models import ProspectiveConsultant
    try:
        prospective_consultant = ProspectiveConsultant.objects.get(id=prospective_consultant_id)
        prospective_consultant.delete()
        return JsonResponse({'success': True, 'message': 'Prospective consultant deleted successfully.'})
    except ProspectiveConsultant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Prospective consultant not found.'}, status=404)

