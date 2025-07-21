from django.shortcuts import render
from custom_admin.models import Skill

def landing_page(request):
    skills = Skill.objects.filter(is_active=True).order_by('name')
    return render(request, 'landingpage.html', {'skills': skills})
