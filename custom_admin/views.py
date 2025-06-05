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
import string
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

    return JsonResponse({'success': True, 'message': 'Timesheet status updated successfully.'})
from django import forms
from django.conf import settings

# Third-party imports
from cryptography.fernet import Fernet
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
import openpyxl

# Local imports
from .models import User, Skill, Invoice, SessionBooking, Timesheet
from consultation.models import ConsultantProfile
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
        
from django import forms

class ConsultantEditForm(forms.ModelForm):
    """Form for editing consultant profile information"""
    
    from .models import ConsultantStatus
    status = forms.ChoiceField(
        choices=ConsultantStatus.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = ConsultantProfile
        fields = [
            'name',
            'mobile',
            'bank_account_name',
            'bank_account_number', 
            'bank_ifsc',
            'bank_branch_name',
            'bank_name',
            'cost_per_hour',
            'skills',
            'status',
            'agreement_document',
            'details',
        ]
    
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(), 
        widget=forms.CheckboxSelectMultiple
    )
    agreement_document = forms.FileField(required=False)
    details = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial status value as string
        if 'instance' in kwargs and kwargs['instance'] is not None:
            status_value = getattr(kwargs['instance'], 'status', None)
            if status_value is not None:
                self.fields['status'].initial = status_value
            else:
                self.fields['status'].initial = 'to_be_reviewed'
        else:
            self.fields['status'].initial = 'to_be_reviewed'

    def save(self, commit=True):
        instance = super().save(commit=False)
        from .models import ConsultantStatus
        status_value = self.cleaned_data.get('status')
        if status_value:
            try:
                status_instance = ConsultantStatus.objects.get(user=instance.user)
                status_instance.status = status_value
                status_instance.save()
                instance.status = status_instance
            except ConsultantStatus.DoesNotExist:
                status_instance = ConsultantStatus.objects.create(user=instance.user, status=status_value)
                instance.status = status_instance
        if commit:
            instance.save()
            self.save_m2m()
        return instance

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
            
            # Agreement is optional for now, so skip validation
            # if not agreement:
            #     logger.warning("Agreement PDF is required.")
            #     return JsonResponse({'success': False, 'message': 'Agreement PDF is required.'})
            
            # if not agreement.name.lower().endswith('.pdf'):
            #     logger.warning("Agreement must be a PDF file.")
            #     return JsonResponse({'success': False, 'message': 'Agreement must be a PDF file.'})

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
    Also handle Excel timesheet upload and processing
    """
    from django.core.serializers.json import DjangoJSONEncoder
    import json
    from django.db.models import Prefetch
    from datetime import datetime
    import openpyxl

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
    
    # Handle Excel upload POST
    upload_message = None
    if request.method == 'POST' and 'timesheet_file' in request.FILES:
        excel_file = request.FILES.get('timesheet_file')
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
                    file=excel_file,
                    status='awaiting_review'
                )
                # Process Excel and create TimesheetEntry records
                wb = openpyxl.load_workbook(timesheet.file)
                sheet = wb.active
                header = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
                expected_headers = ['Date', 'Start Time', 'End Time']
                if header != expected_headers:
                    upload_message = f'Invalid Excel format. Expected headers: {expected_headers}'
                else:
                    entries = []
                    for row in sheet.iter_rows(min_row=2, values_only=True):
                        date_val, start_time, end_time = row
                        if not date_val or not start_time or not end_time:
                            continue
                        if isinstance(date_val, str):
                            try:
                                date_val = datetime.strptime(date_val, '%Y-%m-%d').date()
                            except ValueError:
                                continue
                        elif isinstance(date_val, datetime):
                            date_val = date_val.date()

                        def time_to_decimal(t):
                            if isinstance(t, datetime):
                                return t.hour + t.minute / 60
                            elif isinstance(t, str):
                                try:
                                    dt = datetime.strptime(t, '%H:%M')
                                    return dt.hour + dt.minute / 60
                                except ValueError:
                                    return None
                            elif isinstance(t, (int, float)):
                                return t * 24
                            return None

                        start_decimal = time_to_decimal(start_time)
                        end_decimal = time_to_decimal(end_time)
                        if start_decimal is None or end_decimal is None or end_decimal <= start_decimal:
                            continue
                        hours_worked = end_decimal - start_decimal

                        entry = TimesheetEntry(
                            timesheet=timesheet,
                            date=date_val,
                            hours_worked=hours_worked,
                            project='',
                            description=f'Free time from {start_time} to {end_time}'
                        )
                        entries.append(entry)

                    TimesheetEntry.objects.bulk_create(entries)
                    upload_message = f'Timesheet uploaded successfully with {len(entries)} entries.'
            except Exception as e:
                upload_message = f'Error processing timesheet: {str(e)}'
                logger.error(upload_message)

    # Get related data
    invoices = Invoice.objects.filter(consultant=consultant).order_by('-month')
    # Fetch all timesheets regardless of status for calendar display and history
    timesheets = Timesheet.objects.filter(consultant=consultant).order_by('-month')
    all_skills = Skill.objects.filter(is_active=True).order_by('name')

    # Get timesheet entries for all timesheets of this consultant
    timesheet_entries_qs = TimesheetEntry.objects.filter(timesheet__in=timesheets).order_by('date')
    timesheet_entries = list(timesheet_entries_qs.values('date', 'hours_worked', 'description'))

    # Prepare form for editing consultant profile
    form = ConsultantEditForm(instance=profile)

    context = {
        'consultant': consultant,
        'profile': profile,
        'invoices': invoices,
        'timesheets': timesheets,
        'all_skills': all_skills,
        'form': form,
        'timesheet_entries': json.dumps(timesheet_entries, cls=DjangoJSONEncoder),
        'upload_message': upload_message,
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
@require_POST
def change_consultant_status(request, consultant_id):
    """
    Change consultant approval status
    """
    new_status = request.POST.get('status')
    
    if new_status not in ['approved', 'rejected', 'to_be_reviewed']:
        return HttpResponseBadRequest("Invalid status value")

    try:
        consultant = User.objects.get(id=consultant_id, role='consultant')
        profile = consultant.consultant_profile
        profile.status = new_status
        profile.save()
        logger.info(f"Consultant {consultant.email} status changed to {new_status}")
    except User.DoesNotExist:
        return HttpResponseBadRequest("Consultant not found")
    except ConsultantProfile.DoesNotExist:
        return HttpResponseBadRequest("Consultant profile not found")

    return redirect('custom_admin:consultant_managment')


@login_required
def reset_consultant_password(request, consultant_id):
    """
    Reset consultant password with encryption
    """
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        
        try:
            consultant = User.objects.get(id=consultant_id, role='consultant')
            
            # Generate encryption key and encrypt password
            FERNET_KEY = Fernet.generate_key()
            fernet = Fernet(FERNET_KEY)
            encrypted_password = fernet.encrypt(new_password.encode()).decode()
            
            consultant.encrypted_password = encrypted_password
            consultant.save()
            
            messages.success(request, 'Password reset successfully')
            logger.info(f"Password reset for consultant {consultant.email}")
            
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

@login_required
def admin_invoices(request):
    """
    Display invoice management interface
    """
    return render(request, 'admin_invoices.html', {
        'current_page': 'Invoice Management'
    })
    
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
from consultation.models import TimesheetEntry, Timesheet
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
