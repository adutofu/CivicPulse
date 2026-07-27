import re

from django.contrib.auth.models import User

from .models import Notification


def send_notification(user, complaint, notification_type, message):
    """Create an in-app notification for a user."""
    if user:  # safety check
        Notification.objects.create(
            user=user,
            complaint=complaint,
            notification_type=notification_type,
            title=notification_type.replace('_', ' ').title(),
            message=message,
        )


def notify_mentions(text, sender, complaint):
    """
    Parse text for @username mentions and send notifications to mentioned users.
    Call after saving a comment or complaint.
    """
    usernames = re.findall(r'@(\w+)', text)
    for username in usernames:
        try:
            user = User.objects.get(username=username)
            send_notification(
                user,
                complaint,
                'mention',
                f"{sender.username} mentioned you in complaint #{complaint.id}"
            )
        except User.DoesNotExist:
            pass  # ignore invalid usernames