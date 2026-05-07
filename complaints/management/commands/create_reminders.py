from django.core.management.base import BaseCommand
from complaints.models import create_govt_reminders

class Command(BaseCommand):
    help = 'Create reminder notifications for government users about pending complaints'

    def handle(self, *args, **options):
        create_govt_reminders()
        self.stdout.write(self.style.SUCCESS('Successfully created government reminders'))