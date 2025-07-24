from django.db import models
from django.conf import settings
from custom_admin.models import ConsultantStatus, Skill # Import Skill model
from custom_admin.constants import TIMESHEET_STATUS_CHOICES, INVOICE_STATUS_CHOICES

class ConsultantProfile(models.Model):
    name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='consultant_profile')
    linkedin_profile = models.URLField(max_length=500, blank=True, null=True)
    bank_account_name = models.CharField(max_length=255)
    bank_account_number = models.CharField(max_length=50)
    bank_ifsc = models.CharField(max_length=20)
    bank_branch_name = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=255)
    COST_TYPE_CHOICES = [
        ('hourly', 'Cost per Hour'),
        ('monthly', 'Monthly Cost'),
    ]
    cost_type = models.CharField(max_length=10, choices=COST_TYPE_CHOICES, default='hourly')
    # Renamed from cost_per_hour to cost, and made blank/null true
    cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    weekly_commitment = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Hours per week willing to consult")
    availability = models.CharField(max_length=255, blank=True, null=True, help_text="Availability as text, e.g., Mon-Fri, 9 AM - 5 PM")
    status = models.ForeignKey(ConsultantStatus, on_delete=models.SET_NULL, null=True, blank=True, related_name='consultant_profiles')
    agreement_document = models.FileField(upload_to='agreements/', blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    total_experience = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True, help_text="Total years of professional experience")
    # Updated skills to use a through model
    skills = models.ManyToManyField(Skill, blank=True, related_name='consultant_profiles', through='ConsultantSkillExperience')

    def __str__(self):
        return f"{self.user.email} Profile"

class Timesheet(models.Model):
    consultant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'role': 'consultant'}, related_name='consultant_timesheets')
    month = models.DateField()
    file = models.FileField(upload_to='timesheets/')
    status = models.CharField(max_length=20, choices=TIMESHEET_STATUS_CHOICES, default='awaiting_review')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('consultant', 'month')

    def __str__(self):
        return f"Timesheet for {self.consultant.email} - {self.month.strftime('%B %Y')}"

class ConsultantSkillExperience(models.Model):
    consultant_profile = models.ForeignKey(ConsultantProfile, on_delete=models.CASCADE, related_name='skill_experiences')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    experience_years = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True, help_text="Years of experience in this skill")

    class Meta:
        unique_together = ('consultant_profile', 'skill')

    def __str__(self):
        return f"{self.consultant_profile.user.email} - {self.skill.name} ({self.experience_years} years)"

class Invoice(models.Model):
    consultant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'role': 'consultant'}, related_name='consultant_invoices')
    name = models.CharField(max_length=255)
    month = models.DateField()
    file = models.FileField(upload_to='invoices/')
    status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='awaiting_review')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invoice {self.name} for {self.consultant.email} - {self.month.strftime('%B %Y')}"

