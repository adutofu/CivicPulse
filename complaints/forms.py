from django import forms
from .models import Complaint
from .models import ComplaintImage

class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['category', 'description', 'photo', 'latitude', 'longitude']

# additon of multiple image

class ExtraImageForm(forms.ModelForm):
    class Meta:
        model = ComplaintImage
        fields = ['image']