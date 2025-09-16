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

from custom_admin.models import User, Invoice, SessionBooking, Skill
from consultant.models import Timesheet, ConsultantProfile, ConsultantSkillExperience
from .forms import ConsultantProfileForm

logger = logging.getLogger(__name__)


@login_required
def consultant_dashboard(request):
    """Dashboard view for consultants showing consultants, invoices, and calendar events."""
    user = request.user
    if not hasattr(user, 'role') or user.role != 'consultant':
        return render(request, 'consultant_dashboard.html', {'error': 'Access denied'})

    today = date.today()
    seven_days_later = today + timedelta(days=7)

    total_consultants = Timesheet.objects.filter(consultant=user).count()
    upcoming_consultants = SessionBooking.objects.filter(
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
        'title': f"{booking.name} - {booking.consultant_field}",
        'start': booking.created_at.isoformat(),
        'allDay': True,
    } for booking in bookings]

    import calendar
    last_day = calendar.monthrange(today.year, today.month)[1]
    days_left_in_month = last_day - today.day

    from django.urls import reverse
    timesheet_upload_url = reverse('consultant:consultant_timesheet')

    context = {
        'current_page': 'Consultant Dashboard',
        'total_consultants': total_consultants,
        'upcoming_consultants': upcoming_consultants,
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
    year_options = [year for year in range(current_year - 10, current_year+1)]

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

    if selected_timesheet and selected_timesheet.file and selected_timesheet.file.name:
        try:
            with default_storage.open(selected_timesheet.file.name, 'rb') as f:
                csv_data_bytes = f.read()
            try:
                csv_data = csv_data_bytes.decode('utf-8')
            except UnicodeDecodeError:
                csv_data = csv_data_bytes.decode('latin-1')
            f = StringIO(csv_data)
            reader = csv.DictReader(f)
            for row in reader:
                normalized_row = {k.strip().lower(): v.strip() if v else v for k, v in row.items()}
                # Dynamically find keys
                date_key = next((k for k in normalized_row if 'date' in k), None)
                start_time_key = next((k for k in normalized_row if 'start' in k and 'time' in k), None)
                end_time_key = next((k for k in normalized_row if 'end' in k and 'time' in k), None)
                project_name_key = next((k for k in normalized_row if 'project' in k and 'name' in k), None)
                task_name_key = next((k for k in normalized_row if 'task' in k and 'name' in k), None)
                hours_worked_key = next((k for k in normalized_row if 'hours' in k and 'worked' in k), None)
                description_key = next((k for k in normalized_row if 'description' in k), None)

                raw_hours = normalized_row.get(hours_worked_key, '').strip() if hours_worked_key else ''
                start_time_str = normalized_row.get(start_time_key, '').strip() if start_time_key else ''
                end_time_str = normalized_row.get(end_time_key, '').strip() if end_time_key else ''
                project_name = normalized_row.get(project_name_key, '').strip() if project_name_key else ''
                task_name = normalized_row.get(task_name_key, '').strip() if task_name_key else ''
                description = normalized_row.get(description_key, '').strip() if description_key else ''
                date = normalized_row.get(date_key, '').strip() if date_key else ''

                hours_worked = 0.0
                try:
                    from datetime import datetime as dt
                    fmt_24 = '%H:%M'
                    fmt_12 = '%I:%M %p'
                    def parse_time(t):
                        for fmt in (fmt_24, fmt_12):
                            try:
                                return dt.strptime(t, fmt)
                            except Exception:
                                continue
                        return None
                    start_dt = parse_time(start_time_str) if start_time_str else None
                    end_dt = parse_time(end_time_str) if end_time_str else None
                    if start_dt and end_dt:
                        delta = end_dt - start_dt
                        hours_worked = delta.total_seconds() / 3600
                        if hours_worked < 0:
                            # If negative, assume end time is on next day
                            hours_worked += 24
                    # If not calculated or 0, try raw_hours
                    if hours_worked == 0.0 and raw_hours not in (None, ''):
                        try:
                            hours_worked = float(raw_hours)
                        except:
                            pass
                except (ValueError, TypeError):
                    logger.warning(f"Invalid hours_worked value '{raw_hours}' in timesheet CSV, defaulting to 0")
                    hours_worked = 0.0
                entry = {
                    'date': date,
                    'start_time': start_time_str,
                    'end_time': end_time_str,
                    'project_name': project_name,
                    'hours_worked': hours_worked,
                    'task_name': task_name,
                    'description': description,
                }
                timesheet_entries.append(entry)
            # Sort timesheet entries by date ascending
            timesheet_entries.sort(key=lambda x: x['date'] if x['date'] else '')
            logger.info(f"Loaded {len(timesheet_entries)} timesheet entries")
        except Exception as e:
            logger.error(f"Error reading timesheet CSV file: {str(e)}")

    # Calculate total hours per project
    project_hours_summary = {}
    for entry in timesheet_entries:
        project = entry.get('project_name') or ''
        try:
            raw_hours = entry.get('hours_worked')
            logger.info(f"Processing entry for summary: project='{project}', raw_hours='{raw_hours}' (type: {type(raw_hours)})")
            if isinstance(raw_hours, str):
                raw_hours = raw_hours.replace(',', '').strip()
            hours = float(raw_hours) if raw_hours not in (None, '') else 0
            logger.info(f"Calculated hours for summary: {hours}")
        except (ValueError, TypeError):
            logger.warning(f"Invalid hours_worked value '{entry.get('hours_worked')}' for project '{project}', defaulting to 0")
            hours = 0
        project_hours_summary[project] = project_hours_summary.get(project, 0) + hours
        logger.info(f"Current summary for '{project}': {project_hours_summary[project]}")

    # Convert to list of dicts for template
    project_hours_list = [{'project_name': k, 'total_hours': v} for k, v in project_hours_summary.items() if k]

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
        'project_hours_summary': project_hours_list,
    }
    return render(request, 'consultant_timesheet.html', context)


