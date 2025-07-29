
from django import forms
from consultant.models import ConsultantProfile, ConsultantSkillExperience
from custom_admin.models import Skill
import json

class ConsultantProfileForm(forms.ModelForm):
    name = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Enter full name'}))
    mobile = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Enter mobile number'}))
    
    # New fields for cost type, cost, weekly commitment, and availability
    COST_TYPE_CHOICES = [
        ('hourly', 'Cost per Hour'),
        ('monthly', 'Monthly Cost'),
    ]
    cost_type = forms.ChoiceField(choices=COST_TYPE_CHOICES, widget=forms.Select(attrs={'class': 'form-control shadow-sm'}))
    cost = forms.DecimalField(max_digits=10, decimal_places=2, required=False, widget=forms.NumberInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'e.g. 50.00'}))
    weekly_commitment = forms.DecimalField(max_digits=5, decimal_places=2, required=False, widget=forms.NumberInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'e.g. 10.00'}), help_text="Hours per week willing to consult")
    availability = forms.JSONField(required=False, widget=forms.Textarea(attrs={'class': 'form-control shadow-sm', 'placeholder': 'e.g. {"Monday": "9:00-17:00"}'}), help_text="Availability as JSON: days and time ranges")

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
            'cost_type', 
            'cost',      
            'weekly_commitment', 
            'availability',
            'total_experience',
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
            'total_experience': forms.NumberInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'e.g. 5.0'}), 
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If instance exists, set initial values for cost and total_experience
        if self.instance and self.instance.pk:
            self.fields['cost'].initial = self.instance.cost
            self.fields['total_experience'].initial = self.instance.total_experience
            # Priority: instance.name > user's full name > empty
            if self.instance.name:
                self.fields['name'].initial = self.instance.name
            elif hasattr(self.instance, 'user') and self.instance.user:
                full_name = f"{self.instance.user.first_name} {self.instance.user.last_name}".strip()
                if full_name and full_name != " ":
                    self.fields['name'].initial = full_name
            # Populate initial skills and their experiences for the template
            self.initial_skill_experiences = []
            for se in self.instance.skill_experiences.all():
                self.initial_skill_experiences.append({
                    'skill_id': se.skill.id,
                    'skill_name': se.skill.name,
                    'experience_years': se.experience_years
                })
            # Set status field widget to disabled (readonly)
            self.fields['status'].widget.attrs['disabled'] = 'disabled'
        else:
            self.initial_skill_experiences = []
                
                    

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            if self.instance and self.instance.name:
                return self.instance.name
            elif self.instance and hasattr(self.instance, 'user') and self.instance.user:
                full_name = f"{self.instance.user.first_name} {self.instance.user.last_name}".strip()
                if full_name and full_name != " ":
                    return full_name
            raise forms.ValidationError("Name is required.")
        return name

    def clean_agreement_document(self):
        agreement = self.cleaned_data.get('agreement_document')
        if agreement:
            if not agreement.name.lower().endswith('.pdf'):
                raise forms.ValidationError("Only PDF files are allowed for the agreement document.")
        return agreement

    def clean_weekly_commitment(self):
        weekly_commitment = self.cleaned_data.get('weekly_commitment')
        if weekly_commitment is not None and weekly_commitment < 0:
            raise forms.ValidationError("Weekly commitment cannot be negative.")
        return weekly_commitment

    def clean_availability(self):
        availability = self.cleaned_data.get('availability')
        if availability is not None:
            if not isinstance(availability, dict):
                raise forms.ValidationError("Availability must be a valid JSON object.")
            try:
                # Validate it can be serialized to JSON
                json.dumps(availability)
            except (TypeError, ValueError) as e:
                raise forms.ValidationError(f"Availability must be serializable to JSON: {str(e)}")
            
            # Additional validation: check time ranges format
            for day, ranges in availability.items():
                if not isinstance(ranges, list):
                    raise forms.ValidationError(f"Availability for {day} must be a list of time ranges.")
                for time_range in ranges:
                    if not isinstance(time_range, str) or '-' not in time_range:
                        raise forms.ValidationError(f"Invalid time range format '{time_range}' for {day}. Expected format 'HH:MM-HH:MM'.")
                    start, end = time_range.split('-', 1)
                    # Basic time format check HH:MM
                    import re
                    time_pattern = re.compile(r'^\d{2}:\d{2}$')
                    if not time_pattern.match(start) or not time_pattern.match(end):
                        raise forms.ValidationError(f"Invalid time format in range '{time_range}' for {day}. Expected 'HH:MM-HH:MM'.")
        return availability
            
    def save(self, commit=True):
        instance = super().save(commit=commit)
        # Skills handling is now done in the view
        return instance

