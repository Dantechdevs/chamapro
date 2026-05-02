from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from decimal import Decimal
import datetime
from .models import User, Chama, Membership, Contribution, Penalty, Loan, LoanRepayment


# ─── Auth ────────────────────────────────────────────────────────────────────

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
        if user:
            auth_login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
        messages.error(request, 'Invalid credentials. Please check and try again.')
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
        if not full_name: errors.append('Full name is required.')
        if not email: errors.append('Email is required.')
        if not password or len(password) < 6: errors.append('Password must be at least 6 characters.')
        if User.objects.filter(email=email).exists(): errors.append('Email already registered.')
        if phone and User.objects.filter(phone=phone).exists(): errors.append('Phone already registered.')
        if errors:
            for e in errors: messages.error(request, e)
            return render(request, 'signup.html')
        name_parts = full_name.split(' ', 1)
        base = email.split('@')[0]
        username = base
        i = 1
        while User.objects.filter(username=username).exists():
            username = f'{base}{i}'; i += 1
        user = User.objects.create_user(
            username=username, email=email, password=password,
            first_name=name_parts[0], last_name=name_parts[1] if len(name_parts) > 1 else '',
            phone=phone or None,
        )
        auth_login(request, user)
        return redirect('dashboard')
    return render(request, 'signup.html')


def logout(request):
    auth_logout(request)
    return redirect('login')


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def dashboard(request):
    memberships = request.user.memberships.filter(active=True).select_related('chama')
    chamas = [m.chama for m in memberships]
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
    get_object_or_404(Membership, chama_id=chama_id, user=request.user, active=True)
    request.session['active_chama_id'] = chama_id
    return redirect('dashboard')


# ─── Chama ────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def chama_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Chama name is required.')
            return render(request, 'chama_create.html')
        chama = Chama.objects.create(
            name=name,
            description=request.POST.get('description', ''),
            created_by=request.user,
            contribution_amount=request.POST.get('contribution_amount', 0) or 0,
            contribution_day=request.POST.get('contribution_day', 5) or 5,
            meeting_day=request.POST.get('meeting_day', ''),
            currency=request.POST.get('currency', 'KES'),
        )
        Membership.objects.create(chama=chama, user=request.user, role='admin')
        request.session['active_chama_id'] = chama.id
        messages.success(request, f'"{chama.name}" created! You are the Admin.')
        return redirect('chama_members', chama_id=chama.id)
    return render(request, 'chama_create.html')


@login_required(login_url='login')
def chama_members(request, chama_id):
    chama = get_object_or_404(Chama, id=chama_id)
    membership = get_object_or_404(Membership, chama=chama, user=request.user, active=True)
    memberships = chama.memberships.filter(active=True).select_related('user').order_by('joined_at')
    return render(request, 'chama_members.html', {
        'chama': chama, 'memberships': memberships,
        'my_membership': membership,
        'can_manage': membership.role in ('admin', 'treasurer'),
    })


@login_required(login_url='login')
def member_invite(request, chama_id):
    chama = get_object_or_404(Chama, id=chama_id)
    my = get_object_or_404(Membership, chama=chama, user=request.user, active=True)
    if my.role not in ('admin', 'treasurer'):
        messages.error(request, 'Only admins can invite members.')
        return redirect('chama_members', chama_id=chama_id)
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        role  = request.POST.get('role', 'member')
        try:
            invitee = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, f'No account found for {email}.')
            return redirect('chama_members', chama_id=chama_id)
        if Membership.objects.filter(chama=chama, user=invitee).exists():
            messages.warning(request, f'{invitee.get_full_name()} is already a member.')
            return redirect('chama_members', chama_id=chama_id)
        Membership.objects.create(chama=chama, user=invitee, role=role)
        messages.success(request, f'{invitee.get_full_name()} added as {role}.')
    return redirect('chama_members', chama_id=chama_id)


@login_required(login_url='login')
def member_role_update(request, chama_id, membership_id):
    chama = get_object_or_404(Chama, id=chama_id)
    my = get_object_or_404(Membership, chama=chama, user=request.user, active=True)
    if my.role != 'admin':
        messages.error(request, 'Only admins can change roles.')
        return redirect('chama_members', chama_id=chama_id)
    if request.method == 'POST':
        target = get_object_or_404(Membership, id=membership_id, chama=chama)
        target.role = request.POST.get('role', 'member')
        target.save()
        messages.success(request, f'{target.user.get_full_name()} is now {target.role}.')
    return redirect('chama_members', chama_id=chama_id)


