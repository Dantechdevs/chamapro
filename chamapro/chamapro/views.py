from django.shortcuts import render

def home(request):
    return render(request, 'home.html')  # Render the home page template

def features(request):
    return render(request, "features.html")
