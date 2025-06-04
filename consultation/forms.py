from django import forms
from consultation.models import ConsultantProfile
from custom_admin.models import Skill


class ConsultantProfileForm(forms.ModelForm):
    name = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Enter full name'}))
    mobile = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Enter mobile number'}))
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = ConsultantProfile
        fields = [
            'name',
            'mobile',
            'skills',
            'bank_account_name',
            'bank_account_number',
            'bank_ifsc',
            'bank_branch_name',
            'bank_name',
            'cost_per_hour',
            'status',
            'agreement_document',
        ]
        widgets = {
            'status': forms.Select(choices=[
                ('approved', 'Approved'),
                ('rejected', 'Rejected'),
                ('to_be_reviewed', 'To Be Reviewed'),
            ], attrs={'class': 'form-control'}),

            'bank_account_name': forms.TextInput(attrs={'placeholder': 'e.g. John Doe', 'class': 'form-control shadow-sm'}),
            'bank_account_number': forms.TextInput(attrs={'placeholder': 'e.g. 1234567890', 'class': 'form-control shadow-sm'}),
            'bank_ifsc': forms.TextInput(attrs={'placeholder': 'e.g. ABCD0123456', 'class': 'form-control shadow-sm'}),
            'bank_branch_name': forms.TextInput(attrs={'placeholder': 'e.g. Main Branch', 'class': 'form-control shadow-sm'}),
            'bank_name': forms.TextInput(attrs={'placeholder': 'e.g. Bank of Example', 'class': 'form-control shadow-sm'}),
            'cost_per_hour': forms.NumberInput(attrs={'placeholder': 'e.g. 50.00', 'class': 'form-control shadow-sm'}),
        }
    
    def clean_agreement_document(self):
        agreement = self.cleaned_data.get('agreement_document')
        if agreement:
            if not agreement.name.lower().endswith('.pdf'):
                raise forms.ValidationError("Only PDF files are allowed for the agreement document.")
            # content_type attribute is not available on FieldFile, check file extension only
            # if hasattr(agreement, 'content_type') and agreement.content_type != 'application/pdf':
            #     raise forms.ValidationError("Uploaded file is not a valid PDF.")
        return agreement
