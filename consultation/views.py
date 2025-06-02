from django.shortcuts import render

def consultant_dashboard(request):
    return render(request, 'consultant_dashboard.html')
