from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from consultant.models import Timesheet, ConsultantProfile
from custom_admin.models import Invoice
from unittest.mock import patch
import json
from io import BytesIO

User = get_user_model()

class ConsultantViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.consultant = User.objects.create_user(
            email='consultant@example.com',
            password='testpassword',
            role='consultant'
        )
        self.client.login(email='consultant@example.com', password='testpassword')

    def test_consultant_dashboard_access(self):
        url = reverse('consultant:consultant_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Consultant Dashboard')

    def test_consultant_timesheet_view(self):
        url = reverse('consultant:consultant_timesheet')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Consultant Timesheet')

    @patch('consultant.views.default_storage.save')
    @patch('consultant.views.pd.read_excel')
    def test_upload_timesheet_post(self, mock_read_excel, mock_save):
        mock_read_excel.return_value = patch('pandas.DataFrame').start()
        mock_save.return_value = 'timesheets/test.csv'
        with open('test_timesheet.xlsx', 'wb') as f:
            f.write(b'Test content')
        with open('test_timesheet.xlsx', 'rb') as f:
            response = self.client.post(
                reverse('consultant:upload_timesheet', args=[self.consultant.id]),
                {'timesheet_file': f, 'year': '2023', 'month': '01'}
            )
        self.assertEqual(response.status_code, 200)
        patch.stopall()

    def test_consultant_profile_get(self):
        url = reverse('consultant:consultant_profile', args=[self.consultant.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Consultant Profile')

    def test_consultant_invoice_get(self):
        url = reverse('consultant:consultant_invoice')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Consultant Invoice')

    @patch('consultant.views.send_mail')
    def test_send_otp_post(self, mock_send_mail):
        url = reverse('consultant:send_otp')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'success': True, 'message': 'OTP sent successfully'})

    @patch('consultant.views.send_mail')
    def test_change_password_post(self, mock_send_mail):
        url = reverse('consultant:change_password')
        data = json.dumps({'new_password': 'newpassword123'})
        response = self.client.post(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'success': True, 'message': 'Password changed successfully'})

    def test_save_timesheet_entries_missing_entries(self):
        url = reverse('consultant:save_timesheet_entries')
        response = self.client.post(url, json.dumps({'timesheet_id': 1}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'success': False, 'message': 'Missing entries.'})

    def test_save_timesheet_entries_invalid_timesheet(self):
        url = reverse('consultant:save_timesheet_entries')
        response = self.client.post(url, json.dumps({'timesheet_id': 9999, 'entries': []}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'success': False, 'message': 'Timesheet not found or access denied.'})

    def test_delete_timesheet_not_found(self):
        url = reverse('consultant:delete_timesheet', args=[9999])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)
        self.assertJSONEqual(response.content, {'success': False, 'message': 'Timesheet not found.'})

    def test_delete_timesheet_permission_denied(self):
        # Create a timesheet for another user
        other_user = User.objects.create_user(email='other@example.com', password='password', role='consultant')
        timesheet = Timesheet.objects.create(consultant=other_user, month='2023-01-01', status='awaiting_review')
        url = reverse('consultant:delete_timesheet', args=[timesheet.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