@login_required
@require_POST
def save_timesheet_entries(request):
    """Save or update timesheet entries from an editable table."""
    import csv
    from io import StringIO
    from django.core.files.base import ContentFile
    
    user = request.user
    if not user.is_authenticated or not hasattr(user, 'consultantprofile'):
        return JsonResponse({'success': False, 'message': 'User is not authenticated or not a consultant.'})

    try:
        data = json.loads(request.body)
        entries = data.get('entries', [])
        timesheet_id = data.get('timesheet_id')
        selected_year_str = data.get('selected_year')
        selected_month_str = data.get('selected_month')

        # Generate CSV content
        output = StringIO()
        fieldnames = ['Date', 'Task Description', 'Hours Worked']
        writer = csv.writer(output)
        writer.writerow(fieldnames)
        
        total_hours = 0
        for entry in entries:
            hours = float(entry.get('hours', 0))
            writer.writerow([
                entry.get('date', ''),
                entry.get('task', ''),
                hours
            ])
            total_hours += hours

        csv_content = output.getvalue()
        output.close()

        # Create a ContentFile for saving
        file_content = ContentFile(csv_content.encode('utf-8'))

        if timesheet_id:
            # Update existing timesheet
            timesheet = get_object_or_404(Timesheet, id=timesheet_id, consultant=user)
            file_name = None
            if timesheet.file and timesheet.file.name:
                file_name = os.path.basename(timesheet.file.name)
            
            if not file_name:
                file_name = f"{user.id}_{timesheet.month.strftime('%Y_%m')}.csv"
            
            timesheet.file.save(file_name, file_content, save=True)
            
        else:
            # Create new timesheet
            if not selected_year_str or not selected_month_str:
                return JsonResponse({'success': False, 'message': 'Missing selected_year or selected_month for new timesheet.'})
            
            try:
                selected_month_date = datetime.strptime(f"{selected_year_str}-{selected_month_str}-01", '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'success': False, 'message': 'Invalid year or month.'})

            file_name = f"{user.id}_{selected_month_date.strftime('%Y_%m')}.csv"
            
            # Use get_or_create to handle existing timesheet for the month
            timesheet, created = Timesheet.objects.get_or_create(
                consultant=user,
                month=selected_month_date,
                defaults={'status': 'pending'}
            )
            
            # Save the file to the timesheet instance
            timesheet.file.save(file_name, file_content, save=True)

        logger.info("Timesheet entries saved successfully for timesheet_id: %s", timesheet.id)
        return JsonResponse({
            'success': True,
            'message': 'Timesheet entries saved successfully.',
            'timesheet_id': timesheet.id
        })

    except Timesheet.DoesNotExist:
        logger.error("Timesheet not found or access denied for timesheet_id: %s", timesheet_id)
        return JsonResponse({'success': False, 'message': 'Timesheet not found or access denied.'})
    except Exception as e:
        logger.error("Error saving timesheet entries: %s", str(e), exc_info=True)
        return JsonResponse({'success': False, 'message': f'An unexpected error occurred: {str(e)}'})




@login_required
def upload_timesheet(request, consultant_id):
    """
    Upload a timesheet Excel file, convert it to CSV, delete the original Excel file,
    save the CSV file path in the Timesheet record.
    Accessible by the consultant user themselves or admin users.
    """
    from custom_admin.models import ActivityLog
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

            # Remove blank rows from the dataframe
            df.dropna(how='all', inplace=True)

            # Check for duplicate time duration entries for the same day in the Excel data
            def has_duplicate_time_entries_df(df):
                seen = set()
                for _, row in df.iterrows():
                    date = str(row.get('Date') or row.get('date'))
                    start_time = str(row.get('Start Time') or row.get('start_time'))
                    end_time = str(row.get('End Time') or row.get('end_time'))
                    project_name = str(row.get('Project name') or row.get('project_name') or '')
                    if not date or not start_time or not end_time:
                        continue
                    key = (date, start_time, end_time)
                    if key in seen:
                        return True
                    seen.add(key)
                return False

            if has_duplicate_time_entries_df(df):
                default_storage.delete(temp_path)
                logger.error("Duplicate time duration entries found in uploaded Excel file")
                return JsonResponse({'success': False, 'message': 'Duplicate time duration entries for the same day are not allowed in the uploaded file.'})

            # New validation: For same task name on same date, start time of second entry should be > end time of previous entry
            def validate_task_time_entries_df(df):
                from datetime import datetime as dt

                grouped = {}
                for _, row in df.iterrows():
                    date = str(row.get('Date') or row.get('date'))
                    project_name = str(row.get('Project name') or row.get('project_name') or '')
                    task_name = str(row.get('Task Name') or row.get('task_name') or row.get('task') or row.get('name'))
                    start_time = str(row.get('Start Time') or row.get('start_time'))
                    end_time = str(row.get('End Time') or row.get('end_time'))
                    if not date or not task_name or not start_time or not end_time:
                        continue
                    key = (date, project_name, task_name)
                    if key not in grouped:
                        grouped[key] = []
                    grouped[key].append((start_time, end_time))

                def parse_time(t):
                    try:
                        return dt.strptime(t, '%I:%M %p').time()
                    except ValueError:
                        try:
                            return dt.strptime(t, '%H:%M').time()
                        except ValueError:
                            return None

                for key, times in grouped.items():
                    parsed_times = []
                    for st, et in times:
                        pst = parse_time(st)
                        pet = parse_time(et)
                        if pst is None or pet is None:
                            continue
                        parsed_times.append((pst, pet))

                    parsed_times.sort(key=lambda x: x[0])

                    for i in range(1, len(parsed_times)):
                        if parsed_times[i][0] <= parsed_times[i-1][1]:
                            return False, f"Start time {parsed_times[i][0]} is not after end time {parsed_times[i-1][1]} for task '{key[2]}' on date {key[0]}"
                return True, ""

            valid, error_msg = validate_task_time_entries_df(df)
            if not valid:
                default_storage.delete(temp_path)
                logger.error(f"Time validation error in uploaded Excel file: {error_msg}")
                return JsonResponse({'success': False, 'message': error_msg})

            csv_buffer = BytesIO()
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)

            csv_file_name = os.path.splitext(excel_file.name)[0] + '.csv'

            csv_path = f'timesheets/{csv_file_name}'
            if default_storage.exists(csv_path):
                default_storage.delete(csv_path)
            default_storage.save(csv_path, ContentFile(csv_buffer.read()))

            default_storage.delete(temp_path)

            existing_timesheet = Timesheet.objects.filter(consultant=consultant, month=month).first()
            replace_confirmed = request.POST.get('replace_confirmed', 'false').lower() == 'true'
            user_is_owner = request.user == consultant
            if existing_timesheet:
                if user_is_owner:
                    # Automatically replace if user is owner
                    existing_timesheet.file = csv_path
                    existing_timesheet.save()
                    timesheet = existing_timesheet
                else:
                    if not replace_confirmed:
                        # Inform frontend that a timesheet already exists and ask for confirmation
                        default_storage.delete(csv_path)
                        return JsonResponse({
                            'success': False,
                            'message': 'A timesheet for this month already exists. Do you want to replace it?',
                            'duplicate': True
                        })
                    else:
                        existing_timesheet.file = csv_path
                        existing_timesheet.save()
                        timesheet = existing_timesheet
            else:
                timesheet = Timesheet.objects.create(
                    consultant=consultant,
                    month=month,
                    file=csv_path,
                )

            logger.info(f"Timesheet uploaded and converted to CSV successfully by user {request.user.id} for month {year_str}-{month_str}")

            # Create ActivityLog entry for timesheet upload
            from custom_admin.utils import get_activitylog_url
            ActivityLog.objects.create(
                user=request.user,
                action_type='timesheet_upload',
                description=f"{request.user.email} uploaded a timesheet for {month.strftime('%B %Y')}",
                content_object=timesheet,
                url=get_activitylog_url('custom_admin:timesheet', query_params={'consultant_id': consultant.id, 'year': month.year, 'month': month.strftime('%m')})
            )

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
    from django.http import HttpResponseNotAllowed

    try:
        consultant = User.objects.get(id=consultant_id, role='consultant')
    except User.DoesNotExist:
        logger.error(f"Consultant with id {consultant_id} not found")
        raise Http404("Consultant not found")

    if request.method == 'POST':
        if 'scrap_agreement' in request.POST:
            return _handle_scrap_agreement(request, consultant)
        else:
            return _handle_profile_update(request, consultant, consultant_id)
    elif request.method == 'GET':
        try:
            profile = ConsultantProfile.objects.prefetch_related('skills').get(user=consultant)
        except ConsultantProfile.DoesNotExist:
            profile = ConsultantProfile(user=consultant)
        
        # Reload profile from DB to get latest status before rendering form
        profile.refresh_from_db()
        
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

        is_approved_status = False
        if profile.status and 'approved' in str(profile.status).lower():
            is_approved_status = True

        excluded_fields = ['status', 'name', 'profile_picture', 'cost_type', 'cost', 'weekly_commitment', 'availability']

        skills = Skill.objects.all()

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        import json
        initial_availability = {}
        logger.info(f"🎯 DEBUG: Profile availability for template: {profile.availability}")
        logger.info(f"🎯 DEBUG: Availability type: {type(profile.availability)}")
        
        try:
            if profile.availability:
                if isinstance(profile.availability, str):
                    initial_availability = json.loads(profile.availability)
                elif isinstance(profile.availability, dict):
                    initial_availability = profile.availability
                else:
                    initial_availability = {}
                logger.info(f"🎯 DEBUG: Parsed initial availability: {initial_availability}")
        except Exception as e:
            logger.error(f"Error loading availability JSON for user {consultant.email}: {str(e)}")
                
        # Serialize initial skills data as JSON
        # Convert Decimal to float for JSON serialization
        import decimal
        def decimal_to_float(obj):
            if isinstance(obj, decimal.Decimal):
                return float(obj)
            raise TypeError

        converted_skills = []
        for skill_exp in form.initial_skill_experiences:
            converted_skill_exp = skill_exp.copy()
            if 'experience_years' in converted_skill_exp and converted_skill_exp['experience_years'] is not None:
                converted_skill_exp['experience_years'] = float(converted_skill_exp['experience_years'])
            converted_skills.append(converted_skill_exp)

        initial_skills_json = json.dumps(converted_skills)

        context = {
            'consultant': consultant,
            'form': form,
            'current_page': 'Consultant Profile',
            'decrypted_password': decrypted_password,
            'is_approved_status': is_approved_status,
            'excluded_fields': excluded_fields,
            'skills': skills,
            'days': days,
            'initial_availability': json.dumps(initial_availability),
            'initial_skills_json': initial_skills_json,
        }
        return render(request, 'consultant_profile.html', context)
    else:
        return HttpResponseNotAllowed(['GET', 'POST'])
                    

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
    logger.info(f"🔥 ===== CONSULTANT PROFILE FORM SUBMISSION DEBUG =====")
    logger.info(f"📥 POST data keys: {list(request.POST.keys())}")
    logger.info(f"📥 POST data: {dict(request.POST)}")
    
    # Handle availability data specifically
    availability_data = request.POST.get('availability')
    logger.info(f"🎯 Availability data received: '{availability_data}'")
    logger.info(f"🎯 Availability data type: {type(availability_data)}")
    logger.info(f"🎯 Availability data length: {len(availability_data) if availability_data else 0}")
    
    try:
        profile = consultant.consultant_profile
    except ConsultantProfile.DoesNotExist:
        profile = ConsultantProfile(user=consultant)

    logger.debug(f"POST data keys: {list(request.POST.keys())}")
    logger.debug(f"POST data name field: {request.POST.get('name')}")
    logger.debug(f"POST data skills_data: {request.POST.get('skills_data')}")

    post_data = request.POST.copy()

    # Handle name field properly - don't override with "None None"
    name_value = post_data.get('name', '').strip()
    if not name_value:
        if hasattr(profile, 'name') and profile.name:
            name_value = profile.name
        else:
            name_value = f"{consultant.first_name} {consultant.last_name}".strip()
        post_data['name'] = name_value

    # Update User's first_name and last_name from the name field
    if name_value and name_value.lower() != 'none none':
        name_parts = name_value.split(' ', 1)
        consultant.first_name = name_parts[0]
        consultant.last_name = name_parts[1] if len(name_parts) > 1 else ''
        consultant.save()

    form = ConsultantProfileForm(post_data, request.FILES, instance=profile)
    if form.is_valid():
        try:
            logger.debug(f"Form instance before save: {form.instance}")
            instance = form.save(commit=False)
            logger.debug(f"Instance returned by form.save(commit=False): {instance}")
            if instance is None:
                raise ValueError("form.save(commit=False) returned None")
            instance.save()
            logger.info(f"Consultant profile updated successfully for user {consultant.email}")

            # Process availability data from POST
            logger.info(f"💾 Processing availability data...")
            if availability_data:
                try:
                    # Validate JSON format
                    parsed_availability = json.loads(availability_data)
                    logger.info(f"✅ JSON validation successful: {parsed_availability}")
                    
                    # Check current availability before saving
                    logger.info(f"📄 Profile availability before save: {instance.availability}")
                    
                    # Instead of saving as string, save as parsed JSON object
                    instance.availability = parsed_availability
                    instance.save()
                    
                    # Verify save was successful
                    instance.refresh_from_db()
                    logger.info(f"📄 Profile availability after save: {instance.availability}")
                    logger.info(f"✅ Availability data successfully saved to database!")

                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid availability JSON: {e}")
                except Exception as e:
                    logger.error(f"❌ Error saving availability: {e}")
                    # Try to save as empty object if there's an error
                    try:
                        instance.availability = {}
                        instance.save()
                        logger.info("Saved empty availability object as fallback")
                    except Exception as e2:
                        logger.error(f"❌ Even fallback failed: {e2}")
            else:
                logger.warning("⚠️  No availability data received in POST request")

            # Additional debug log for saved availability
            logger.info(f"🔍 Final saved availability in DB: {instance.availability}")
                # Process skills_data from POST
            skills_data_json = request.POST.get('skills_data', '[]')
            try:
                skills_data = json.loads(skills_data_json)
            except json.JSONDecodeError:
                skills_data = []
                logger.error(f"Invalid skills_data JSON for user {consultant.email}: {skills_data_json}")

            # Current skill ids submitted
            submitted_skill_ids = set()
            for skill_entry in skills_data:
                skill_id = skill_entry.get('skill_id')
                experience_years = skill_entry.get('experience_years')
                if skill_id is None:
                    continue
                submitted_skill_ids.add(int(skill_id))
                # Update or create ConsultantSkillExperience
                try:
                    skill_obj = Skill.objects.get(id=skill_id)
                    cse, created = ConsultantSkillExperience.objects.update_or_create(
                        consultant_profile=instance,
                        skill=skill_obj,
                        defaults={'experience_years': experience_years}
                    )
                except Skill.DoesNotExist:
                    logger.error(f"Skill with id {skill_id} does not exist for user {consultant.email}")

            # Remove ConsultantSkillExperience not in submitted skills
            ConsultantSkillExperience.objects.filter(
                consultant_profile=instance
            ).exclude(
                skill_id__in=submitted_skill_ids
            ).delete()

            messages.success(request, "Profile updated successfully!")
            return redirect('consultant:consultant_profile', consultant_id=consultant_id)
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
    from custom_admin.models import ActivityLog
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
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Month and invoice file are required.'})
            else:
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
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': 'Invalid month format. Please select a valid month.'})
                else:
                    messages.error(request, 'Invalid month format. Please select a valid month.')
                month_date = None

            if month_date:
                try:
                    # Check if invoice for this month already exists for the user
                    existing_invoice = Invoice.objects.filter(consultant=user, month=month_date).first()
                    if existing_invoice:
                        # Replace existing invoice file and update fields
                        if existing_invoice.file and existing_invoice.file.name:
                            existing_invoice.file.delete(save=False)
                        existing_invoice.file = invoice_file
                        existing_invoice.name = invoice_file.name
                        existing_invoice.status = 'awaiting_review'
                        existing_invoice.save()
                        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                            return JsonResponse({'success': True, 'message': 'Existing invoice replaced successfully and awaiting review.'})
                        else:
                            messages.success(request, 'Existing invoice replaced successfully and awaiting review.')
                        logger.info(f"Invoice replaced successfully for user {user.id}")

                        # Create ActivityLog entry for invoice replacement
                        ActivityLog.objects.create(
                            user=user,
                            action_type='invoice_upload',
                            description=f"{user.email} replaced an invoice for {month_date.strftime('%B %Y')}",
                            content_object=existing_invoice,
                            url=f"/auth/admin_invoices/?invoice_id={existing_invoice.id}"
                        )
                    else:
                        # Create new invoice
                        invoice = Invoice.objects.create(
                            consultant=user,
                            month=month_date,
                            file=invoice_file,
                            name=invoice_file.name,
                            status='awaiting_review'
                        )
                        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                            return JsonResponse({'success': True, 'message': 'Invoice uploaded successfully and awaiting review.'})
                        else:
                            messages.success(request, 'Invoice uploaded successfully and awaiting review.')
                        logger.info(f"Invoice saved successfully for user {user.id}")

                        # Create ActivityLog entry for new invoice upload
                        ActivityLog.objects.create(
                            user=user,
                            action_type='invoice_upload',
                            description=f"{user.email} uploaded a new invoice for {month_date.strftime('%B %Y')}",
                            content_object=invoice,
                            url=f"/auth/admin_invoices/?invoice_id={invoice.id}"
                        )
                except Exception as e:
                    logger.error(f"Error saving invoice: {str(e)}")
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'message': f'Error saving invoice: {str(e)}'})
                    else:
                        messages.error(request, f'Error saving invoice: {str(e)}')

    # Fetch invoices for the logged-in consultant
    invoices = Invoice.objects.filter(consultant=user).order_by('-month')

    context = {
        'current_page': 'Consultant Invoice',
        'invoices': invoices,
    }
    return render(request, 'consultant_invoice.html', context)

