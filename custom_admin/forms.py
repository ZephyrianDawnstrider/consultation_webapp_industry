from django import forms
from .models import ConsultantStatus, Skill
from consultation.models import ConsultantProfile

class ConsultantRegistrationForm(forms.Form):
    """Form for consultant registration with required fields: mobile, email, agreement"""
    name = forms.CharField(max_length=100, label="Full Name")
    mobile = forms.CharField(max_length=20, label="Mobile Number")
    email = forms.EmailField(label="Email Address")
    agreement = forms.BooleanField(label="Agreement Accepted")

class ConsultantEditForm(forms.ModelForm):
    """Form for editing consultant profile information including banking, professional info, and status"""
    
    status = forms.ModelChoiceField(
        queryset=ConsultantStatus.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
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
            'status',
            'agreement_document',
            'details',
        ]
    
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Skills"
    )
    agreement_document = forms.FileField(required=False)
    details = forms.CharField(widget=forms.Textarea, required=False)
