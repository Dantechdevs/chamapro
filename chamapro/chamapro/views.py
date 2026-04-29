from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import User


def home(request):
    return render(request, 'home.html')


def features(request):
    return render(request, 'features.html')


def pricing(request):
    return render(request, 'pricing.html')


def customers(request):
    return render(request, 'customers.html')


def login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        identity = request.POST.get('identity', '').strip()
        password = request.POST.get('password', '').strip()

        if not identity or not password:
            messages.error(request, 'Please enter your email/phone and password.')
            return render(request, 'login.html')

        user = None
        if '@' in identity:
            try:
                u = User.objects.get(email=identity)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                pass
        else:
            try:
                u = User.objects.get(phone=identity)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                user = authenticate(request, username=identity, password=password)

        if user is not None:
            auth_login(request, user)
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid credentials. Please check and try again.')
            return render(request, 'login.html')

    return render(request, 'login.html')


def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email     = request.POST.get('email', '').strip()
        phone     = request.POST.get('phone', '').strip()
        password  = request.POST.get('password', '').strip()

        errors = []
        if not full_name:
            errors.append('Full name is required.')
        if not email:
            errors.append('Email is required.')
        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if User.objects.filter(email=email).exists():
            errors.append('An account with this email already exists.')
        if phone and User.objects.filter(phone=phone).exists():
            errors.append('An account with this phone number already exists.')

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'signup.html')

        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name  = name_parts[1] if len(name_parts) > 1 else ''

        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'{base_username}{counter}'
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone if phone else None,
        )

        auth_login(request, user)
        messages.success(request, f'Welcome to ChamaPro, {first_name}!')
        return redirect('dashboard')

    return render(request, 'signup.html')


def logout(request):
    auth_logout(request)
    return redirect('login')


def forgot_password(request):
    return render(request, 'forgot_password.html')


@login_required(login_url='login')
def dashboard(request):
    return render(request, 'dashboard.html', {'user': request.user})