@login_required
@require_POST
def edit_invoice(request, invoice_id):
    """View to handle editing (replacing) an existing invoice file."""
    user = request.user
    if user.role != 'consultant':
        return JsonResponse({'success': False, 'message': 'Access denied'}, status=403)

    invoice = get_object_or_404(Invoice, id=invoice_id, consultant=user)

    new_file = request.FILES.get('invoice_file')
    if not new_file:
        return JsonResponse({'success': False, 'message': 'No file uploaded'}, status=400)

    try:
        # Delete old file
        if invoice.file and invoice.file.name:
            invoice.file.delete(save=False)

        # Update invoice with new file
        invoice.file = new_file
        invoice.name = new_file.name
        invoice.status = 'awaiting_review'
        invoice.save()

        return JsonResponse({'success': True, 'message': 'Invoice updated successfully'})
    except Exception as e:
        logger.error(f"Error updating invoice {invoice_id}: {str(e)}")
        return JsonResponse({'success': False, 'message': 'Error updating invoice'}, status=500)


@login_required
@require_POST
def delete_invoice(request, invoice_id):
    """View to handle deleting an invoice and its file."""
    user = request.user
    if user.role != 'consultant':
        return JsonResponse({'success': False, 'message': 'Access denied'}, status=403)

    invoice = get_object_or_404(Invoice, id=invoice_id, consultant=user)

    try:
        # Delete file from storage
        if invoice.file and invoice.file.name:
            invoice.file.delete(save=False)
        # Delete invoice record
        invoice.delete()

        return JsonResponse({'success': True, 'message': 'Invoice deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting invoice {invoice_id}: {str(e)}")
        return JsonResponse({'success': False, 'message': 'Error deleting invoice'}, status=500)


