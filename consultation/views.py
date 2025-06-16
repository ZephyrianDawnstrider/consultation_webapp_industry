import json
import logging
import openpyxl
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.core.serializers.json import DjangoJSONEncoder
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now
from django.views.decorators.http import require_POST

from custom_admin.models import User, Invoice, SessionBooking
from consultation.models import Timesheet, TimesheetEntry, ConsultantProfile
from .forms import ConsultantProfileForm

logger = logging.getLogger(__name__)


from datetime import date, timedelta
import json

def consultant_dashboard(request):
    """Dashboard view for consultants showing approved timesheets and other data."""
    user = request.user
    if not hasattr(user, 'role') or user.role != 'consultant':
        return render(request, 'consultant_dashboard.html', {'error': 'Access denied'})

    today = date.today()
    first_day_of_month = today.replace(day=1)
    seven_days_later = today + timedelta(days=7)

    # Total consultations: count of approved timesheets
    total_consultations = Timesheet.objects.filter(
        consultant=user,
        status='approved'
    ).count()

    # Upcoming consultations: count of SessionBooking in next 7 days
    upcoming_consultations = SessionBooking.objects.filter(
        created_at__date__gte=today,
        created_at__date__lte=seven_days_later
    ).count()

    # Timesheet uploaded for current month
    timesheet_uploaded = Timesheet.objects.filter(
        consultant=user,
        month__year=today.year,
        month__month=today.month
    ).exists()

    # Latest invoice status or 'No Invoices'
    latest_invoice = Invoice.objects.filter(consultant=user).order_by('-month').first()
    invoice_status = latest_invoice.status if latest_invoice else 'No Invoices'

    # Invoice uploaded for current month
    invoice_uploaded = Invoice.objects.filter(
        consultant=user,
        month__year=today.year,
        month__month=today.month
    ).exists()

    # Invoice history ordered by month descending
    invoice_history = Invoice.objects.filter(consultant=user).order_by('-month')

    # Calendar events from SessionBooking for FullCalendar
    bookings = SessionBooking.objects.filter(
        created_at__date__gte=today
    ).order_by('created_at')

    calendar_events = []
    for booking in bookings:
        event = {
            'title': f"{booking.name} - {booking.consultation_field}",
            'start': booking.created_at.isoformat(),
            'allDay': True,
        }
        calendar_events.append(event)

    from django.urls import reverse

    # Calculate days left in current month
    import calendar
    last_day = calendar.monthrange(today.year, today.month)[1]
    days_left_in_month = last_day - today.day

    # URL for timesheet upload page - redirect to consultant_timesheet page instead of upload_timesheet
    from django.urls import reverse
    timesheet_upload_url = reverse('consultation:consultant_timesheet')

    context = {
        'current_page': 'Consultant Dashboard',
        'total_consultations': total_consultations,
        'upcoming_consultations': upcoming_consultations,
        'timesheet_uploaded': timesheet_uploaded,
        'invoice_status': invoice_status,
        'invoice_history': invoice_history,
        'calendar_events': json.dumps(calendar_events),
        'days_left_in_month': days_left_in_month,
        'timesheet_upload_url': timesheet_upload_url,
    }
    return render(request, 'consultant_dashboard.html', context)


@login_required
def consultant_timesheet(request):
    """View for consultant timesheet with month options and entries."""
    # Prepare month options for last 12 months
    today = now().date()
    month_options = []
    for i in range(12):
        month_date = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        month_value = month_date.strftime('%Y-%m')
        month_name = month_date.strftime('%B %Y')
        month_options.append({'value': month_value, 'name': month_name, 'selected': False})

    # Fetch approved timesheets and their entries for this consultant
    approved_timesheets = Timesheet.objects.filter(
        consultant=request.user,
        status__in=['approved', 'rejected', 'awaiting_review', 'sent_to_bank']
    ).order_by('-month')

    timesheet_entries_qs = TimesheetEntry.objects.filter(
        timesheet__in=approved_timesheets
    ).order_by('date')

    timesheet_entries = list(timesheet_entries_qs.values(
        'date', 'hours_worked', 'task_name', 'description'
    ))

    context = {
        'current_page': 'Consultant Timesheet',
        'month_options': month_options,
        'timesheets': approved_timesheets,
        'timesheet_entries': json.dumps(timesheet_entries, cls=DjangoJSONEncoder)
    }
    return render(request, 'consultant_timesheet.html', context)

