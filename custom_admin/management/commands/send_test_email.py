from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Send a test email to verify email sending configuration'

    def handle(self, *args, **kwargs):
        subject = 'Test Email from Consultation Webapp'
        message = 'This is a test email to verify SMTP email sending configuration.'
        from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'no-reply@example.com'
        recipient_list = [settings.EMAIL_HOST_USER]

        try:
            send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            self.stdout.write(self.style.SUCCESS(f'Successfully sent test email to {recipient_list[0]}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Failed to send test email: {str(e)}'))
