from django.shortcuts import render
from django.utils.timezone import now
from datetime import timedelta, datetime
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.core.mail import send_mail
from django.conf import settings
from custom_admin.models import User, Invoice, SessionBooking
from consultation.models import Timesheet, TimesheetEntry
import openpyxl
import logging

logger = logging.getLogger(__name__)

def consultant_dashboard(request):
    user = request.user
    if not hasattr(user, 'role') or user.role != 'consultant':
        # Redirect or show error if not a consultant
        return render(request, 'consultant_dashboard.html', {'error': 'Access denied'})

    today = now().date()
    next_week = today + timedelta(days=7)

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

from django.utils.timezone import now
from datetime import date

@login_required
def consultant_timesheet(request):
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

    timesheet_entries = list(timesheet_entries_qs.values('date', 'hours_worked', 'task_name', 'description'))

    import json
    from django.core.serializers.json import DjangoJSONEncoder

    context = {
        'current_page': 'Consultant Timesheet',
        'month_options': month_options,
        'timesheet_entries': json.dumps(timesheet_entries, cls=DjangoJSONEncoder)
    }
    return render(request, 'consultant_timesheet.html', context)

@login_required
def upload_timesheet(request, consultant_id):
    """
    View to upload a timesheet Excel file and save Timesheet record.
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
            return JsonResponse({'success': False, 'message': 'Timesheet file and month are required.'})

        try:
            month = datetime.strptime(month_str, '%Y-%m')
        except ValueError:
            logger.error(f"Upload failed: Invalid month format '{month_str}'. User: {request.user.id}")
            return JsonResponse({'success': False, 'message': 'Invalid month format. Use YYYY-MM.'})

        try:
            # Create Timesheet record only
            timesheet = Timesheet.objects.create(
                consultant=consultant,
                month=month,
                file=excel_file,
                status='awaiting_review'
            )
        except Exception as e:
            logger.error(f"Upload failed: Exception {str(e)}. User: {request.user.id}")
            return JsonResponse({'success': False, 'message': f'Error saving timesheet: {str(e)}'})

        logger.info(f"Timesheet uploaded successfully by user {request.user.id} for month {month_str}")
        return JsonResponse({'success': True, 'message': 'Timesheet uploaded successfully and awaiting review.'})

    # GET request - render upload form
    return render(request, 'upload_timesheet.html', {'consultant': consultant})

def create_timesheet_entries(timesheet):
    """
    Process the Excel file of the given Timesheet and create TimesheetEntry records.
    """
    try:
        wb = openpyxl.load_workbook(timesheet.file)
        sheet = wb.active

        header = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
        expected_headers = ['Date', 'Start Time', 'End Time', 'Task']
        if header != expected_headers:
            logger.error(f"Timesheet {timesheet.id} has invalid Excel headers: {header}")
            return False, f'Invalid Excel format. Expected headers: {expected_headers}'

        entries = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            date_val, start_time, end_time, task_name = row
            if not date_val or not start_time or not end_time or not task_name:
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

@login_required
@user_passes_test(lambda u: u.is_staff)
def update_timesheet_status(request, timesheet_id):
    """
    View to update the status of a timesheet. Only admin can update.
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
            return JsonResponse({'success': False, 'message': f'Failed to create timesheet entries: {error}'})

    if new_status == 'rejected':
        # Send email to consultant to upload a new timesheet
        subject = 'Timesheet Rejected - Please Upload a New One'
        message = f'Dear {timesheet.consultant.email},\n\nYour timesheet for {timesheet.month.strftime("%B %Y")} has been rejected. Please upload a new timesheet.\n\nRegards,\nConsultation Team'
        from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'no-reply@example.com'
        recipient_list = [timesheet.consultant.email]

        try:
            send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        except Exception as e:
            logger.error(f"Failed to send timesheet rejection email: {str(e)}")

    return JsonResponse({'success': True, 'message': 'Timesheet status updated successfully.'})

@login_required
@user_passes_test(lambda u: u.is_staff)
def update_timesheet_status(request, timesheet_id):
    """
    View to update the status of a timesheet. Only admin can update.
    Sends email notification if timesheet is rejected.
    """
    timesheet = get_object_or_404(Timesheet, id=timesheet_id)
    new_status = request.POST.get('status')

    if new_status not in dict(Timesheet.STATUS_CHOICES).keys():
        return JsonResponse({'success': False, 'message': 'Invalid status value.'})

    timesheet.status = new_status
    timesheet.save()

    if new_status == 'rejected':
        # Send email to consultant to upload a new timesheet
        subject = 'Timesheet Rejected - Please Upload a New One'
        message = f'Dear {timesheet.consultant.email},\n\nYour timesheet for {timesheet.month.strftime("%B %Y")} has been rejected. Please upload a new timesheet.\n\nRegards,\nConsultation Team'
        from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'no-reply@example.com'
        recipient_list = [timesheet.consultant.email]

        try:
            send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        except Exception as e:
            logger.error(f"Failed to send timesheet rejection email: {str(e)}")

    return JsonResponse({'success': True, 'message': 'Timesheet status updated successfully.'})

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
