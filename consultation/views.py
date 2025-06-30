import json
import logging
import os
from datetime import datetime, date, timedelta
from io import StringIO, BytesIO

import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
import random
import string
from custom_admin.utils import decrypt_password, encrypt_password
from custom_admin.models import User
from django.contrib.auth.decorators import login_required
import logging

logger = logging.getLogger(__name__)
from django.utils.dateparse import parse_date
from django.utils.timezone import now
from django.views.decorators.http import require_POST

from custom_admin.models import User, Invoice, SessionBooking
from consultation.models import Timesheet, ConsultantProfile
from .forms import ConsultantProfileForm

logger = logging.getLogger(__name__)


@login_required
def consultant_dashboard(request):
    """Dashboard view for consultants showing consultations, invoices, and calendar events."""
    user = request.user
    if not hasattr(user, 'role') or user.role != 'consultant':
        return render(request, 'consultant_dashboard.html', {'error': 'Access denied'})

    today = date.today()
    seven_days_later = today + timedelta(days=7)

    total_consultations = Timesheet.objects.filter(consultant=user).count()
    upcoming_consultations = SessionBooking.objects.filter(
        created_at__date__gte=today,
        created_at__date__lte=seven_days_later
    ).count()
    timesheet_uploaded = Timesheet.objects.filter(
        consultant=user,
        month__year=today.year,
        month__month=today.month
    ).exists()
    latest_invoice = Invoice.objects.filter(consultant=user).order_by('-month').first()
    invoice_status = latest_invoice.status if latest_invoice else 'No Invoices'
    invoice_uploaded = Invoice.objects.filter(
        consultant=user,
        month__year=today.year,
        month__month=today.month
    ).exists()
    invoice_history = Invoice.objects.filter(consultant=user).order_by('-month')
    bookings = SessionBooking.objects.filter(created_at__date__gte=today).order_by('created_at')

    calendar_events = [{
        'title': f"{booking.name} - {booking.consultation_field}",
        'start': booking.created_at.isoformat(),
        'allDay': True,
    } for booking in bookings]

    import calendar
    last_day = calendar.monthrange(today.year, today.month)[1]
    days_left_in_month = last_day - today.day

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
    import csv
    from datetime import datetime as dt

    today = dt.today().date()
    current_year = today.year
    year_options = [year for year in range(current_year - 10, current_year + 11)]

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

    approved_timesheets = Timesheet.objects.filter(consultant=request.user).order_by('-month')

    mode = request.GET.get('mode', 'upload')
    selected_year_str = request.GET.get('year') or str(current_year)
    selected_month_str = request.GET.get('month') or today.strftime('%m')
    selected_month = None
    if selected_year_str and selected_month_str:
        try:
            selected_month = dt.strptime(f"{selected_year_str}-{selected_month_str}", '%Y-%m').date()
        except ValueError:
            selected_month = None

    selected_timesheet = None
    if selected_month:
        selected_timesheet = approved_timesheets.filter(month__year=selected_month.year, month__month=selected_month.month).first()
    else:
        selected_timesheet = approved_timesheets.first()

    timesheet_entries = []

    logger.info(f"Selected timesheet: {selected_timesheet}")

    if selected_timesheet:
        try:
            with default_storage.open(selected_timesheet.file.name, 'r') as csv_file:
                csv_data = csv_file.read()
            f = StringIO(csv_data)
            reader = csv.DictReader(f)
            for row in reader:
                normalized_row = {k.strip().lower(): v for k, v in row.items()}
                task_name_keys = ['task name', 'task_name', 'task', 'name']
                task_name_value = ''
                for key in task_name_keys:
                    if key in normalized_row:
                        task_name_value = normalized_row[key]
                        break
                entry = {
                    'date': normalized_row.get('date'),
                    'start_time': normalized_row.get('start time'),
                    'end_time': normalized_row.get('end time'),
                    'hours_worked': normalized_row.get('hours worked'),
                    'task_name': task_name_value,
                    'description': normalized_row.get('description'),
                }
                timesheet_entries.append(entry)
            logger.info(f"Loaded {len(timesheet_entries)} timesheet entries")
        except Exception as e:
            logger.error(f"Error reading timesheet CSV file: {str(e)}")

    context = {
        'current_page': 'Consultant Timesheet',
        'year_options': year_options,
        'month_options': month_options,
        'timesheets': approved_timesheets,
        'selected_timesheet': selected_timesheet,
        'timesheet_entries': timesheet_entries,
        'mode': mode,
        'selected_year': selected_year_str,
        'selected_month': selected_month_str,
    }
    return render(request, 'consultant_timesheet.html', context)