@login_required
def upload_timesheet(request, consultant_id):
    """
    Upload a timesheet Excel file and save Timesheet record.
    TimesheetEntry records are created only when Timesheet status is approved.
    Accessible by the consultant user themselves or admin users.
    """
    consultant = get_object_or_404(User, id=consultant_id, role='consultant')

    # Check if the user is the consultant or an admin
    if not (request.user == consultant or request.user.is_staff):
        return JsonResponse({'success': False, 'message': 'Permission denied.'})

    if request.method == "POST":
        excel_file = request.FILES.get('timesheet_file')
        month_str = request.POST.get('month')

        if not excel_file or not month_str:
            logger.error(f"Upload failed: Missing file or month. User: {request.user.id}")
            return JsonResponse({
                'success': False, 
                'message': 'Timesheet file and month are required.'
            })

        try:
            month = datetime.strptime(month_str, '%Y-%m')
        except ValueError:
            logger.error(f"Upload failed: Invalid month format '{month_str}'. User: {request.user.id}")
            return JsonResponse({
                'success': False, 
                'message': 'Invalid month format. Use YYYY-MM.'
            })

        try:
            # Create Timesheet record only
            timesheet = Timesheet.objects.create(
                consultant=consultant,
                month=month,
                file=excel_file,
                status='awaiting_review'
            )
            logger.info(f"Timesheet uploaded successfully by user {request.user.id} for month {month_str}")
            return JsonResponse({
                'success': True, 
                'message': 'Timesheet uploaded successfully and awaiting review.'
            })
        except Exception as e:
            logger.error(f"Upload failed: Exception {str(e)}. User: {request.user.id}")
            return JsonResponse({
                'success': False, 
                'message': f'Error saving timesheet: {str(e)}'
            })

    # GET request - render upload form
    return render(request, 'upload_timesheet.html', {'consultant': consultant})


@login_required
def consultant_profile(request, consultant_id):
    """View and edit consultant profile."""
    try:
        consultant = User.objects.get(id=consultant_id, role='consultant')
    except User.DoesNotExist:
        logger.error(f"Consultant with id {consultant_id} not found")
        raise Http404("Consultant not found")

    if request.method == 'POST':
        if 'scrap_agreement' in request.POST:
            return _handle_scrap_agreement(request, consultant)
        
        return _handle_profile_update(request, consultant, consultant_id)

    # GET request - render form
    try:
        profile = ConsultantProfile.objects.prefetch_related('skills').get(user=consultant)
    except ConsultantProfile.DoesNotExist:
        profile = ConsultantProfile(user=consultant)
    
    form = ConsultantProfileForm(instance=profile)
    logger.info(f"Rendering consultant profile page for user {consultant.email}")

    context = {
        'consultant': consultant,
        'form': form,
        'current_page': 'Consultant Profile'
    }
    return render(request, 'consultant_profile.html', context)


def _handle_scrap_agreement(request, consultant):
    """Handle scrapping agreement document."""
    try:
        profile = consultant.consultant_profile
    except ConsultantProfile.DoesNotExist:
        logger.error(f"No profile found for consultant {consultant.id}")
        return JsonResponse({'error': 'No profile found'}, status=404)

    if not profile.agreement_document:
        return JsonResponse({'error': 'No agreement document to scrap'}, status=400)

    profile.agreement_document.delete(save=False)
    profile.agreement_document = None
    profile.save()

    logger.info(f"Agreement document scrapped by consultant {consultant.id} - {consultant.email}")
    _send_scrap_notification_email(consultant)
    
    return JsonResponse({'success': True})


