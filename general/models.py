from django.db import models

class ProspectiveConsultant(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    consultant_field = models.CharField(max_length=255)
    other_consultant_field = models.CharField(max_length=255, blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True, help_text="LinkedIn profile URL")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.consultant_field}"
