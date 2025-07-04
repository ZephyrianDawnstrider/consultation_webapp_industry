from custom_admin.models import User
from consultation.models import ConsultantProfile
from datetime import datetime

def timesheet_sidebar_context(request):
    """
    Context processor to add consultants list and date/year options for timesheet sidebar.
    """
    consultants = User.objects.filter(role='consultant').select_related('consultant_profile').order_by('consultant_profile__name')
    today = datetime.today()
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
    selected_year = request.GET.get('year')
    selected_month = request.GET.get('month')
    if not selected_year:
        selected_year = current_year
    else:
        try:
            selected_year = int(selected_year)
        except ValueError:
            selected_year = current_year
    if not selected_month:
        selected_month = today.strftime('%m')

    return {
        'consultants': consultants,
        'year_options': year_options,
        'month_options': month_options,
        'selected_year': selected_year,
        'selected_month': selected_month,
    }
