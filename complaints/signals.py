from django.db.models import F
from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile, Vote, Complaint
from .models import ComplaintFollower, Notification, User


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return
    if created:
        Profile.objects.create(user=instance, user_type='citizen')

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if kwargs.get('raw'):
        return
    instance.profile.save()

@receiver(post_save, sender=Vote)
def increase_complaint_upvotes(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return
    if created:
        Complaint.objects.filter(pk=instance.complaint_id).update(upvotes=F('upvotes') + 1)

@receiver(post_delete, sender=Vote)
def decrease_complaint_upvotes(sender, instance, **kwargs):
    Complaint.objects.filter(pk=instance.complaint_id, upvotes__gt=0).update(upvotes=F('upvotes') - 1)

@receiver(post_save, sender=Complaint)
def notify_followers_on_update(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return


# Only notify followers when the complaint is updated (not on creation)
@receiver(post_save, sender=Complaint)
def notify_followers_on_update(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return

    # Only notify followers when the complaint is UPDATED (not on creation)
    if not created:
        followers = ComplaintFollower.objects.filter(complaint=instance).exclude(user=instance.citizen)
        if followers.exists():
            message = f"Complaint #{instance.id} has been updated."
            if instance.status:
                message += f" Status: {instance.get_status_display()}"
            if instance.government_response:
                message += f" Response: {instance.government_response[:60]}..."
            for follower in followers:
                Notification.objects.create(
                    recipient=follower.user,
                    complaint=instance,
                    notification_type='status_change',
                    message=message
                )    

@receiver(post_save, sender=Complaint)
def notify_govt_on_new_complaint(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return
    if created:
        # Notify all government users (or staff) about the new complaint
        gov_users = User.objects.filter(profile__user_type='govt')
        for user in gov_users:
            Notification.objects.create(
                recipient=user,
                complaint=instance,
                notification_type='new_complaint',
                message=f"New complaint #{instance.id} reported by {instance.citizen.username}"
            )
