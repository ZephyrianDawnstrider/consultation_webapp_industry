from django import forms
from .models import ProspectiveConsultant

class ProspectiveConsultantForm(forms.ModelForm):
    class Meta:
        model = ProspectiveConsultant
        fields = ['name', 'email', 'phone', 'consultant_field', 'other_consultant_field']

    def clean(self):
        cleaned_data = super().clean()
        consultant_field = cleaned_data.get('consultant_field')
        other_field = cleaned_data.get('other_consultant_field')

        if consultant_field == 'Other' and not other_field:
            self.add_error('other_consultant_field', 'Please specify the consultantion field.')
        return cleaned_data
