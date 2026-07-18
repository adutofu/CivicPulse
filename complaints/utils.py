from .models import Notification
import re
from django.contrib.auth.models import User


def send_notification(user, complaint, notification_type, message):
    """Create an in‑app notification for a user."""
    if user:  # safety check
        Notification.objects.create(
            recipient=user,
            complaint=complaint,
            notification_type=notification_type,
            message=message
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