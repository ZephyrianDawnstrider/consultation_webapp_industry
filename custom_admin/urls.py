from django.urls import path, include
from . import views
from rest_framework import routers

app_name = 'custom_admin'

router = routers.DefaultRouter()
router.register(r'skills', views.SkillViewSet, basename='skill')

urlpatterns = [
    path('logout/', views.logout_view, name='logout'),
    path('reset_password/<int:consultant_id>/', views.reset_consultant_password, name='reset_consultant_password'),
    path('register/<int:user_id>/', views.consultant_registration, name='consultant_registration'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin_skills/', views.admin_skills, name='admin_skills'),
    path('admin_invoices/', views.admin_invoices, name='admin_invoices'),
    path('add_consultant/', views.add_consultant, name='add_consultant'),
    path('consultant_list/', views.consultant_list, name='consultant_list'),
    path('consultant_management/', views.consultant_management, name='consultant_management'),
    path('consultant_profile/<int:consultant_id>/', views.consultant_profile, name='consultant_profile'),
    path('edit_consultant/<int:consultant_id>/', views.edit_consultant, name='edit_consultant'),
    path('change_consultant_status/<int:consultant_id>/', views.change_consultant_status, name='change_consultant_status'),
    path('delete_consultant/<int:consultant_id>/', views.delete_consultant, name='delete_consultant'),
    path('update_timesheet_status/<int:timesheetId>/', views.update_timesheet_status, name='update_timesheet_status'),
    path('update_invoice_status/<int:invoice_id>/', views.update_invoice_status, name='update_invoice_status'),
    path('save_timesheet_entries/', views.save_timesheet_entries, name='save_timesheet_entries'),
    path('api/consultant_autofill/', views.consultant_autofill, name='consultant_autofill'),
    path('invoice/edit/<int:invoice_id>/', views.edit_invoice, name='edit_invoice'),
    path('invoice/delete/<int:invoice_id>/', views.delete_invoice, name='delete_invoice'),
    path('new_consultant_details/', views.new_consultant_details, name='new_consultant_details'),
    path('prospective_consultants_management/', views.prospective_consultants_management, name='prospective_consultants_management'),
    path('prospective_consultant_detail/<int:prospective_consultant_id>/', views.prospective_consultant_detail, name='prospective_consultant_detail'),
    path('delete_prospective_consultant/<int:prospective_consultant_id>/', views.delete_prospective_consultant, name='delete_prospective_consultant'),
    path('', include(router.urls)),
    path('admin_profile/<int:admin_id>/', views.admin_profile, name='admin_profile'),
    path('timesheet/', views.timesheet, name='timesheet'),
]
