from django.db import models
from django.contrib.auth.models import User
#just added to test if it would fix the error



#to see if this would fix the issue at hand.


CATEGORY_CHOICES = [
    ('roads', 'Bad Roads'),
    ('lights', 'Broken Lights'),
    ('flooding', 'Flooding'),
    ('waste', 'Waste'),
    ('corruption', 'Corruption Signal'),
    ('water', 'Water Issues'),
]

STATUS_CHOICES = [
    ('reported', 'Reported'),
    ('under_review', 'Under Review'),
    ('in_progress', 'In Progress'),
    ('resolved', 'Resolved'),
]

class Complaint(models.Model):
    citizen = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField()
    photo = models.ImageField(upload_to='complaints/', blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    address_text = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='reported')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    government_response = models.TextField(blank=True, null=True)
    resolved_photo = models.ImageField(upload_to='resolved/', blank=True, null=True)

    def __str__(self):
        return f"{self.category} - {self.created_at.date()}"

class GovernmentUpdate(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    before_after_photos = models.ImageField(upload_to='gov_updates/', blank=True)
    published_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    

#USER Profile. both for citizen and for goverment
class Profile(models.Model):
    USER_TYPES = (
        ('citizen', 'Citizen'),
        ('govt', 'Government Officer'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='citizen')
    agency = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.user_type}"
    
# code for murtiple pictures 
class ComplaintImage(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='extra_images')
    image = models.ImageField(upload_to='complaint_extra/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image for complaint #{self.complaint.id}"
    