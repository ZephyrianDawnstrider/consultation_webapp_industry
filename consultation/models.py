from django.db import models
from django.conf import settings
from custom_admin.models import ConsultantStatus
from custom_admin.constants import TIMESHEET_STATUS_CHOICES, INVOICE_STATUS_CHOICES

class ConsultantProfile(models.Model):
    name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='consultant_profile')
    bank_account_name = models.CharField(max_length=255)
    bank_account_number = models.CharField(max_length=50)
    bank_ifsc = models.CharField(max_length=20)
    bank_branch_name = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=255)
    cost_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.ForeignKey(ConsultantStatus, on_delete=models.SET_NULL, null=True, blank=True, related_name='consultation_profiles')
    agreement_document = models.FileField(upload_to='agreements/', blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    skills = models.ManyToManyField('custom_admin.Skill', blank=True, related_name='consultant_profiles')

    def __str__(self):
        return f"{self.user.email} Profile"

class Timesheet(models.Model):
    consultant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'role': 'consultant'}, related_name='consultation_timesheets')
    month = models.DateField()
    file = models.FileField(upload_to='timesheets/')
    status = models.CharField(max_length=20, choices=TIMESHEET_STATUS_CHOICES, default='awaiting_review')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Timesheet for {self.consultant.email} - {self.month.strftime('%B %Y')}"

class TimesheetEntry(models.Model):
    timesheet = models.ForeignKey(Timesheet, on_delete=models.CASCADE, related_name='entries')
    date = models.DateField()
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2)
    project = models.CharField(max_length=255, blank=True, null=True)
    task_name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.timesheet.consultant.email} - {self.date} - {self.hours_worked} hours - {self.task_name}"

class Invoice(models.Model):
    consultant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'role': 'consultant'}, related_name='consultation_invoices')
    name = models.CharField(max_length=255)
    month = models.DateField()
    file = models.FileField(upload_to='invoices/')
    status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='awaiting_review')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invoice {self.name} for {self.consultant.email} - {self.month.strftime('%B %Y')}"
