"""
investments/services.py
Core business logic for the ChamaPro investment module.
"""
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from .models import Investment, InvestmentUnit, InvestmentReturn, ReturnDistribution, NAVHistory


# ── Unit issuance ──────────────────────────────────────────────────────────────

def issue_units(investment: Investment, membership, amount: Decimal) -> InvestmentUnit:
    """
    Issue units to a member for a given investment amount.
    Uses the current NAV as the price per unit.
    Creates or updates the member's unit record.
    """
    nav = investment.current_nav
    if nav <= 0:
        nav = Decimal('1')

    units_to_issue = amount / nav

    unit_record, created = InvestmentUnit.objects.get_or_create(
        investment=investment,
        member=membership,
        defaults={
            'units_held': units_to_issue,
            'nav_at_entry': nav,
            'invested_amount': amount,
        }
    )

    if not created:
        unit_record.units_held      += units_to_issue
        unit_record.invested_amount += amount
        unit_record.save()

    return unit_record


# ── Return processing ──────────────────────────────────────────────────────────

@transaction.atomic
def process_return(investment_return: InvestmentReturn) -> list[ReturnDistribution]:
    """
    Process an investment return:
    - 'distribute': split gross_amount across unit holders proportionally,
      create ReturnDistribution records, and credit each member's wallet.
    - 'reinvest': increase investment's current_value and update NAV.
    Returns list of ReturnDistribution objects (empty for reinvest).
    """
    if investment_return.processed:
        raise ValueError("This return has already been processed.")

    investment = investment_return.investment
    distributions = []

    if investment_return.flow == 'distribute':
        unit_records = InvestmentUnit.objects.filter(investment=investment).select_related('member')
        total_units  = sum(u.units_held for u in unit_records)

        if total_units <= 0:
            raise ValueError("No unit holders found for this investment.")

        for unit_record in unit_records:
            share   = unit_record.units_held / total_units
            payout  = investment_return.gross_amount * share

            dist = ReturnDistribution.objects.create(
                investment_return=investment_return,
                member=unit_record.member,
                units_at_time=unit_record.units_held,
                share_percent=share * 100,
                amount=payout,
            )
            distributions.append(dist)

            # Credit wallet — wire to your existing wallet logic
            _credit_wallet(unit_record.member, payout, investment_return)

    elif investment_return.flow == 'reinvest':
        investment.current_value += investment_return.gross_amount
        investment.save(update_fields=['current_value'])

        # Record new NAV snapshot
        total_units = investment.total_units
        NAVHistory.objects.update_or_create(
            investment=investment,
            date=investment_return.date_received,
            defaults={
                'nav_per_unit': investment.current_nav,
                'total_value':  investment.current_value,
                'total_units':  total_units,
                'note': f'Reinvested: {investment_return.get_return_type_display()}',
            }
        )

    investment_return.processed    = True
    investment_return.processed_at = timezone.now()
    investment_return.save()

    return distributions


def _credit_wallet(membership, amount: Decimal, investment_return: InvestmentReturn):
    """
    Hook into your existing wallet / ledger system.
    Replace this stub with your actual wallet credit logic.
    """
    # Example:
    # from wallets.services import credit_member_wallet
    # credit_member_wallet(
    #     membership=membership,
    #     amount=amount,
    #     description=f"Return from {investment_return.investment.name}",
    #     reference=f"INV-RET-{investment_return.pk}",
    # )
    pass


# ── NAV update ────────────────────────────────────────────────────────────────

@transaction.atomic
def update_nav(investment: Investment, new_total_value: Decimal, date, note: str = '') -> NAVHistory:
    """
    Update an investment's current value and record a NAV snapshot.
    """
    investment.current_value = new_total_value
    investment.save(update_fields=['current_value'])

    total_units = investment.total_units

    nav_snapshot, _ = NAVHistory.objects.update_or_create(
        investment=investment,
        date=date,
        defaults={
            'nav_per_unit': investment.current_nav,
            'total_value':  new_total_value,
            'total_units':  total_units,
            'note': note,
        }
    )
    return nav_snapshot


# ── Portfolio summary ──────────────────────────────────────────────────────────

def portfolio_summary(chama) -> dict:
    """
    Aggregate portfolio stats for the chama dashboard.
    """
    investments = Investment.objects.filter(chama=chama)

    total_invested = sum(i.capital_invested for i in investments)
    total_value    = sum(i.current_value    for i in investments)
    total_returns  = sum(i.total_returns_received for i in investments)
    roi            = ((total_value - total_invested) / total_invested * 100) if total_invested else Decimal('0')

    by_type = {}
    for inv in investments:
        t = inv.get_investment_type_display()
        if t not in by_type:
            by_type[t] = {'invested': Decimal('0'), 'value': Decimal('0'), 'count': 0, 'color': inv.type_color}
        by_type[t]['invested'] += inv.capital_invested
        by_type[t]['value']    += inv.current_value
        by_type[t]['count']    += 1

    return {
        'total_invested': total_invested,
        'total_value':    total_value,
        'total_returns':  total_returns,
        'roi_percent':    roi,
        'count':          investments.count(),
        'active_count':   investments.filter(status='active').count(),
        'by_type':        by_type,
        'investments':    investments,
    }


def member_portfolio(membership) -> dict:
    """
    All unit positions for a single member.
    """
    units = InvestmentUnit.objects.filter(member=membership).select_related('investment')
    total_invested    = sum(u.invested_amount for u in units)
    total_value       = sum(u.current_value   for u in units)
    total_distributions = ReturnDistribution.objects.filter(
        member=membership
    ).aggregate(t=__import__('django.db.models', fromlist=['Sum']).Sum('amount'))['t'] or Decimal('0')

    return {
        'units': units,
        'total_invested': total_invested,
        'total_value': total_value,
        'total_distributions': total_distributions,
        'unrealised_gain': total_value - total_invested,
    }
