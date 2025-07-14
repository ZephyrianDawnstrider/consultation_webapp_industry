from django.contrib import admin
from django import forms
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from .models import User, Skill, Invoice
from consultant.models import ConsultantProfile
from cryptography.fernet import Fernet

FERNET_KEY = Fernet.generate_key()
fernet = Fernet(FERNET_KEY)

class ConsultantCreationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'consultant'
        # Generate a random password
        raw_password = get_random_string(length=10)
        # Encrypt the password
        encrypted_password = fernet.encrypt(raw_password.encode()).decode()
        user.encrypted_password = encrypted_password
        user.set_unusable_password()
        if commit:
            user.save()
            # Send welcome email
            subject = 'Welcome to the Platform - Complete Your Consultant Registration'
            message = f'Dear Consultant,\n\nYour account has been created.\n\nLogin: {user.email}\nPassword: {raw_password}\n\nPlease complete your registration using the link provided.\n\nRegards,\nAdmin Team'
            send_mail(subject, message, 'admin@platform.com', [user.email], fail_silently=False)
        return user

class ConsultantAdmin(admin.ModelAdmin):
    form = ConsultantCreationForm
    list_display = ('email', 'role', 'is_active')
    readonly_fields = ('role',)

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'consultant', 'month', 'status', 'uploaded_at')
    list_filter = ('month', 'consultant', 'status')
    search_fields = ('name', 'consultant__email')
    list_editable = ('status',)

admin.site.register(User)
admin.site.register(Skill)
admin.site.register(ConsultantProfile)

from consultant.models import Timesheet

@admin.register(Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    list_display = ('consultant', 'month', 'status', 'uploaded_at')
    list_filter = ('month', 'consultant', 'status')
    search_fields = ('consultant__email',)
    list_editable = ('status',)

admin.site.unregister(User)
admin.site.register(User, ConsultantAdmin)
