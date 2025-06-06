"""
URL configuration for consultaion_webapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from .views import landing_page
from general.views import login_view
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib import admin
from .views import landing_page

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/login/', login_view, name='login'),
    path('auth/', include(('custom_admin.urls', 'custom_admin'), namespace='custom_admin')),
    path('consultation/', include(('consultation.urls', 'consultation'), namespace='consultation')),
    path('accounts/login/', RedirectView.as_view(url='/auth/login/', permanent=False), name='account_login_redirect'),
    path('', landing_page, name='landing_page'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