@login_required
@require_POST
def save_timesheet_entries(request):
    import json
    import csv
    from io import StringIO
    from django.http import JsonResponse
    from django.core.files.base import ContentFile

    user = request.user
    try:
        data = json.loads(request.body)
        logger.info(f"save_timesheet_entries received data: {data}")
        timesheet_id = data.get('timesheet_id')
        entries = data.get('entries')
        selected_year_str = data.get('selected_year')
        selected_month_str = data.get('selected_month')

        if entries is None:
            logger.error("Missing entries in request data")
            return JsonResponse({'success': False, 'message': 'Missing entries.'})

        if timesheet_id:
            timesheet = Timesheet.objects.get(id=timesheet_id, consultant=user)
        else:
            if not selected_year_str or not selected_month_str:
                return JsonResponse({'success': False, 'message': 'Missing selected_year or selected_month for new timesheet.'})
            try:
                selected_month = datetime.strptime(f"{selected_year_str}-{selected_month_str}", '%Y-%m').date()
            except ValueError:
                return JsonResponse({'success': False, 'message': 'Invalid selected_year or selected_month format.'})

            file_name = f"{user.id}_{selected_month.strftime('%Y_%m')}.csv"
            file_path = os.path.join('timesheets', file_name)

            # Check if a timesheet already exists for this user and month to avoid duplicates
            existing_timesheet = Timesheet.objects.filter(consultant=user, month=selected_month).first()
            if existing_timesheet:
                timesheet = existing_timesheet
                timesheet.file.name = file_path
            else:
                timesheet = Timesheet.objects.create(
                    consultant=user,
                    month=selected_month,
                    status='awaiting_review',
                )
                timesheet.file.name = file_path

        output = StringIO()
        fieldnames = ['Date', 'Start Time', 'End Time', 'Hours Worked', 'Task Name', 'Description']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for entry in entries:
            writer.writerow({
                'Date': entry.get('date', ''),
                'Start Time': entry.get('start_time', ''),
                'End Time': entry.get('end_time', ''),
                'Hours Worked': entry.get('hours_worked', ''),
                'Task Name': entry.get('task_name', ''),
                'Description': entry.get('description', ''),
            })

        csv_content = output.getvalue()
        output.close()

        timesheet.file.save(timesheet.file.name, content=ContentFile(csv_content.encode('utf-8')))
        timesheet.save()

        logger.info("Timesheet entries saved successfully")
        return JsonResponse({'success': True, 'message': 'Timesheet entries saved successfully.', 'timesheet_id': timesheet.id})
    except Timesheet.DoesNotExist:
        logger.error("Timesheet not found or access denied")
        return JsonResponse({'success': False, 'message': 'Timesheet not found or access denied.'})
    except Exception as e:
        logger.error(f"Error saving timesheet entries: {str(e)}")
        return JsonResponse({'success': False, 'message': f'Error saving timesheet entries: {str(e)}'})




@login_required
def upload_timesheet(request, consultant_id):
    """
    Upload a timesheet Excel file, convert it to CSV, delete the original Excel file,
    save the CSV file path in the Timesheet record.
    Accessible by the consultant user themselves or admin users.
    """
    consultant = get_object_or_404(User, id=consultant_id, role='consultant')

    if not (request.user == consultant or request.user.is_staff):
        return JsonResponse({'success': False, 'message': 'Permission denied.'})

    if request.method == "POST":
        excel_file = request.FILES.get('timesheet_file')
        year_str = request.POST.get('year')
        month_str = request.POST.get('month')

        if not excel_file or not year_str or not month_str:
            logger.error(f"Upload failed: Missing file or year/month. User: {request.user.id}")
            return JsonResponse({
                'success': False,
                'message': 'Timesheet file, year, and month are required.'
            })

        try:
            month = datetime.strptime(f"{year_str}-{month_str}", '%Y-%m')
        except ValueError:
            logger.error(f"Upload failed: Invalid year/month format '{year_str}-{month_str}'. User: {request.user.id}")
            return JsonResponse({
                'success': False,
                'message': 'Invalid year/month format. Use YYYY-MM.'
            })

        try:
            temp_path = default_storage.save(f'temp/{excel_file.name}', ContentFile(excel_file.read()))
            temp_file_path = default_storage.path(temp_path)

            df = pd.read_excel(temp_file_path)

            csv_buffer = BytesIO()
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)

            csv_file_name = os.path.splitext(excel_file.name)[0] + '.csv'

            csv_path = f'timesheets/{csv_file_name}'
            if default_storage.exists(csv_path):
                default_storage.delete(csv_path)
            default_storage.save(csv_path, ContentFile(csv_buffer.read()))

            default_storage.delete(temp_path)

            timesheet = Timesheet.objects.create(
                consultant=consultant,
                month=month,
                file=csv_path,
            )

            logger.info(f"Timesheet uploaded and converted to CSV successfully by user {request.user.id} for month {year_str}-{month_str}")
            return JsonResponse({
                'success': True,
                'message': 'Timesheet uploaded successfully, converted to CSV, and awaiting review.'
            })
        except Exception as e:
            logger.error(f"Upload failed: Exception {str(e)}. User: {request.user.id}")
            return JsonResponse({
                'success': False,
                'message': f'Error processing timesheet: {str(e)}'
            })

    return render(request, 'upload_timesheet.html', {'consultant': consultant})


