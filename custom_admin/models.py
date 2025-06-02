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

    def __str__(self):
        return self.name

class ConsultantProfile(models.Model):
    STATUS_CHOICES = (
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('to_be_reviewed', 'To Be Reviewed'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='consultant_profile')
    bank_account_name = models.CharField(max_length=255)
    bank_account_number = models.CharField(max_length=50)
    bank_ifsc = models.CharField(max_length=20)
    bank_branch_name = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=255)
    cost_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    skills = models.ManyToManyField(Skill)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='to_be_reviewed')

    def __str__(self):
        return f"{self.user.email} Profile"

class Timesheet(models.Model):
    consultant = models.ForeignKey('User', on_delete=models.CASCADE, limit_choices_to={'role': 'consultant'})
    month = models.DateField()
    file = models.FileField(upload_to='timesheets/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Timesheet for {self.consultant.email} - {self.month.strftime('%B %Y')}"

class Invoice(models.Model):
    STATUS_CHOICES = (
        ('approved', 'Approved'),
        ('pending', 'Pending'),
        ('rejected', 'Rejected'),
        ('awaiting_review', 'Awaiting Review'),
    )
    consultant = models.ForeignKey('User', on_delete=models.CASCADE, limit_choices_to={'role': 'consultant'})
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
    consultation_field = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session Booking by {self.name} ({self.email})"
