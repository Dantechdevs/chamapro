from django.shortcuts import render

def home(request):
    return render(request, 'home.html')  # Render the home page template

def features(request):
    return render(request, "features.html")

def pricing(request):
    return render(request, "pricing.html")

def customers(request):
    return render(request, "customers.html")    

def login(request):
    return render(request, 'login.html')

def signup(request):
    return render(request, 'signup.html')  # Render the signup page template    