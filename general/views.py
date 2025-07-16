import json
import logging
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.core.mail import send_mail
from general.forms import ProspectiveConsultantForm

logger = logging.getLogger(__name__)
User = get_user_model()

@csrf_exempt
def login_view(request):
    """
    Handle user login for both admin and consultant users
    Supports different authentication methods based on user role
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        logger.info(f"Login attempt for email: {email}")
        
        # Check if user exists
        try:
            user = User.objects.get(email=email)
            logger.info(f"User found: {user.email} with role {user.role}")
        except User.DoesNotExist:
            logger.warning(f"Login failed: User with email {email} does not exist")
            messages.error(request, 'Invalid email or password')
            return redirect('login')

        # Handle admin login
        if user.role == 'admin':
            user_auth = authenticate(request, username=email, password=password)
            if user_auth is not None:
                logger.info(f"Admin user {email} authenticated successfully.")
                login(request, user_auth)
                return redirect('custom_admin:admin_dashboard')
            else:
                logger.warning(f"Admin user {email} failed authentication.")
                messages.error(request, 'Invalid email or password')
                return redirect('login')
        
        # Handle consultant login
        elif user.role == 'consultant':
            if user.check_consultant_password(password):
                login(request, user)
                logger.info(f"Consultant user {email} logged in successfully.")
                return redirect('consultant:consultant_dashboard')
            else:
                logger.warning(f"Consultant user {email} failed password check.")
                messages.error(request, 'Invalid email or password')
                return redirect('login')
        else:
            logger.warning(f"User {email} has unknown role {user.role}")
        
        # Fallback for unhandled cases
        return render(request, 'landingpage.html')
    
    # GET request - show login form
    return render(request, 'landingpage.html')

from django.contrib import messages
from django.shortcuts import redirect

@csrf_exempt
@require_http_methods(["POST"])
def ProspectiveConsultant(request):
    form = ProspectiveConsultantForm(request.POST)
    if form.is_valid():
        prospective_consultant = form.save(commit=False)
        consultant_field = prospective_consultant.consultant_field
        if consultant_field == 'Other' and prospective_consultant.other_consultant_field:
            consultant_field = prospective_consultant.other_consultant_field
        prospective_consultant.save()

        # Send booking details to admin email
        admin_email = "1ayushchaturvedi@gmail.com"
        subject = 'New Prospective Consultant Request'
        message = f"""
New prospective consultant details:

Name: {prospective_consultant.name}
Email: {prospective_consultant.email}
Phone: {prospective_consultant.phone}
Consultant Field: {consultant_field}
Consultant Linkedin: {prospective_consultant.linkedin if hasattr(prospective_consultant, 'linkedin') else 'N/A'}
"""
        send_mail(subject, message, admin_email, [admin_email])

        # Send confirmation email to user
        user_subject = "Request Confirmation"
        user_message = f"Dear {prospective_consultant.name},\n\nThank you for your interest. We have received your request and will get back to you shortly.\n\nBest regards,\nCHL Softech Team"
        send_mail(user_subject, user_message, admin_email, [prospective_consultant.email])

        messages.success(request, "Your request has been submitted successfully.")
        return redirect('general:landingpage')
    else:
        messages.error(request, "There was an error with your submission. Please correct the errors and try again.")
        return redirect('general:landingpage')
