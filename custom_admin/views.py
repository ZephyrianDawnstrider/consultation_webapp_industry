from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django import forms
from .models import User, Skill, ConsultantProfile
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from cryptography.fernet import Fernet

import logging
import datetime
import openpyxl
from django.core.mail import send_mail
from rest_framework import viewsets, permissions
from .serializers import SkillSerializer

logger = logging.getLogger(__name__)

class ConsultantRegistrationForm(forms.Form):
    name = forms.CharField(max_length=255)
    mobile = forms.CharField(max_length=20)
    email = forms.EmailField()
    agreement = forms.BooleanField()
    bank_account_name = forms.CharField(max_length=255)
    bank_account_number = forms.CharField(max_length=50)
    bank_ifsc = forms.CharField(max_length=20)
    bank_branch_name = forms.CharField(max_length=255)
    bank_name = forms.CharField(max_length=255)
    cost_per_hour = forms.DecimalField(max_digits=10, decimal_places=2)
    skills = forms.ModelMultipleChoiceField(queryset=None, widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['skills'].queryset = Skill.objects.all()

@csrf_exempt
@require_http_methods(["GET", "POST"])
def consultant_registration(request, user_id):
    user = get_object_or_404(User, id=user_id, role='consultant')
    try:
        profile = user.consultant_profile
    except ConsultantProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        form = ConsultantRegistrationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if not profile:
                profile = ConsultantProfile(user=user)
            profile.bank_account_name = data['bank_account_name']
            profile.bank_account_number = data['bank_account_number']
            profile.bank_ifsc = data['bank_ifsc']
            profile.bank_branch_name = data['bank_branch_name']
            profile.bank_name = data['bank_name']
            profile.cost_per_hour = data['cost_per_hour']
            profile.status = 'to_be_reviewed'
            profile.save()
            profile.skills.set(data['skills'])
            profile.save()
            messages.success(request, 'Registration completed successfully.')
            return redirect('registration_success')
    else:
        initial_data = {
            'name': user.email,
            'mobile': '',  # Could be added to User model if needed
            'email': user.email,
            'agreement': True,
        }
        form = ConsultantRegistrationForm(initial=initial_data)

    return render(request, 'consultant_registration.html', {'form': form, 'user': user})

def registration_success(request):
    return render(request, 'registration_success.html')

from rest_framework.response import Response
from rest_framework import status

import logging

logger = logging.getLogger(__name__)

class SkillViewSet(viewsets.ModelViewSet):
    serializer_class = SkillSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        # Return only active skills
        return Skill.objects.filter(is_active=True)

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            logger.info(f"Skill created successfully: {response.data}")
            return response
        except Exception as e:
            logger.error(f"Error creating skill: {str(e)}", exc_info=True)
            return Response({'detail': 'Error creating skill'}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        # Override destroy to perform soft delete
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        logger.info(f"Skill soft deleted: {instance.id}")
        return Response(status=status.HTTP_204_NO_CONTENT)

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        logger.info(f"Login attempt for email: {email}")
        try:
            user = User.objects.get(email=email)
            logger.info(f"User found: {user.email} with role {user.role}")
        except User.DoesNotExist:
            logger.warning(f"Login failed: User with email {email} does not exist")
            messages.error(request, 'Invalid email or password')
            return redirect('login')

        if user.role == 'admin':
            from django.contrib.auth import authenticate, login
            user_auth = authenticate(request, username=email, password=password)
            if user_auth is not None:
                logger.info(f"Admin user {email} authenticated successfully.")
                login(request, user_auth)
                return redirect('admin_dashboard')
            else:
                logger.warning(f"Admin user {email} failed authentication.")
                messages.error(request, 'Invalid email or password')
                return redirect('login')
        elif user.role == 'consultant':
            if user.check_consultant_password(password):
                from django.contrib.auth import login
                login(request, user)
                logger.info(f"Consultant user {email} logged in successfully.")
                return redirect('consultant_dashboard')
            else:
                logger.warning(f"Consultant user {email} failed password check.")
                messages.error(request, 'Invalid email or password')
                return redirect('login')
        else:
            logger.warning(f"User {email} has unknown role {user.role}")
        # Added fallback return for POST requests that don't match above conditions
        return render(request, 'landingpage.html')
    else:
        return render(request, 'landingpage.html')

from django.contrib.auth.decorators import login_required

from django.db.models import Count
from .models import Invoice, SessionBooking
from django.contrib.auth.decorators import login_required

@login_required
def admin_dashboard(request):
    total_consultants = User.objects.filter(role='consultant').count()
    pending_invoices = Invoice.objects.filter(status='pending').count()
    approved_sessions = SessionBooking.objects.count()  # Assuming all sessions are approved

    context = {
        'total_consultants': total_consultants,
        'pending_invoices': pending_invoices,
        'approved_sessions': approved_sessions,
        'current_page': 'Dashboard',
    }
    return render(request, 'admin_dashboard.html', context)

from .models import Skill

@login_required
def admin_skills(request):
    skills = Skill.objects.all().order_by('name')
    return render(request, 'admin_skills.html', {'skills': skills, 'current_page': 'Skill Master'})

@login_required
def consultant_management(request):
    # Query all users with role 'consultant' and prefetch related ConsultantProfile
    consultants = User.objects.filter(role='consultant').select_related('consultant_profile')
    context = {
        'consultants': consultants,
        'current_page': 'Consultant Management',
    }
    return render(request, 'consultant_managment.html', context)

@login_required
def admin_invoices(request):
    return render(request, 'admin_invoices.html', {'current_page': 'Invoice Management'})

from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
import re

@login_required
@csrf_exempt
def add_consultant(request):
    import random
    import string
    from django.contrib.auth.hashers import make_password

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        mobile = request.POST.get('mobile', '').strip()
        email = request.POST.get('email', '').strip()
        agreement = request.FILES.get('agreement')

        # Server-side validation
        if not name:
            return JsonResponse({'success': False, 'message': 'Name is required.'})
        if not re.fullmatch(r'\d{10}', mobile):
            return JsonResponse({'success': False, 'message': 'Mobile number must be exactly 10 digits.'})
        email_regex = r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'
        if not re.fullmatch(email_regex, email, re.IGNORECASE):
            return JsonResponse({'success': False, 'message': 'Invalid email address.'})
        if not agreement:
            return JsonResponse({'success': False, 'message': 'Agreement PDF is required.'})
        if not agreement.name.lower().endswith('.pdf'):
            return JsonResponse({'success': False, 'message': 'Agreement must be a PDF file.'})

        # Check if user with email already exists
        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': 'User with this email already exists.'})

        # Generate a random password
        autogenerated_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

        # Create new user with encrypted password using UserManager.create_user
        new_user = User.objects.create_user(email=email, role='consultant', password=autogenerated_password)

        # TODO: Save consultant profile or other related data if needed

        # Send email to the entered email address with login details
        login_url = request.build_absolute_uri('/auth/login/')
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
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'no-reply@example.com',
                recipient_list=[email],
                fail_silently=False,
            )
            logger.info(f"Registration email sent to {email}")
        except Exception as e:
            logger.error(f"Error sending registration email to {email}: {str(e)}")
            return JsonResponse({'success': False, 'message': f'Error sending email: {str(e)}'})

        return JsonResponse({'success': True, 'message': 'Consultant added successfully and email sent.'})
    else:
        return render(request, 'add_consultant.html', {'current_page': 'Add Consultant'})

@login_required
def consultation_list(request):
    logger.info("consultation_list view called")
    # Render consultant management page instead of consultation_list.html
    consultants = User.objects.filter(role='consultant').select_related('consultant_profile')
    context = {
        'consultants': consultants,
        'current_page': 'Consultation List',
    }
    logger.info(f"consultation_list rendering with {consultants.count()} consultants")
    return render(request, 'consultant_managment.html', context)

@login_required
def consultant_profile(request, consultant_id):
    consultant = get_object_or_404(User, id=consultant_id, role='consultant')
    return render(request, 'consultant_profile.html', {'consultant': consultant})

@login_required
def reset_consultant_password(request, consultant_id):
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        try:
            consultant = User.objects.get(id=consultant_id, role='consultant')
            from cryptography.fernet import Fernet
            FERNET_KEY = Fernet.generate_key()
            fernet = Fernet(FERNET_KEY)
            encrypted_password = fernet.encrypt(new_password.encode()).decode()
            consultant.encrypted_password = encrypted_password
            consultant.save()
            messages.success(request, 'Password reset successfully')
        except User.DoesNotExist:
            messages.error(request, 'Consultant not found')
        return redirect('admin_dashboard')
    else:
        return HttpResponse(status=405)  # Method not allowed

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.shortcuts import redirect

from django.views.decorators.http import require_POST
from django.http import HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404

@login_required
@csrf_exempt
@require_POST
def delete_consultant(request, consultant_id):
    try:
        consultant = User.objects.get(id=consultant_id, role='consultant')
        consultant.delete()
        # Optionally, add messages or logging here
    except User.DoesNotExist:
        return HttpResponseBadRequest("Consultant not found")

    return redirect('consultant_management')

@login_required
@csrf_exempt
@require_POST
def change_consultant_status(request, consultant_id):
    new_status = request.POST.get('status')
    if new_status not in ['approved', 'rejected', 'to_be_reviewed']:
        return HttpResponseBadRequest("Invalid status value")

    try:
        consultant = User.objects.get(id=consultant_id, role='consultant')
        profile = consultant.consultant_profile
        profile.status = new_status
        profile.save()
        # Optionally, add messages or logging here
    except User.DoesNotExist:
        return HttpResponseBadRequest("Consultant not found")
    except ConsultantProfile.DoesNotExist:
        return HttpResponseBadRequest("Consultant profile not found")

    return redirect('consultant_management')

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_date
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Invoice

User = get_user_model()

# API view to get consultant data for autofill
def consultant_autofill(request):
    query_id = request.GET.get('id', '').strip()
    query_name = request.GET.get('name', '').strip()

    if query_id:
        consultants = User.objects.filter(role='consultant', id__startswith=query_id).values('id', 'email')[:10]
        results = []
        for c in consultants:
            results.append({'id': c['id'], 'name': c['email']})
        return JsonResponse({'results': results})

    if query_name:
        consultants = User.objects.filter(role='consultant').filter(email__istartswith=query_name)[:10]
        results = []
        for c in consultants:
            results.append({'id': c['id'], 'name': c['email']})
        return JsonResponse({'results': results})

    return JsonResponse({'results': []})

@login_required
@csrf_exempt
@require_POST
def add_invoice(request):
    try:
        consultant_id = request.POST.get('consultant_id')
        name = request.POST.get('name')
        month_str = request.POST.get('month')
        status = request.POST.get('status')
        invoice_file = request.FILES.get('invoice_file')

        if not all([consultant_id, name, month_str, status, invoice_file]):
            return JsonResponse({'success': False, 'message': 'All fields are required.'})

        try:
            month = parse_date(month_str + '-01')  # Convert YYYY-MM to date
            if month is None:
                raise ValidationError('Invalid month format.')
        except ValidationError:
            return JsonResponse({'success': False, 'message': 'Invalid month format.'})

        consultant = User.objects.filter(id=consultant_id, role='consultant').first()
        if not consultant:
            return JsonResponse({'success': False, 'message': 'Consultant not found.'})

        with transaction.atomic():
            invoice = Invoice.objects.create(
                consultant=consultant,
                name=name,
                month=month,
                file=invoice_file,
                status=status
            )
        return JsonResponse({'success': True, 'message': 'Invoice added successfully.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error adding invoice: {str(e)}'})
