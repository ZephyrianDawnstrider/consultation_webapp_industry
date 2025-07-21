from django.db import models
from custom_admin.models import Skill

class ProspectiveConsultant(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    linkedin = models.URLField(blank=True, null=True, help_text="LinkedIn profile URL")
    skills = models.ManyToManyField(Skill, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.consultant_field}"
