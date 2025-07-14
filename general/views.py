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
from general.forms import consultantBookingForm

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

@csrf_exempt
@require_http_methods(["POST"])
def book_consultant(request):
    form = consultantBookingForm(request.POST)
    if form.is_valid():
        booking = form.save(commit=False)
        consultant_field = booking.consultant_field
        if consultant_field == 'Other' and booking.other_consultant_field:
            consultant_field = booking.other_consultant_field
        booking.save()

        # Send booking details to admin email
        admin_email = "1ayushchaturvedi@gmail.com"
        subject = 'New Consultant Booking'
        message = f"""
New consultant booking details:

Name: {booking.name}
Email: {booking.email}
Phone: {booking.phone}
Consultant Field: {consultant_field}
"""
        send_mail(subject, message, admin_email, [admin_email])

        # Send confirmation email to user
        user_subject = "Booking Confirmation"
        user_message = f"Dear {booking.name},\n\nThank you for booking a consultation with us. We have received your inquiry and will get back to you shortly.\n\nBest regards,\nCHL Softech Team"
        send_mail(user_subject, user_message, admin_email, [booking.email])

        return JsonResponse({'success': True, 'message': 'Booking submitted successfully.'})
    else:
        return JsonResponse({'success': False, 'errors': form.errors})