def _handle_profile_update(request, consultant, consultant_id):
    """Handle profile form submission."""
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
    
    context = {
        'consultant': consultant,
        'form': form,
        'current_page': 'Consultant Profile'
    }
    return render(request, 'consultant_profile.html', context)


def _send_scrap_notification_email(consultant):
    """Send email notification when agreement document is scrapped."""
    subject = 'Agreement Document Scrapped'
    message = (
        f'Consultant ID: {consultant.id}\n'
        f'Consultant Email: {consultant.email}\n'
        f'Action: Agreement document scrapped.'
    )
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com')
    recipient_list = [getattr(settings, 'EMAIL_HOST_USER', 'admin@example.com')]

    try:
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
    except Exception as e:
        logger.error(f"Failed to send scrap notification email: {str(e)}")


@login_required
def consultant_registration(request):
    """Basic view to render the consultant registration template."""
    context = {
        'current_page': 'Consultant Registration'
    }
    return render(request, 'consultant_registration.html', context)


from django.contrib import messages
from django.utils.dateparse import parse_date

from custom_admin.models import Invoice

@login_required
def consultant_invoice(request):
    """View to handle invoice upload and display uploaded invoices."""
    user = request.user
    if user.role != 'consultant':
        return render(request, 'consultant_invoice.html', {'error': 'Access denied'})

    if request.method == 'POST':
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Invoice upload POST request received from user {user.id}")
        month_str = request.POST.get('month')
        invoice_file = request.FILES.get('invoice_file')
        logger.info(f"Received month: {month_str}, invoice_file present: {invoice_file is not None}")

        if not month_str or not invoice_file:
            messages.error(request, 'Month and invoice file are required.')
        else:
            # Parse month string to date object (assume format is month name)
            try:
                # Convert month name to date with day=1 and current year
                month_date = parse_date(f"2025-{datetime.strptime(month_str, '%B').month:02d}-01")
                if not month_date:
                    raise ValueError("Invalid month format")
            except Exception as e:
                logger.error(f"Invalid month format error: {str(e)}")
                messages.error(request, 'Invalid month format. Please select a valid month.')
                month_date = None

            if month_date:
                try:
                    # Save invoice
                    invoice = Invoice.objects.create(
                        consultant=user,
                        month=month_date,
                        file=invoice_file,
                        name=invoice_file.name,
                        status='awaiting_review'
                    )
                    messages.success(request, 'Invoice uploaded successfully and awaiting review.')
                    logger.info(f"Invoice saved successfully for user {user.id}")
                except Exception as e:
                    logger.error(f"Error saving invoice: {str(e)}")
                    messages.error(request, f'Error saving invoice: {str(e)}')

    # Fetch invoices for the logged-in consultant
    invoices = Invoice.objects.filter(consultant=user).order_by('-month')

    context = {
        'current_page': 'Consultant Invoice',
        'invoices': invoices,
    }
    return render(request, 'consultant_invoice.html', context)


@login_required
def consultant_profile(request, consultant_id):
    """View and edit consultant profile."""
    try:
        consultant = User.objects.get(id=consultant_id, role='consultant')
    except User.DoesNotExist:
        logger.error(f"Consultant with id {consultant_id} not found")
        raise Http404("Consultant not found")

    if request.method == 'POST':
        if 'scrap_agreement' in request.POST:
            return _handle_scrap_agreement(request, consultant)
        
        return _handle_profile_update(request, consultant, consultant_id)

    # GET request - render form
    try:
        profile = ConsultantProfile.objects.prefetch_related('skills').get(user=consultant)
    except ConsultantProfile.DoesNotExist:
        profile = ConsultantProfile(user=consultant)
    
    form = ConsultantProfileForm(instance=profile)
    logger.info(f"Rendering consultant profile page for user {consultant.email}")

    context = {
        'consultant': consultant,
        'form': form,
        'current_page': 'Consultant Profile'
    }
    return render(request, 'consultant_profile.html', context)


