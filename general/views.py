import json
import logging
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth import get_user_model

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
                return redirect('consultation:consultant_dashboard')
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
