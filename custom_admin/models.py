from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from cryptography.fernet import Fernet
from django.conf import settings

from django.conf import settings

# Use a static Fernet key from Django settings or environment variable
FERNET_KEY = getattr(settings, 'FERNET_KEY', None)
if not FERNET_KEY:
    raise ValueError("FERNET_KEY must be set in Django settings")

fernet = Fernet(FERNET_KEY)

class UserManager(BaseUserManager):
    def create_user(self, email, role, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        if role == 'admin':
            user.set_password(password)
        elif role == 'consultant':
            # Encrypt the password using Fernet
            encrypted_password = fernet.encrypt(password.encode()).decode()
            user.encrypted_password = encrypted_password
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, role='admin', password=password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('consultant', 'Consultant'),
    )
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    encrypted_password = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_admin_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_admin_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['role']

    def check_consultant_password(self, raw_password):
        if self.role != 'consultant' or not self.encrypted_password:
            return False
        try:
            decrypted_password = fernet.decrypt(self.encrypted_password.encode()).decode()
            return decrypted_password == raw_password
        except:
            return False

    def __str__(self):
        return self.email

class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'custom_admin_skill_master'

    def __str__(self):
        return self.name

from custom_admin.constants import TIMESHEET_STATUS_CHOICES, INVOICE_STATUS_CHOICES, CONSULTANT_STATUS_CHOICES

class ConsultantStatus(models.Model):
    STATUS_CHOICES = CONSULTANT_STATUS_CHOICES
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='consultant_status')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='to_be_reviewed')

    def __str__(self):
        return f"{self.user.email} Status: {self.status}"

# Removed ConsultantProfile model from custom_admin/models.py as per user request.

from consultant.models import Timesheet as consultantTimesheet, Invoice as consultantInvoice

class Timesheet(models.Model):
    consultant = models.ForeignKey('User', on_delete=models.CASCADE, limit_choices_to={'role': 'consultant'})
    consultant_timesheet = models.ForeignKey(consultantTimesheet, on_delete=models.CASCADE, related_name='custom_admin_timesheets', null=True, blank=True)
    month = models.DateField()
    file = models.FileField(upload_to='timesheets/')
    status = models.CharField(max_length=20, choices=TIMESHEET_STATUS_CHOICES, default='awaiting_review')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Timesheet for {self.consultant.email} - {self.month.strftime('%B %Y')}"

from consultant.models import Timesheet as consultantTimesheet, Invoice as consultantInvoice

class Invoice(models.Model):
    STATUS_CHOICES = INVOICE_STATUS_CHOICES
    consultant = models.ForeignKey('User', on_delete=models.CASCADE, limit_choices_to={'role': 'consultant'})
    consultant_invoice = models.ForeignKey(consultantInvoice, on_delete=models.CASCADE, related_name='custom_admin_invoices', null=True, blank=True)
    name = models.CharField(max_length=255)
    month = models.DateField()
    file = models.FileField(upload_to='invoices/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='awaiting_review')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invoice {self.name} for {self.consultant.email} - {self.month.strftime('%B %Y')}"

class SessionBooking(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    consultant_field = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session Booking by {self.name} ({self.email})"

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.auth import get_user_model

User = get_user_model()

class ActivityLog(models.Model):
    ACTION_TYPES = [
        ('timesheet_upload', 'Timesheet Upload'),
        ('invoice_upload', 'Invoice Upload'),
        ('prospective_consultant', 'Prospective Consultant Submission'),
        # Add more action types as needed
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    description = models.TextField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    url = models.CharField(max_length=255, blank=True)  # URL to the related object/page
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.get_action_type_display()} - {self.timestamp}"
