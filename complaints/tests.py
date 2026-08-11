from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Complaint, Comment, ComplaintFollower, Notification, Vote


class NotificationSystemTests(TestCase):
    def setUp(self):
        self.citizen = User.objects.create_user(username='citizen', password='secret')
        self.govt = User.objects.create_user(username='govt', password='secret')

        self.citizen.profile.user_type = 'citizen'
        self.citizen.profile.save()
        self.govt.profile.user_type = 'govt'
        self.govt.profile.save()

        self.complaint = Complaint.objects.create(
            citizen=self.citizen,
            category='roads',
            description='Hole in the road near the market.',
            status='reported',
        )

        self.notification = Notification.objects.create(
            user=self.citizen,
            complaint=self.complaint,
            notification_type='status_change',
            title='Status changed',
            message='Your complaint status updated.',
        )

        self.client = Client()

    def test_unread_count_requires_authentication(self):
        response = self.client.get(reverse('get_unread_count'))
        self.assertEqual(response.status_code, 302)

    def test_unread_count_returns_correct_value(self):
        self.client.login(username='citizen', password='secret')
        response = self.client.get(reverse('get_unread_count'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'unread_count': 1})

    def test_get_notifications_returns_owned_notifications(self):
        self.client.login(username='citizen', password='secret')
        response = self.client.get(reverse('get_notifications'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('notifications', data)
        self.assertEqual(len(data['notifications']), 1)
        self.assertEqual(data['notifications'][0]['title'], 'Status changed')

    def test_mark_notification_read_updates_notification(self):
        self.client.login(username='citizen', password='secret')
        response = self.client.post(reverse('mark_notification_read', args=[self.notification.id]))
        self.assertEqual(response.status_code, 200)
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_mark_all_read_updates_all_notifications(self):
        self.client.login(username='citizen', password='secret')
        second_notification = Notification.objects.create(
            user=self.citizen,
            complaint=self.complaint,
            notification_type='status_change',
            title='Another update',
            message='Another update was applied.',
        )
        response = self.client.post(reverse('mark_all_read'))
        self.assertEqual(response.status_code, 200)
        self.notification.refresh_from_db()
        second_notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
        self.assertTrue(second_notification.is_read)

    def test_notify_new_complaint_govt_creates_notification(self):
        from .models import notify_new_complaint_govt

        Notification.objects.filter(user=self.govt).delete()
        notify_new_complaint_govt(self.complaint)
        self.assertTrue(
            Notification.objects.filter(user=self.govt, notification_type='new_complaint').exists()
        )

    def test_citizen_can_toggle_vote(self):
        self.client.login(username='citizen', password='secret')
        response = self.client.post(reverse('toggle_vote', args=[self.complaint.id]))
        self.assertEqual(response.status_code, 200)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.upvotes, 1)
        self.assertTrue(Vote.objects.filter(user=self.citizen, complaint=self.complaint).exists())

        response = self.client.post(reverse('toggle_vote', args=[self.complaint.id]))
        self.assertEqual(response.status_code, 200)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.upvotes, 0)
        self.assertFalse(Vote.objects.filter(user=self.citizen, complaint=self.complaint).exists())

    def test_govt_cannot_vote(self):
        self.client.login(username='govt', password='secret')
        response = self.client.post(reverse('toggle_vote', args=[self.complaint.id]))
        self.assertEqual(response.status_code, 403)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.upvotes, 0)
        self.assertFalse(Vote.objects.filter(user=self.govt, complaint=self.complaint).exists())

    def test_api_follow_notifies_owner(self):
        other_user = User.objects.create_user(username='follower', password='secret')
        self.client.login(username='follower', password='secret')

        response = self.client.post(reverse('api_follow'), {'complaint_id': self.complaint.id})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Notification.objects.filter(user=self.citizen, notification_type='follow', complaint=self.complaint).exists())

    def test_api_comment_notifies_owner_and_followers(self):
        follower = User.objects.create_user(username='follower', password='secret')
        ComplaintFollower.objects.create(complaint=self.complaint, user=follower)
        self.client.login(username='follower', password='secret')

        response = self.client.post(reverse('api_comment'), {'complaint_id': self.complaint.id, 'text': 'Looks good'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Notification.objects.filter(user=self.citizen, notification_type='comment_added', complaint=self.complaint).exists())
        self.assertTrue(Notification.objects.filter(user=follower, notification_type='comment_added', complaint=self.complaint).exists())