@login_required(login_url='login')
def member_remove(request, chama_id, membership_id):
    chama = get_object_or_404(Chama, id=chama_id)
    my = get_object_or_404(Membership, chama=chama, user=request.user, active=True)
    if my.role != 'admin':
        messages.error(request, 'Only admins can remove members.')
        return redirect('chama_members', chama_id=chama_id)
    target = get_object_or_404(Membership, id=membership_id, chama=chama)
    if target.user == request.user:
        messages.error(request, "You can't remove yourself.")
        return redirect('chama_members', chama_id=chama_id)
    target.active = False
    target.save()
    messages.success(request, f'{target.user.get_full_name()} removed.')
    return redirect('chama_members', chama_id=chama_id)


# ─── Contributions ────────────────────────────────────────────────────────────

@login_required(login_url='login')
def contributions(request, chama_id):
    chama = get_object_or_404(Chama, id=chama_id)
    my = get_object_or_404(Membership, chama=chama, user=request.user, active=True)

    contribs = chama.contributions.select_related('member', 'recorded_by').order_by('-date', '-created_at')

    # Filters
    member_filter = request.GET.get('member', '')
    method_filter = request.GET.get('method', '')
    status_filter = request.GET.get('status', '')

    if member_filter:
        contribs = contribs.filter(member_id=member_filter)
    if method_filter:
        contribs = contribs.filter(payment_method=method_filter)
    if status_filter:
        contribs = contribs.filter(status=status_filter)

    # Summary stats
    today = datetime.date.today()
    total_confirmed  = chama.contributions.filter(status='confirmed').aggregate(t=Sum('amount'))['t'] or 0
    total_pending    = chama.contributions.filter(status='pending').aggregate(t=Sum('amount'))['t'] or 0
    total_this_month = chama.contributions.filter(
        status='confirmed',
        date__month=today.month,
        date__year=today.year,
    ).aggregate(t=Sum('amount'))['t'] or 0

    members = chama.memberships.filter(active=True).select_related('user')

    context = {
        'chama': chama,
        'my_membership': my,
        'can_manage': my.role in ('admin', 'treasurer'),
        'contributions': contribs,
        'members': members,
        'total_confirmed': total_confirmed,
        'total_pending': total_pending,
        'total_this_month': total_this_month,
        'member_filter': member_filter,
        'method_filter': method_filter,
        'status_filter': status_filter,
        'payment_methods': Contribution.PAYMENT_METHODS,
    }
    return render(request, 'contributions.html', context)


@login_required(login_url='login')
def contribution_add(request, chama_id):
    chama = get_object_or_404(Chama, id=chama_id)
    my = get_object_or_404(Membership, chama=chama, user=request.user, active=True)

    if my.role not in ('admin', 'treasurer'):
        messages.error(request, 'Only admins and treasurers can record contributions.')
        return redirect('contributions', chama_id=chama_id)

    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        amount    = request.POST.get('amount', '').strip()
        method    = request.POST.get('payment_method', 'cash')
        reference = request.POST.get('reference', '').strip()
        notes     = request.POST.get('notes', '').strip()
        date      = request.POST.get('date', '').strip()
        status    = request.POST.get('status', 'confirmed')

        errors = []
        if not member_id: errors.append('Please select a member.')
        if not amount:    errors.append('Amount is required.')
        try:
            amount = float(amount)
            if amount <= 0: errors.append('Amount must be greater than 0.')
        except (ValueError, TypeError):
            errors.append('Invalid amount.')

        if errors:
            for e in errors: messages.error(request, e)
            return redirect('contributions', chama_id=chama_id)

        member = get_object_or_404(User, id=member_id)
        Contribution.objects.create(
            chama=chama,
            member=member,
            amount=amount,
            payment_method=method,
            reference=reference or None,
            notes=notes or None,
            status=status,
            date=date or datetime.date.today(),
            recorded_by=request.user,
        )
        messages.success(request, f'Contribution of KES {amount:,.2f} recorded for {member.get_full_name()}.')
        return redirect('contributions', chama_id=chama_id)

    return redirect('contributions', chama_id=chama_id)


