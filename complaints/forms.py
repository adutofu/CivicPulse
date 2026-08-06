from django import forms
from django.core.validators import FileExtensionValidator
from .models import Complaint, ComplaintImage, Profile

MAX_GOVT_APPLICATION_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

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
    id_card = forms.FileField(
        required=True,
        validators=[FileExtensionValidator(['pdf', 'docx'])],
        widget=forms.ClearableFileInput(attrs={'accept': '.pdf,.docx'}),
        help_text='Upload a PDF or DOCX document no larger than 5MB.'
    )

    class Meta:
        model = Profile
        fields = ['agency', 'id_card']

    def clean_id_card(self):
        file = self.cleaned_data.get('id_card')
        if not file:
            raise forms.ValidationError('Please upload a PDF or DOCX document before submitting your application.')
        if file.size > MAX_GOVT_APPLICATION_FILE_SIZE:
            raise forms.ValidationError('Uploaded file must be 5MB or smaller.')
        return file


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