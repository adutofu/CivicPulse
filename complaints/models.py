from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

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
    upvotes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    government_response = models.TextField(blank=True, null=True)
    resolved_photo = models.ImageField(upload_to='resolved/', blank=True, null=True)

    def __str__(self):
        return f"{self.category} - {self.created_at.date()}"

    def has_vote_from(self, user):
        if not user.is_authenticated:
            return False
        return self.votes.filter(user=user).exists()

class GovernmentUpdate(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    before_after_photos = models.ImageField(upload_to='gov_updates/', blank=True)
    published_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
# notification model and utility functions for creating notifications based on complaint updates and new complaints

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('status_change', 'Status Change'),
        ('govt_response', 'Government Response'),
        ('resolved_photo', 'Resolution Photo Added'),
        ('new_complaint', 'New Complaint (Govt Only)'),
        ('complaint_reminder', 'Complaint Reminder (Govt Only)'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, null=True, blank=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}: {self.title}"


class Vote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='votes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'complaint')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} upvoted complaint #{self.complaint_id}"


# Notification utility functions
def create_notification(user, complaint, notification_type, title, message):
    """Create a notification for a user"""
    return Notification.objects.create(
        user=user,
        complaint=complaint,
        notification_type=notification_type,
        title=title,
        message=message
    )

def notify_status_change(complaint, old_status, new_status):
    """Notify citizen when complaint status changes"""
    if old_status != new_status:
        create_notification(
            user=complaint.citizen,
            complaint=complaint,
            notification_type='status_change',
            title=f'Complaint Status Updated',
            message=f'Your complaint "{complaint.get_category_display()}" status changed from {complaint.get_status_display()} to {dict(STATUS_CHOICES)[new_status]}'
        )

def notify_govt_response(complaint):
    """Notify citizen when government adds response"""
    if complaint.government_response:
        create_notification(
            user=complaint.citizen,
            complaint=complaint,
            notification_type='govt_response',
            title='Government Response Added',
            message=f'Government has responded to your complaint: "{complaint.description[:50]}..."'
        )

def notify_resolved_photo(complaint):
    """Notify citizen when resolution photo is added"""
    if complaint.resolved_photo:
        create_notification(
            user=complaint.citizen,
            complaint=complaint,
            notification_type='resolved_photo',
            title='Resolution Photo Added',
            message=f'A resolution photo has been added to your complaint: "{complaint.description[:50]}..."'
        )

def notify_new_complaint_govt(complaint):
    """Notify all government users of new complaint"""
    from django.contrib.auth.models import User
    govt_users = User.objects.filter(profile__user_type='govt')
    for govt_user in govt_users:
        create_notification(
            user=govt_user,
            complaint=complaint,
            notification_type='new_complaint',
            title='New Complaint Reported',
            message=f'New complaint: {complaint.get_category_display()} - {complaint.description[:50]}...'
        )

def notify_govt_application_submitted(profile):
    """Notify all admins when a citizen applies to become a Government Officer"""
    from django.contrib.auth.models import User
    admins = User.objects.filter(is_staff=True)
    for admin_user in admins:
        create_notification(
            user=admin_user,
            complaint=None,
            notification_type='new_complaint',  # reuses existing type; add 'govt_application' below if you want a dedicated one
            title='New Government Officer Application',
            message=f'{profile.user.username} has applied to become a Government Officer and is awaiting ID verification.'
        )

def notify_govt_application_reviewed(profile):
    """Notify the applicant once an admin approves or rejects their application"""
    create_notification(
        user=profile.user,
        complaint=None,
        notification_type='status_change',  # reuses existing type; see note above
        title='Government Officer Application Reviewed',
        message=f'Your application to become a Government Officer was {profile.verification_status}.'
    )

def create_govt_reminders():
    """Create reminder notifications for government users about pending complaints"""
    from django.contrib.auth.models import User
    from django.utils import timezone
    from datetime import timedelta
    
    # Get complaints pending for more than 3 days
    three_days_ago = timezone.now() - timedelta(days=3)
    pending_complaints = Complaint.objects.filter(
        status__in=['reported', 'under_review'],
        created_at__lt=three_days_ago
    )
    
    govt_users = User.objects.filter(profile__user_type='govt')
    for govt_user in govt_users:
        for complaint in pending_complaints:
            # Check if reminder already exists for this complaint in last 24 hours
            recent_reminder = Notification.objects.filter(
                user=govt_user,
                complaint=complaint,
                notification_type='complaint_reminder',
                created_at__gt=timezone.now() - timedelta(hours=24)
            ).exists()
            
            if not recent_reminder:
                create_notification(
                    user=govt_user,
                    complaint=complaint,
                    notification_type='complaint_reminder',
                    title='Pending Complaint Reminder',
                    message=f'Complaint "{complaint.description[:50]}..." has been pending for {(timezone.now() - complaint.created_at).days} days'
                )


#USER Profile. both for citizen and for goverment
class Profile(models.Model):
    USER_TYPES = (
        ('citizen', 'Citizen'),
        ('govt', 'Government Officer'),
    )

    VERIFICATION_STATUS = (
        ('not_applicable', 'Not Applicable'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='citizen')
    agency = models.CharField(max_length=100, blank=True)

    # --- Government official verification fields ---
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='not_applicable')
    id_card = models.ImageField(upload_to='govt_ids/', blank=True, null=True)
    applied_at = models.DateTimeField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='verified_profiles'
    )

    def __str__(self):
        return f"{self.user.username} - {self.user_type}"

    def is_verified_govt(self):
        return self.user_type == 'govt' and self.verification_status == 'approved'
    
# code for murtiple pictures 
class ComplaintImage(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='extra_images')
    image = models.ImageField(upload_to='complaint_extra/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image for complaint #{self.complaint.id}"
    