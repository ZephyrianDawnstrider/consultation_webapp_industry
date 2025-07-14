from django import forms
from .models import ConsultantStatus, Skill
from consultant.models import ConsultantProfile
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class ConsultantRegistrationForm(forms.Form):
    """Form for consultant registration with required fields: mobile, email, agreement"""
    name = forms.CharField(max_length=100, label="Full Name")
    mobile = forms.CharField(max_length=20, label="Mobile Number")
    email = forms.EmailField(label="Email Address")
    agreement = forms.BooleanField(label="Agreement Accepted")

class ConsultantEditForm(forms.ModelForm):
    """Form for editing consultant profile information including banking, professional info, and status"""
    
    from .models import CONSULTANT_STATUS_CHOICES
    from django.forms import Select, PasswordInput
    from .models import CONSULTANT_STATUS_CHOICES
    status = forms.ChoiceField(choices=CONSULTANT_STATUS_CHOICES, widget=Select(attrs={'class': 'form-control'}), required=False)
    password = forms.CharField(
        label="Password",
        widget=PasswordInput(render_value=True),
        required=False,
        help_text="Leave blank if you do not want to change the password."
    )
    
    class Meta:
        model = ConsultantProfile
        fields = [
            'name',
            'mobile',
            'bank_account_name',
            'bank_account_number',
            'bank_ifsc',
            'bank_branch_name',
            'bank_name',
            'cost_per_hour',
            'skills',
            'agreement_document',
            'details',
            # 'status',  # Exclude status from fields to avoid direct assignment error
        ]
    
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Skills",
        required=False
    )
    agreement_document = forms.FileField(required=False)
    details = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial status value as string from ConsultantStatus instance
        if 'instance' in kwargs and kwargs['instance'] is not None:
            status_instance = getattr(kwargs['instance'], 'status', None)
            if status_instance is not None:
                self.fields['status'].initial = status_instance.status
            else:
                self.fields['status'].initial = 'to_be_reviewed'
        else:
            self.fields['status'].initial = 'to_be_reviewed'

    def save(self, commit=True):
        instance = super().save(commit=False)
        from .models import ConsultantStatus
        status_value = self.cleaned_data.get('status')
        if status_value:
            try:
                status_instance = ConsultantStatus.objects.get(user=instance.user)
                status_instance.status = status_value
                status_instance.save()
                instance.status = status_instance
            except ConsultantStatus.DoesNotExist:
                status_instance = ConsultantStatus.objects.create(user=instance.user, status=status_value)
                instance.status = status_instance
        if commit:
            instance.save()
            self.save_m2m()
        return instance

from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class AdminProfileForm(forms.ModelForm):
    """Form for editing admin profile information"""
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(render_value=True),
        required=False,
        help_text="Leave blank if you do not want to change the password."
    )

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'phone_number',
            'email',
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user