@login_required
def delete_timesheet(request, timesheet_id):
    """Hard delete a timesheet and its associated file."""
    user = request.user
    try:
        timesheet = Timesheet.objects.get(id=timesheet_id)
    except Timesheet.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Timesheet not found.'}, status=404)

    # Check permission: user must be the owner or staff
    if not (user == timesheet.consultant or user.is_staff):
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)

    try:
        # Delete the file from storage
        if timesheet.file and timesheet.file.name:
            timesheet.file.delete(save=False)
        # Delete the timesheet record
        timesheet.delete()
        return JsonResponse({'success': True, 'message': 'Timesheet deleted successfully.'})
    except Exception as e:
        logger.error(f"Error deleting timesheet {timesheet_id}: {str(e)}")
        return JsonResponse({'success': False, 'message': 'Error deleting timesheet.'}, status=500)

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
        
        # Handle profile update including updating User's first_name and last_name
        form = ConsultantProfileForm(request.POST, request.FILES, instance=consultant.consultant_profile if hasattr(consultant, 'consultant_profile') else None)
        if form.is_valid():
            # Save ConsultantProfile form
            profile = form.save(commit=False)
            profile.user = consultant
            profile.save()
            form.save_m2m()

            # Update User's first_name and last_name from form's 'name' field
            full_name = form.cleaned_data.get('name', '').strip()
            if full_name:
                name_parts = full_name.split()
                if len(name_parts) == 1:
                    consultant.first_name = name_parts[0]
                    consultant.last_name = ''
                else:
                    consultant.first_name = name_parts[0]
                    consultant.last_name = ' '.join(name_parts[1:])
                consultant.save()

            return redirect('consultation:consultant_profile', consultant_id=consultant_id)
        else:
            context = {
                'consultant': consultant,
                'form': form,
                'current_page': 'Consultant Profile'
            }
            return render(request, 'consultant_profile.html', context)

    try:
        profile = ConsultantProfile.objects.prefetch_related('skills').get(user=consultant)
    except ConsultantProfile.DoesNotExist:
        profile = ConsultantProfile(user=consultant)
    
    form = ConsultantProfileForm(instance=profile)
    logger.info(f"Rendering consultant profile page for user {consultant.email}")

    # Decrypt password if exists
    decrypted_password = None
    if hasattr(consultant, 'encrypted_password') and consultant.encrypted_password:
        try:
            decrypted_password = decrypt_password(consultant.encrypted_password)
        except Exception as e:
            logger.error(f"Error decrypting password for user {consultant.email}: {str(e)}")

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Return JSON response with decrypted password for AJAX requests
        return JsonResponse({'decrypted_password': decrypted_password})

    context = {
        'consultant': consultant,
        'form': form,
        'current_page': 'Consultant Profile',
        'decrypted_password': decrypted_password,
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

# OTP storage for demo purposes (in-memory dictionary)
otp_storage = {}

@login_required
@csrf_exempt
def send_otp(request):
    if request.method == 'POST':
        user = request.user
        if user.role != 'consultant':
            return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
        if user.id in otp_storage:
            # OTP already sent and not yet verified
            logger.info(f"OTP already sent to user {user.email}, not sending again")
            return JsonResponse({'success': True, 'message': 'OTP already sent'})
        otp = ''.join(random.choices(string.digits, k=6))
        otp_storage[user.id] = otp
        # Send OTP via email
        try:
            send_mail(
                subject='Your OTP for Password Change',
                message=f'Your OTP is: {otp}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info(f"OTP sent to user {user.email}")
            return JsonResponse({'success': True, 'message': 'OTP sent successfully'})
        except Exception as e:
            logger.error(f"Error sending OTP email to {user.email}: {str(e)}")
            return JsonResponse({'success': False, 'message': 'Failed to send OTP'}, status=500)
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

@login_required
@csrf_exempt
def verify_otp(request):
    if request.method == 'POST':
        user = request.user
        if user.role != 'consultant':
            return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
        data = json.loads(request.body)
        otp = data.get('otp')
        if otp_storage.get(user.id) == otp:
            # OTP verified, allow password change
            return JsonResponse({'success': True, 'message': 'OTP verified'})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid OTP'}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

@login_required
@csrf_exempt
def change_password(request):
    if request.method == 'POST':
        user = request.user
        if user.role != 'consultant':
            return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
        data = json.loads(request.body)
        new_password = data.get('new_password')
        if not new_password:
            return JsonResponse({'success': False, 'message': 'New password is required'}, status=400)
        try:
            encrypted_password = encrypt_password(new_password)
            user.encrypted_password = encrypted_password
            user.set_password(new_password)
            user.save()
            # Remove OTP after successful change
            otp_storage.pop(user.id, None)
            # Send notification emails to admin and consultant
            admin_email = settings.EMAIL_HOST_USER
            send_mail(
                subject='Password Changed Successfully',
                message=f'Consultant {user.email} has changed their password successfully.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin_email, user.email],
                fail_silently=False,
            )
            logger.info(f"Password changed successfully for user {user.email}")
            return JsonResponse({'success': True, 'message': 'Password changed successfully'})
        except Exception as e:
            logger.error(f"Error changing password for user {user.email}: {str(e)}")
            return JsonResponse({'success': False, 'message': 'Failed to change password'}, status=500)
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)


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