@login_required(login_url='login')
def contribution_delete(request, chama_id, contribution_id):
    chama = get_object_or_404(Chama, id=chama_id)
    my = get_object_or_404(Membership, chama=chama, user=request.user, active=True)

    if my.role not in ('admin', 'treasurer'):
        messages.error(request, 'Only admins and treasurers can delete contributions.')
        return redirect('contributions', chama_id=chama_id)

    contrib = get_object_or_404(Contribution, id=contribution_id, chama=chama)
    contrib.delete()
    messages.success(request, 'Contribution deleted.')
    return redirect('contributions', chama_id=chama_id)


@login_required(login_url='login')
def contribution_status_update(request, chama_id, contribution_id):
    """Confirm or reject a pending contribution."""
    chama = get_object_or_404(Chama, id=chama_id)
    my = get_object_or_404(Membership, chama=chama, user=request.user, active=True)

    if my.role not in ('admin', 'treasurer'):
        messages.error(request, 'Permission denied.')
        return redirect('contributions', chama_id=chama_id)

    contrib = get_object_or_404(Contribution, id=contribution_id, chama=chama)
    new_status = request.POST.get('status')
    if new_status in ('confirmed', 'rejected', 'pending'):
        contrib.status = new_status
        contrib.save()
        messages.success(request, f'Contribution marked as {new_status}.')
    return redirect('contributions', chama_id=chama_id)


# ─── Penalties ────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def penalty_add(request, chama_id):
    chama = get_object_or_404(Chama, id=chama_id)
    my = get_object_or_404(Membership, chama=chama, user=request.user, active=True)

    if my.role not in ('admin', 'treasurer'):
        messages.error(request, 'Only admins and treasurers can issue penalties.')
        return redirect('contributions', chama_id=chama_id)

    if request.method == 'POST':
        member_id   = request.POST.get('member_id')
        amount      = request.POST.get('amount', '').strip()
        reason      = request.POST.get('reason', 'late_contribution')
        description = request.POST.get('description', '').strip()

        member = get_object_or_404(User, id=member_id)
        Penalty.objects.create(
            chama=chama, member=member,
            amount=amount, reason=reason,
            description=description or None,
            issued_by=request.user,
        )
        messages.success(request, f'Penalty of KES {amount} issued to {member.get_full_name()}.')

    return redirect('contributions', chama_id=chama_id)


# ─── Loans ────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def loans(request, chama_id):
    chama = get_object_or_404(Chama, id=chama_id)
    my = get_object_or_404(Membership, chama=chama, user=request.user, active=True)

    all_loans = chama.loans.select_related('member', 'approved_by').order_by('-created_at')

    # Filters
    status_filter = request.GET.get('status', '')
    member_filter = request.GET.get('member', '')
    if status_filter:
        all_loans = all_loans.filter(status=status_filter)
    if member_filter:
        all_loans = all_loans.filter(member_id=member_filter)

    # Summary stats
    total_disbursed   = chama.loans.filter(status__in=['active', 'overdue', 'repaid']).aggregate(t=Sum('amount'))['t'] or Decimal('0')
    total_outstanding = chama.loans.filter(status__in=['active', 'overdue']).aggregate(t=Sum('amount'))['t'] or Decimal('0')
    total_pending     = chama.loans.filter(status='pending').count()
    total_overdue     = chama.loans.filter(status='overdue').count()

    members = chama.memberships.filter(active=True).select_related('user')

    context = {
        'chama': chama,
        'my_membership': my,
        'can_manage': my.role in ('admin', 'treasurer'),
        'loans': all_loans,
        'members': members,
        'total_disbursed': total_disbursed,
        'total_outstanding': total_outstanding,
        'total_pending': total_pending,
        'total_overdue': total_overdue,
        'status_filter': status_filter,
        'member_filter': member_filter,
        'loan_statuses': Loan.STATUS_CHOICES,
        'purpose_choices': Loan.PURPOSE_CHOICES,
    }
    return render(request, 'loans.html', context)


