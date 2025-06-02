from django.core.management.base import BaseCommand
from django.test import Client
import os

class Command(BaseCommand):
    help = 'Test add_consultant view by simulating POST request'

    def handle(self, *args, **kwargs):
        client = Client()

        # Prepare test data
        test_pdf_path = os.path.join(os.path.dirname(__file__), 'test_agreement.pdf')
        # Create a dummy PDF file if not exists
        if not os.path.exists(test_pdf_path):
            with open(test_pdf_path, 'wb') as f:
                f.write(b'%PDF-1.4\n%Dummy PDF content\n')

        with open(test_pdf_path, 'rb') as pdf_file:
            response = client.post('/auth/add_consultant/', {
                'name': 'Test Consultant',
                'mobile': '1234567890',
                'email': 'testconsultant@example.com',
                'agreement': pdf_file,
            })

        self.stdout.write(f'Status code: {response.status_code}')
        self.stdout.write(f'Response content: {response.content.decode()}')
