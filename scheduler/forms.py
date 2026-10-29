from django import forms

from .models import SavedSearch


class SavedSearchForm(forms.ModelForm):
    class Meta:
        model = SavedSearch
        fields = ['date_from', 'date_to', 'origin', 'destination']
        widgets = {
            'date_from': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_to': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            # "hertz-locations" is a <datalist> of all Hertz stations rendered by the dashboard
            'origin': forms.TextInput(
                attrs={'class': 'form-control', 'list': 'hertz-locations', 'placeholder': 'e.g. Stockholm*'}
            ),
            'destination': forms.TextInput(
                attrs={'class': 'form-control', 'list': 'hertz-locations', 'placeholder': 'e.g. * (anywhere)'}
            ),
        }

    def clean(self):
        cleaned = super().clean()
        date_from, date_to = cleaned.get('date_from'), cleaned.get('date_to')
        if date_from and date_to and date_from > date_to:
            self.add_error('date_to', '"Date to" must be on or after "Date from".')
        return cleaned