@login_required(login_url='login')
def loan_apply(request, chama_id):
    chama = get_object_or_404(Chama, id=chama_id)
    my = get_object_or_404(Membership, chama=chama, user=request.user, active=True)

    if request.method == 'POST':
        member_id    = request.POST.get('member_id') or request.user.id
        amount       = request.POST.get('amount', '').strip()
        interest     = request.POST.get('interest_rate', '10').strip()
        term         = request.POST.get('term_months', '3').strip()
        purpose      = request.POST.get('purpose', 'other')
        description  = request.POST.get('description', '').strip()
        applied_date = request.POST.get('applied_at', '').strip()

        errors = []
        if not amount: errors.append('Loan amount is required.')
        try:
            amount_val = float(amount)
            if amount_val <= 0: errors.append('Amount must be greater than 0.')
        except (ValueError, TypeError):
            errors.append('Invalid amount.')

        if errors:
            for e in errors: messages.error(request, e)
            return redirect('loans', chama_id=chama_id)

        # Admins/treasurers can apply on behalf of any member
        if my.role in ('admin', 'treasurer') and member_id:
            member = get_object_or_404(User, id=member_id)
        else:
            member = request.user

        Loan.objects.create(
            chama=chama,
            member=member,
            amount=Decimal(amount),
            interest_rate=Decimal(interest or '10'),
            term_months=int(term or 3),
            purpose=purpose,
            description=description or None,
            status='pending',
            applied_at=applied_date or datetime.date.today(),
        )
        messages.success(request, f'Loan application of KES {amount_val:,.2f} submitted for {member.get_full_name()}.')
        return redirect('loans', chama_id=chama_id)

    return redirect('loans', chama_id=chama_id)


@login_required(login_url='login')
def loan_approve(request, chama_id, loan_id):
    chama = get_object_or_404(Chama, id=chama_id)
    my = get_object_or_404(Membership, chama=chama, user=request.user, active=True)

    if my.role not in ('admin', 'treasurer'):
        messages.error(request, 'Only admins and treasurers can approve loans.')
        return redirect('loans', chama_id=chama_id)

    loan = get_object_or_404(Loan, id=loan_id, chama=chama)

    if request.method == 'POST':
        action = request.POST.get('action')  # 'approve' or 'reject'
        from dateutil.relativedelta import relativedelta

        if action == 'approve' and loan.status == 'pending':
            loan.status      = 'active'
            loan.approved_by = request.user
            loan.approved_at = datetime.date.today()
            loan.due_date    = datetime.date.today() + relativedelta(months=loan.term_months)
            loan.save()
            messages.success(request, f'Loan of KES {loan.amount:,.2f} approved for {loan.member.get_full_name()}.')

        elif action == 'reject' and loan.status == 'pending':
            loan.status = 'rejected'
            loan.save()
            messages.warning(request, f'Loan application rejected for {loan.member.get_full_name()}.')

    return redirect('loans', chama_id=chama_id)


@login_required(login_url='login')
def loan_repayment_add(request, chama_id, loan_id):
    chama = get_object_or_404(Chama, id=chama_id)
    my = get_object_or_404(Membership, chama=chama, user=request.user, active=True)

    if my.role not in ('admin', 'treasurer'):
        messages.error(request, 'Only admins and treasurers can record repayments.')
        return redirect('loans', chama_id=chama_id)

    loan = get_object_or_404(Loan, id=loan_id, chama=chama)

    if request.method == 'POST':
        amount    = request.POST.get('amount', '').strip()
        method    = request.POST.get('payment_method', 'cash')
        reference = request.POST.get('reference', '').strip()
        date      = request.POST.get('date', '').strip()

        try:
            amount_val = Decimal(amount)
        except Exception:
            messages.error(request, 'Invalid amount.')
            return redirect('loans', chama_id=chama_id)

        LoanRepayment.objects.create(
            loan=loan,
            amount=amount_val,
            payment_method=method,
            reference=reference or None,
            date=date or datetime.date.today(),
            recorded_by=request.user,
            status='confirmed',
        )

        # Check if fully repaid
        if loan.balance() <= 0:
            loan.status = 'repaid'
            loan.save()
            messages.success(request, f'Loan fully repaid by {loan.member.get_full_name()}! 🎉')
        else:
            messages.success(request, f'Repayment of KES {amount_val:,.2f} recorded. Balance: KES {loan.balance():,.2f}')

    return redirect('loans', chama_id=chama_id)


@login_required(login_url='login')
def loan_detail(request, chama_id, loan_id):
    chama = get_object_or_404(Chama, id=chama_id)
    my = get_object_or_404(Membership, chama=chama, user=request.user, active=True)
    loan = get_object_or_404(Loan, id=loan_id, chama=chama)
    repayments = loan.repayments.all()

    context = {
        'chama': chama,
        'my_membership': my,
        'can_manage': my.role in ('admin', 'treasurer'),
        'loan': loan,
        'repayments': repayments,
        'payment_methods': LoanRepayment.PAYMENT_METHODS,
    }
    return render(request, 'loan_detail.html', context)