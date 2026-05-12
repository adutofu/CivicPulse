from django.db.models import F
from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile, Vote, Complaint

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, user_type='citizen')

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

@receiver(post_save, sender=Vote)
def increase_complaint_upvotes(sender, instance, created, **kwargs):
    if created:
        Complaint.objects.filter(pk=instance.complaint_id).update(upvotes=F('upvotes') + 1)

@receiver(post_delete, sender=Vote)
def decrease_complaint_upvotes(sender, instance, **kwargs):
    Complaint.objects.filter(pk=instance.complaint_id, upvotes__gt=0).update(upvotes=F('upvotes') - 1)
