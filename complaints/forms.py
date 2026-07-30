from django import forms
from .models import Complaint, ComplaintImage, Profile

class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['category', 'description', 'photo', 'address_text']

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


# profile settings — used by both citizen and govt accounts
class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_picture', 'bio', 'phone_number']

# government coverage area — used only on the govt profile settings page
class GovtCoverageForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['assigned_state', 'assigned_lga']