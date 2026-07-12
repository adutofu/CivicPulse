from django import forms
from .models import Complaint, ComplaintImage, Profile

class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['category', 'description', 'photo']  # 'latitude', 'longitude']

# additon of multiple image
class ExtraImageForm(forms.ModelForm):
    class Meta:
        model = ComplaintImage
        fields = ['image']

# government officer application form (ID verification)
class GovtApplicationForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['agency', 'id_card']