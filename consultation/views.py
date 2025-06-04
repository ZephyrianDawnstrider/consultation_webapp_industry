from django.shortcuts import render
from django.utils.timezone import now
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from custom_admin.models import User, Timesheet, Invoice, SessionBooking

def consultant_dashboard(request):
    user = request.user
    if not hasattr(user, 'role') or user.role != 'consultant':
        # Redirect or show error if not a consultant
        return render(request, 'consultant_dashboard.html', {'error': 'Access denied'})

    today = now().date()
    next_week = today + timedelta(days=7)

    # For now, just render the dashboard template without additional context
    context = {
        'current_page': 'Consultant Dashboard'
    }
    return render(request, 'consultant_dashboard.html', context)

@login_required
def consultant_timesheet(request):
    # Basic view to render the consultant_timesheet template
    context = {
        'current_page': 'Consultant Timesheet'
    }
    return render(request, 'consultant_timesheet.html', context)

from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from .forms import ConsultantProfileForm
from consultation.models import ConsultantProfile
import logging

logger = logging.getLogger(__name__)

@login_required
def consultant_profile(request, consultant_id):
    # Fetch consultant data from User model
    try:
        consultant = User.objects.get(id=consultant_id, role='consultant')
    except User.DoesNotExist:
        logger.error(f"Consultant with id {consultant_id} not found")
        raise Http404("Consultant not found")

    if request.method == 'POST':
        if 'scrap_agreement' in request.POST:
            # Handle scrap agreement document action
            try:
                profile = consultant.consultant_profile
            except ConsultantProfile.DoesNotExist:
                logger.error(f"No profile found for consultant {consultant.id}")
                return JsonResponse({'error': 'No profile found'}, status=404)

            if profile.agreement_document:
                profile.agreement_document.delete(save=False)
                profile.agreement_document = None
                profile.save()

                # Log the scrap action
                logger.info(f"Agreement document scrapped by consultant {consultant.id} - {consultant.email}")

                # Send email notification to admin
                subject = 'Agreement Document Scrapped'
                message = f'Consultant ID: {consultant.id}\nConsultant Email: {consultant.email}\nAction: Agreement document scrapped.'
                from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'no-reply@example.com'
                recipient_list = [settings.EMAIL_HOST_USER] if hasattr(settings, 'EMAIL_HOST_USER') else ['admin@example.com']

                try:
                    send_mail(subject, message, from_email, recipient_list, fail_silently=False)
                except Exception as e:
                    logger.error(f"Failed to send scrap notification email: {str(e)}")

                return JsonResponse({'success': True})

            return JsonResponse({'error': 'No agreement document to scrap'}, status=400)

        # Normal form submission to save profile data
        try:
            profile = consultant.consultant_profile
        except ConsultantProfile.DoesNotExist:
            profile = ConsultantProfile(user=consultant)

        form = ConsultantProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            try:
                form.save()
                logger.info(f"Consultant profile updated successfully for user {consultant.email}")
                return redirect('consultation:consultant_profile', consultant_id=consultant_id)
            except Exception as e:
                logger.error(f"Error saving consultant profile for user {consultant.email}: {str(e)}")
                form.add_error(None, "An error occurred while saving the profile. Please try again.")
        else:
            logger.error(f"Form validation errors for consultant {consultant.email}: {form.errors}")

    else:
        try:
            profile = ConsultantProfile.objects.prefetch_related('skills').get(user=consultant)
        except ConsultantProfile.DoesNotExist:
            profile = ConsultantProfile(user=consultant)
        form = ConsultantProfileForm(instance=profile)
        logger.info(f"Rendering consultant profile page for user {consultant.email}")

    # Debug logging for profile and form data
    logger.debug(f"ConsultantProfile: {profile}")
    logger.debug(f"Form initial data: {form.initial}")
    logger.debug(f"Form instance data: {form.instance}")

    context = {
        'consultant': consultant,
        'form': form,
        'current_page': 'Consultant Profile'
    }
    return render(request, 'consultant_profile.html', context)

@login_required
def consultant_registration(request):
    # Basic view to render the consultant_registration template
    context = {
        'current_page': 'Consultant Registration'
    }
    return render(request, 'consultant_registration.html', context)

@login_required
def consultant_invoice(request):
    # Basic view to render the consultant_invoice template
    context = {
        'current_page': 'Consultant Invoice'
    }
    return render(request, 'cosultant_invoice.html', context)
