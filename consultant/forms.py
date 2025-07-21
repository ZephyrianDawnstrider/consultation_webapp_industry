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

    # Skills field will be handled dynamically in the template with JavaScript
    # We will pass the selected skills and their experiences via a hidden field or directly in the request.POST
    # For now, we remove it from the Meta.fields and handle it in save()
    # skills = forms.ModelMultipleChoiceField(
    #     queryset=Skill.objects.all(),
    #     widget=forms.CheckboxSelectMultiple,
    #     required=False
    # )

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
            'cost_type', # Added
            'cost',      # Added (renamed from cost_per_hour)
            'weekly_commitment', # Added
            'availability', # Added
            'total_experience', # Added
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
            'total_experience': forms.NumberInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'e.g. 5.0'}), # Added
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If instance exists, set initial values for cost and total_experience
        if self.instance and self.instance.pk:
            self.fields['cost'].initial = self.instance.cost
            self.fields['total_experience'].initial = self.instance.total_experience
            # Populate initial skills and their experiences for the template
            self.initial_skill_experiences = []
            for se in self.instance.skill_experiences.all():
                self.initial_skill_experiences.append({
                    'skill_id': se.skill.id,
                    'skill_name': se.skill.name,
                    'experience_years': se.experience_years
                })
        else:
            self.initial_skill_experiences = []


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
        if availability:
            try:
                # Attempt to parse JSON to validate format
                json.loads(availability)
            except json.JSONDecodeError:
                raise forms.ValidationError("Availability must be a valid JSON string.")
        return availability

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Handle skills and experiences
        # Get skills data from the request (will be sent via a hidden input or similar)
        skills_data_json = self.data.get('skills_data')
        
        if commit:
            instance.save() # Save the profile first to get an ID if it's new

            # Clear existing skill experiences for this profile
            instance.skill_experiences.all().delete()

            if skills_data_json:
                try:
                    skills_data = json.loads(skills_data_json)
                    for item in skills_data:
                        skill_id = item.get('skill_id')
                        experience = item.get('experience_years')
                        if skill_id:
                            try:
                                skill = Skill.objects.get(id=skill_id)
                                ConsultantSkillExperience.objects.create(
                                    consultant_profile=instance,
                                    skill=skill,
                                    experience_years=experience if experience else None
                                )
                            except Skill.DoesNotExist:
                                # Log or handle case where skill_id is invalid
                                pass
                except json.JSONDecodeError:
                    # Log or handle invalid JSON
                    pass
        return instance

