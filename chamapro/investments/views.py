from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal

from chamapro.models import Chama, Membership  # ← fixed, imported at top level
from .models import Investment, InvestmentUnit, InvestmentReturn, ReturnDistribution, NAVHistory
from .forms import InvestmentForm, InvestmentReturnForm, NAVUpdateForm, IssueUnitsForm
from .services import portfolio_summary, process_return, update_nav, issue_units, member_portfolio


def get_chama_and_membership(request, chama_id):
    chama = get_object_or_404(Chama, pk=chama_id)
    membership = get_object_or_404(Membership, chama=chama, user=request.user)
    return chama, membership


# ── Portfolio (index) ──────────────────────────────────────────────────────────

@login_required
def portfolio(request, chama_id):
    chama, my_membership = get_chama_and_membership(request, chama_id)
    summary = portfolio_summary(chama)

    nav_chart = {}
    for inv in summary['investments'].filter(status='active'):
        history = inv.nav_history.order_by('date').values('date', 'nav_per_unit')
        nav_chart[inv.id] = [
            {'date': str(h['date']), 'nav': float(h['nav_per_unit'])}
            for h in history
        ]

    context = {
        'chama': chama,
        'my_membership': my_membership,
        'summary': summary,
        'nav_chart': nav_chart,
        'page': 'investments',
    }
    return render(request, 'investments/portfolio.html', context)


# ── Investment detail ──────────────────────────────────────────────────────────

@login_required
def investment_detail(request, chama_id, pk):
    chama, my_membership = get_chama_and_membership(request, chama_id)
    investment = get_object_or_404(Investment, pk=pk, chama=chama)

    units         = InvestmentUnit.objects.filter(investment=investment).select_related('member__user')
    returns       = InvestmentReturn.objects.filter(investment=investment)
    nav_history   = investment.nav_history.order_by('date')
    distributions = ReturnDistribution.objects.filter(
        investment_return__investment=investment
    ).select_related('member__user', 'investment_return').order_by('-investment_return__date_received')

    return_form = InvestmentReturnForm()
    nav_form    = NAVUpdateForm(initial={'date': timezone.now().date(), 'total_value': investment.current_value})
    issue_form  = IssueUnitsForm()

    nav_chart_data = [
        {'date': str(h.date), 'nav': float(h.nav_per_unit), 'value': float(h.total_value)}
        for h in nav_history
    ]

    context = {
        'chama': chama,
        'my_membership': my_membership,
        'investment': investment,
        'units': units,
        'returns': returns,
        'distributions': distributions,
        'return_form': return_form,
        'nav_form': nav_form,
        'issue_form': issue_form,
        'nav_chart_data': nav_chart_data,
        'page': 'investments',
    }
    return render(request, 'investments/detail.html', context)


# ── Add investment ─────────────────────────────────────────────────────────────

@login_required
def investment_add(request, chama_id):
    chama, my_membership = get_chama_and_membership(request, chama_id)

    if request.method == 'POST':
        form = InvestmentForm(request.POST)
        if form.is_valid():
            inv = form.save(commit=False)
            inv.chama      = chama
            inv.created_by = request.user
            inv.save()

            NAVHistory.objects.create(
                investment=inv,
                date=inv.date_invested,
                nav_per_unit=Decimal('1'),
                total_value=inv.capital_invested,
                total_units=inv.capital_invested,
                note='Initial investment',
            )
            messages.success(request, f'Investment "{inv.name}" added successfully.')
            return redirect('investments:investment_detail', chama_id=chama_id, pk=inv.pk)  # ← fixed
    else:
        form = InvestmentForm()

    context = {
        'chama': chama,
        'my_membership': my_membership,
        'form': form,
        'page': 'investments',
    }
    return render(request, 'investments/add.html', context)


# ── Edit investment ────────────────────────────────────────────────────────────

@login_required
def investment_edit(request, chama_id, pk):
    chama, my_membership = get_chama_and_membership(request, chama_id)
    investment = get_object_or_404(Investment, pk=pk, chama=chama)

    if request.method == 'POST':
        form = InvestmentForm(request.POST, instance=investment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Investment updated.')
            return redirect('investments:investment_detail', chama_id=chama_id, pk=pk)  # ← fixed
    else:
        form = InvestmentForm(instance=investment)

    context = {
        'chama': chama,
        'my_membership': my_membership,
        'form': form,
        'investment': investment,
        'page': 'investments',
    }
    return render(request, 'investments/add.html', context)


# ── Log return ────────────────────────────────────────────────────────────────

@login_required
def log_return(request, chama_id, pk):
    chama, my_membership = get_chama_and_membership(request, chama_id)
    investment = get_object_or_404(Investment, pk=pk, chama=chama)

    if request.method == 'POST':
        form = InvestmentReturnForm(request.POST)
        if form.is_valid():
            ret = form.save(commit=False)
            ret.investment  = investment
            ret.recorded_by = request.user
            ret.save()

            try:
                process_return(ret)
                messages.success(request, f'Return of KES {ret.gross_amount:,.2f} logged and processed.')
            except Exception as e:
                messages.error(request, f'Return saved but processing failed: {e}')

    return redirect('investments:investment_detail', chama_id=chama_id, pk=pk)  # ← fixed


# ── Update NAV ────────────────────────────────────────────────────────────────

@login_required
def update_nav_view(request, chama_id, pk):
    chama, my_membership = get_chama_and_membership(request, chama_id)
    investment = get_object_or_404(Investment, pk=pk, chama=chama)

    if request.method == 'POST':
        form = NAVUpdateForm(request.POST)
        if form.is_valid():
            update_nav(
                investment=investment,
                new_total_value=form.cleaned_data['total_value'],
                date=form.cleaned_data['date'],
                note=form.cleaned_data.get('note', ''),
            )
            messages.success(request, 'NAV updated successfully.')

    return redirect('investments:investment_detail', chama_id=chama_id, pk=pk)  # ← fixed


# ── Issue units to member ──────────────────────────────────────────────────────

@login_required
def issue_units_view(request, chama_id, pk):
    chama, my_membership = get_chama_and_membership(request, chama_id)
    investment = get_object_or_404(Investment, pk=pk, chama=chama)

    if request.method == 'POST':
        form = IssueUnitsForm(request.POST)
        if form.is_valid():
            member = get_object_or_404(Membership, pk=form.cleaned_data['member_id'], chama=chama)  # ← fixed
            unit_record = issue_units(investment, member, form.cleaned_data['amount'])
            messages.success(
                request,
                f'{unit_record.units_held:.4f} units issued to {member.user.get_full_name()}.'
            )

    return redirect('investments:investment_detail', chama_id=chama_id, pk=pk)  # ← fixed


# ── Member stakes view ────────────────────────────────────────────────────────

@login_required
def member_stakes(request, chama_id):
    chama, my_membership = get_chama_and_membership(request, chama_id)
    memberships = Membership.objects.filter(chama=chama).select_related('user')  # ← fixed

    stakes = []
    for m in memberships:
        data = member_portfolio(m)
        if data['units'].exists():
            stakes.append({'membership': m, **data})

    context = {
        'chama': chama,
        'my_membership': my_membership,
        'stakes': stakes,
        'page': 'investments',
    }
    return render(request, 'investments/stakes.html', context)