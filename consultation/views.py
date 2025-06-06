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


def consultant_dashboard(request):
    """Dashboard view for consultants showing approved timesheets."""
    user = request.user
    if not hasattr(user, 'role') or user.role != 'consultant':
        return render(request, 'consultant_dashboard.html', {'error': 'Access denied'})

    # Fetch approved timesheets and their entries for this consultant
    approved_timesheets = Timesheet.objects.filter(
        consultant=user,
        status='approved'
    ).order_by('-month')

    timesheet_entries = TimesheetEntry.objects.filter(
        timesheet__in=approved_timesheets
    ).order_by('date')

    context = {
        'current_page': 'Consultant Dashboard',
        'timesheets': approved_timesheets,
        'timesheet_entries': timesheet_entries,
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
        status='approved'
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


def create_timesheet_entries(timesheet):
    """
    Process the Excel file of the given Timesheet and create TimesheetEntry records.
    Returns (success: bool, error_message: str or None)
    """
    try:
        wb = openpyxl.load_workbook(timesheet.file)
        sheet = wb.active

        # Validate headers
        header = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
        expected_headers = ['Date', 'Start Time', 'End Time', 'Task']
        if header != expected_headers:
            logger.error(f"Timesheet {timesheet.id} has invalid Excel headers: {header}")
            return False, f'Invalid Excel format. Expected headers: {expected_headers}'

        entries = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            date_val, start_time, end_time, task_name = row
            
            # Skip empty rows
            if not all([date_val, start_time, end_time, task_name]):
                continue
            
            # Parse date
            date_val = _parse_date(date_val)
            if not date_val:
                continue

            # Parse times and calculate hours
            start_decimal = _time_to_decimal(start_time)
            end_decimal = _time_to_decimal(end_time)
            if start_decimal is None or end_decimal is None or end_decimal <= start_decimal:
                continue
            
            hours_worked = end_decimal - start_decimal

            entry = TimesheetEntry(
                timesheet=timesheet,
                date=date_val,
                hours_worked=hours_worked,
                project=task_name,
                task_name=task_name,
                description=f'Task: {task_name} from {start_time} to {end_time}'
            )
            entries.append(entry)

        TimesheetEntry.objects.bulk_create(entries)
        logger.info(f"Created {len(entries)} TimesheetEntry records for Timesheet {timesheet.id}")
        return True, None
        
    except Exception as e:
        logger.error(f"Error processing Timesheet {timesheet.id}: {str(e)}")
        return False, str(e)


def _parse_date(date_val):
    """Parse date value from Excel."""
    if isinstance(date_val, str):
        try:
            return datetime.strptime(date_val, '%Y-%m-%d').date()
        except ValueError:
            return None
    elif isinstance(date_val, datetime):
        return date_val.date()
    return None


def _time_to_decimal(time_val):
    """Convert time value to decimal hours."""
    if isinstance(time_val, datetime):
        return time_val.hour + time_val.minute / 60
    elif isinstance(time_val, str):
        try:
            dt = datetime.strptime(time_val, '%H:%M')
            return dt.hour + dt.minute / 60
        except ValueError:
            return None
    elif isinstance(time_val, (int, float)):
        return time_val * 24
    return None


@login_required
@user_passes_test(lambda u: u.is_staff)
def update_timesheet_status(request, timesheet_id):
    """
    Update the status of a timesheet. Only admin can update.
    Sends email notification if timesheet is rejected.
    Creates TimesheetEntry records if status is approved.
    """
    timesheet = get_object_or_404(Timesheet, id=timesheet_id)
    new_status = request.POST.get('status')

    if new_status not in dict(Timesheet.STATUS_CHOICES).keys():
        return JsonResponse({'success': False, 'message': 'Invalid status value.'})

    timesheet.status = new_status
    timesheet.save()

    if new_status == 'approved':
        success, error = create_timesheet_entries(timesheet)
        if not success:
            return JsonResponse({
                'success': False, 
                'message': f'Failed to create timesheet entries: {error}'
            })

    if new_status == 'rejected':
        _send_rejection_email(timesheet)

    return JsonResponse({'success': True, 'message': 'Timesheet status updated successfully.'})


def _send_rejection_email(timesheet):
    """Send email notification for rejected timesheet."""
    subject = 'Timesheet Rejected - Please Upload a New One'
    message = (
        f'Dear {timesheet.consultant.email},\n\n'
        f'Your timesheet for {timesheet.month.strftime("%B %Y")} has been rejected. '
        f'Please upload a new timesheet.\n\n'
        f'Regards,\nConsultation Team'
    )
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com')
    recipient_list = [timesheet.consultant.email]

    try:
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
    except Exception as e:
        logger.error(f"Failed to send timesheet rejection email: {str(e)}")


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


@login_required
def consultant_invoice(request):
    """Basic view to render the consultant invoice template."""
    context = {
        'current_page': 'Consultant Invoice'
    }
    return render(request, 'consultant_invoice.html', context)
