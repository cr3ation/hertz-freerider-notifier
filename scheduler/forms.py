from django import forms
from .models import SavedSearch

class SavedSearchForm(forms.ModelForm):
    class Meta:
        model = SavedSearch
        fields = ['date_from', 'date_to', 'origin', 'destination']
        widgets = {
            'date_from': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_to': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'origin': forms.TextInput(attrs={'class': 'form-control'}),
            'destination': forms.TextInput(attrs={'class': 'form-control'}),
        }