def _handle_scrap_agreement(request, consultant):
    """Handle scrapping agreement document."""
    try:
        profile = consultant.consultant_profile
    except ConsultantProfile.DoesNotExist:
        logger.error(f"No profile found for consultant {consultant.id}")
        return JsonResponse({'error': 'No profile found'}, status=404)

    if not profile.agreement_document:
        return JsonResponse({'error': 'No agreement document to scrap'}, status=400)

    profile.agreement_document.delete(save=False)
    profile.agreement_document = None
    profile.save()

    logger.info(f"Agreement document scrapped by consultant {consultant.id} - {consultant.email}")
    _send_scrap_notification_email(consultant)
    
    return JsonResponse({'success': True})


def _handle_profile_update(request, consultant, consultant_id):
    """Handle profile form submission."""
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
    
    context = {
        'consultant': consultant,
        'form': form,
        'current_page': 'Consultant Profile'
    }
    return render(request, 'consultant_profile.html', context)


def _send_scrap_notification_email(consultant):
    """Send email notification when agreement document is scrapped."""
    subject = 'Agreement Document Scrapped'
    message = (
        f'Consultant ID: {consultant.id}\n'
        f'Consultant Email: {consultant.email}\n'
        f'Action: Agreement document scrapped.'
    )
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com')
    recipient_list = [getattr(settings, 'EMAIL_HOST_USER', 'admin@example.com')]

    try:
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
    except Exception as e:
        logger.error(f"Failed to send scrap notification email: {str(e)}")


@login_required
def consultant_registration(request):
    """Basic view to render the consultant registration template."""
    context = {
        'current_page': 'Consultant Registration'
    }
    return render(request, 'consultant_registration.html', context)


from django.contrib import messages
from django.utils.dateparse import parse_date

from custom_admin.models import Invoice

@login_required
def consultant_invoice(request):
    """View to handle invoice upload and display uploaded invoices."""
    user = request.user
    if user.role != 'consultant':
        return render(request, 'consultant_invoice.html', {'error': 'Access denied'})

    if request.method == 'POST':
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Invoice upload POST request received from user {user.id}")
        month_str = request.POST.get('month')
        invoice_file = request.FILES.get('invoice_file')
        logger.info(f"Received month: {month_str}, invoice_file present: {invoice_file is not None}")

        if not month_str or not invoice_file:
            messages.error(request, 'Month and invoice file are required.')
        else:
            # Parse month string to date object (assume format is month name)
            try:
                # Convert month name to date with day=1 and current year
                month_date = parse_date(f"2025-{datetime.strptime(month_str, '%B').month:02d}-01")
                if not month_date:
                    raise ValueError("Invalid month format")
            except Exception as e:
                logger.error(f"Invalid month format error: {str(e)}")
                messages.error(request, 'Invalid month format. Please select a valid month.')
                month_date = None

            if month_date:
                try:
                    # Save invoice
                    invoice = Invoice.objects.create(
                        consultant=user,
                        month=month_date,
                        file=invoice_file,
                        name=invoice_file.name,
                        status='awaiting_review'
                    )
                    messages.success(request, 'Invoice uploaded successfully and awaiting review.')
                    logger.info(f"Invoice saved successfully for user {user.id}")
                except Exception as e:
                    logger.error(f"Error saving invoice: {str(e)}")
                    messages.error(request, f'Error saving invoice: {str(e)}')

    # Fetch invoices for the logged-in consultant
    invoices = Invoice.objects.filter(consultant=user).order_by('-month')

    context = {
        'current_page': 'Consultant Invoice',
        'invoices': invoices,
    }
    return render(request, 'consultant_invoice.html', context)
