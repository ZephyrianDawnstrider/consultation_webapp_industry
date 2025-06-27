from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from custom_admin.models import Skill, Invoice
from unittest.mock import patch
import json

User = get_user_model()

class AdminViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='adminpassword',
            is_staff=True,
            role='admin'
        )
        self.client.login(email='admin@example.com', password='adminpassword')

    def test_admin_dashboard_access(self):
        url = reverse('custom_admin:admin_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')

    def test_consultant_management_access(self):
        url = reverse('custom_admin:consultant_management')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Consultant Management')

    @patch('custom_admin.views.send_mail')
    def test_add_consultant_post(self, mock_send_mail):
        url = reverse('custom_admin:add_consultant')
        data = {
            'name': 'Test Consultant',
            'mobile': '1234567890',
            'email': 'testconsultant@example.com',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'success': True, 'message': 'Consultant added successfully and email sent.'})

    def test_admin_skills_view(self):
        url = reverse('custom_admin:admin_skills')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Skill Master')

    def test_admin_invoices_view(self):
        url = reverse('custom_admin:admin_invoices')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invoice Management')

    @patch('custom_admin.views.Invoice.objects.get')
    def test_update_invoice_status_post(self, mock_get):
        mock_invoice = mock_get.return_value
        mock_invoice.status = 'pending'
        mock_invoice.save.return_value = None

        url = reverse('custom_admin:update_invoice_status', args=[1])
        response = self.client.post(url, {'status': 'approved'})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'success': True, 'message': 'Invoice status updated successfully.'})

    def test_logout_view(self):
        url = reverse('custom_admin:logout')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
