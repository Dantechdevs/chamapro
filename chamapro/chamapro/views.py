from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import User, Chama, Membership


# ─── Public views ────────────────────────────────────────────────────────────

def home(request):
    return render(request, 'home.html')

def features(request):
    return render(request, 'features.html')

def pricing(request):
    return render(request, 'pricing.html')

def customers(request):
    return render(request, 'customers.html')

def forgot_password(request):
    return render(request, 'forgot_password.html')


# ─── Auth views ───────────────────────────────────────────────────────────────

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
            return redirect(request.GET.get('next', 'dashboard'))
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


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def dashboard(request):
    # Get all chamas the user belongs to
    memberships = request.user.memberships.filter(active=True).select_related('chama')
    chamas = [m.chama for m in memberships]

    # Active chama: from session or first one
    active_chama_id = request.session.get('active_chama_id')
    active_chama = None
    active_membership = None

    if active_chama_id:
        active_chama = next((c for c in chamas if c.id == active_chama_id), None)

    if not active_chama and chamas:
        active_chama = chamas[0]
        request.session['active_chama_id'] = active_chama.id

    if active_chama:
        try:
            active_membership = Membership.objects.get(chama=active_chama, user=request.user)
        except Membership.DoesNotExist:
            pass

    context = {
        'user': request.user,
        'chamas': chamas,
        'active_chama': active_chama,
        'active_membership': active_membership,
    }
    return render(request, 'dashboard.html', context)


@login_required(login_url='login')
def switch_chama(request, chama_id):
    """Switch the active chama in the session."""
    membership = get_object_or_404(Membership, chama_id=chama_id, user=request.user, active=True)
    request.session['active_chama_id'] = chama_id
    return redirect('dashboard')


# ─── Chama views ─────────────────────────────────────────────────────────────

@login_required(login_url='login')
def chama_create(request):
    if request.method == 'POST':
        name                = request.POST.get('name', '').strip()
        description         = request.POST.get('description', '').strip()
        contribution_amount = request.POST.get('contribution_amount', '0').strip()
        contribution_day    = request.POST.get('contribution_day', '5').strip()
        meeting_day         = request.POST.get('meeting_day', '').strip()
        currency            = request.POST.get('currency', 'KES').strip()

        if not name:
            messages.error(request, 'Chama name is required.')
            return render(request, 'chama_create.html')

        chama = Chama.objects.create(
            name=name,
            description=description,
            created_by=request.user,
            contribution_amount=contribution_amount or 0,
            contribution_day=contribution_day or 5,
            meeting_day=meeting_day,
            currency=currency,
        )

        # Creator is automatically the Admin
        Membership.objects.create(
            chama=chama,
            user=request.user,
            role='admin',
        )

        # Set as active chama
        request.session['active_chama_id'] = chama.id
        messages.success(request, f'"{chama.name}" created successfully! You are the Admin.')
        return redirect('chama_members', chama_id=chama.id)

    return render(request, 'chama_create.html')


@login_required(login_url='login')
def chama_members(request, chama_id):
    chama = get_object_or_404(Chama, id=chama_id)

    # Only members of this chama can view it
    membership = get_object_or_404(Membership, chama=chama, user=request.user, active=True)
    memberships = chama.memberships.filter(active=True).select_related('user').order_by('joined_at')

    context = {
        'chama': chama,
        'memberships': memberships,
        'my_membership': membership,
        'can_manage': membership.role in ('admin', 'treasurer'),
    }
    return render(request, 'chama_members.html', context)


@login_required(login_url='login')
def member_invite(request, chama_id):
    chama = get_object_or_404(Chama, id=chama_id)
    my_membership = get_object_or_404(Membership, chama=chama, user=request.user, active=True)

    # Only admins and treasurers can invite
    if my_membership.role not in ('admin', 'treasurer'):
        messages.error(request, 'Only admins and treasurers can invite members.')
        return redirect('chama_members', chama_id=chama_id)

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        role  = request.POST.get('role', 'member').strip()

        if not email:
            messages.error(request, 'Email is required to invite a member.')
            return redirect('chama_members', chama_id=chama_id)

        try:
            invitee = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, f'No ChamaPro account found for {email}. They need to sign up first.')
            return redirect('chama_members', chama_id=chama_id)

        if Membership.objects.filter(chama=chama, user=invitee).exists():
            messages.warning(request, f'{invitee.get_full_name()} is already a member of this chama.')
            return redirect('chama_members', chama_id=chama_id)

        Membership.objects.create(chama=chama, user=invitee, role=role)
        messages.success(request, f'{invitee.get_full_name()} added as {role} to {chama.name}.')
        return redirect('chama_members', chama_id=chama_id)

    return redirect('chama_members', chama_id=chama_id)


@login_required(login_url='login')
def member_role_update(request, chama_id, membership_id):
    chama = get_object_or_404(Chama, id=chama_id)
    my_membership = get_object_or_404(Membership, chama=chama, user=request.user, active=True)

    # Only admins can change roles
    if my_membership.role != 'admin':
        messages.error(request, 'Only admins can change member roles.')
        return redirect('chama_members', chama_id=chama_id)

    target = get_object_or_404(Membership, id=membership_id, chama=chama)

    if request.method == 'POST':
        new_role = request.POST.get('role', 'member')
        target.role = new_role
        target.save()
        messages.success(request, f'{target.user.get_full_name()} is now {new_role}.')

    return redirect('chama_members', chama_id=chama_id)


@login_required(login_url='login')
def member_remove(request, chama_id, membership_id):
    chama = get_object_or_404(Chama, id=chama_id)
    my_membership = get_object_or_404(Membership, chama=chama, user=request.user, active=True)

    if my_membership.role != 'admin':
        messages.error(request, 'Only admins can remove members.')
        return redirect('chama_members', chama_id=chama_id)

    target = get_object_or_404(Membership, id=membership_id, chama=chama)

    # Can't remove yourself if you're the only admin
    if target.user == request.user:
        messages.error(request, "You can't remove yourself from the chama.")
        return redirect('chama_members', chama_id=chama_id)

    target.active = False
    target.save()
    messages.success(request, f'{target.user.get_full_name()} has been removed from {chama.name}.')
    return redirect('chama_members', chama_id=chama_id)