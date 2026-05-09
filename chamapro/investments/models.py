from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class Investment(models.Model):
    TYPES = [
        ('mmf',         'Money Market Fund'),
        ('fd',          'Fixed Deposit'),
        ('real_estate', 'Real Estate / Land'),
        ('stocks',      'NSE Stocks'),
        ('business',    'Chama Business'),
        ('other',       'Other'),
    ]
    STATUS = [
        ('active',   'Active'),
        ('matured',  'Matured'),
        ('sold',     'Sold'),
        ('exited',   'Exited'),
    ]

    chama             = models.ForeignKey('chamapro.Chama', on_delete=models.CASCADE, related_name='investments')
    name              = models.CharField(max_length=200)
    investment_type   = models.CharField(max_length=20, choices=TYPES)
    institution       = models.CharField(max_length=200, blank=True)
    capital_invested  = models.DecimalField(max_digits=14, decimal_places=2)
    date_invested     = models.DateField()
    maturity_date     = models.DateField(null=True, blank=True)
    current_value     = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status            = models.CharField(max_length=20, choices=STATUS, default='active')
    notes             = models.TextField(blank=True)
    created_by        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='investments_created')
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_invested']

    def __str__(self):
        return f"{self.name} ({self.chama.name})"

    @property
    def roi_percent(self):
        if self.capital_invested and self.capital_invested > 0:
            return ((self.current_value - self.capital_invested) / self.capital_invested) * 100
        return Decimal('0')

    @property
    def total_units(self):
        return self.units.aggregate(t=models.Sum('units_held'))['t'] or Decimal('0')

    @property
    def current_nav(self):
        """Net Asset Value per unit."""
        total_units = self.total_units
        if total_units > 0:
            return self.current_value / total_units
        return Decimal('1')

    @property
    def total_returns_received(self):
        return self.returns.aggregate(t=models.Sum('gross_amount'))['t'] or Decimal('0')

    @property
    def type_icon(self):
        icons = {
            'mmf':         'fa-chart-line',
            'fd':          'fa-landmark',
            'real_estate': 'fa-building',
            'stocks':      'fa-chart-bar',
            'business':    'fa-briefcase',
            'other':       'fa-coins',
        }
        return icons.get(self.investment_type, 'fa-coins')

    @property
    def type_color(self):
        colors = {
            'mmf':         '#3b82f6',
            'fd':          '#8b5cf6',
            'real_estate': '#f59e0b',
            'stocks':      '#10b981',
            'business':    '#ef4444',
            'other':       '#6b7280',
        }
        return colors.get(self.investment_type, '#6b7280')


class InvestmentUnit(models.Model):
    """Unit ledger — tracks each member's stake in an investment."""
    investment      = models.ForeignKey(Investment, on_delete=models.CASCADE, related_name='units')
    member          = models.ForeignKey('chamapro.Membership', on_delete=models.CASCADE, related_name='investment_units')
    units_held      = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    nav_at_entry    = models.DecimalField(max_digits=14, decimal_places=6, default=1)
    invested_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    issued_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('investment', 'member')

    def __str__(self):
        return f"{self.member} – {self.units_held} units in {self.investment}"

    @property
    def current_value(self):
        return self.units_held * self.investment.current_nav

    @property
    def unrealised_gain(self):
        return self.current_value - self.invested_amount

    @property
    def ownership_percent(self):
        total = self.investment.total_units
        if total > 0:
            return (self.units_held / total) * 100
        return Decimal('0')


class InvestmentReturn(models.Model):
    RETURN_TYPES = [
        ('dividend',     'Dividend'),
        ('interest',     'Interest'),
        ('rental',       'Rental Income'),
        ('capital_gain', 'Capital Gain'),
        ('maturity',     'Maturity Payout'),
    ]
    FLOW = [
        ('reinvest',   'Reinvest into Portfolio'),
        ('distribute', 'Distribute to Members'),
    ]

    investment    = models.ForeignKey(Investment, on_delete=models.CASCADE, related_name='returns')
    return_type   = models.CharField(max_length=20, choices=RETURN_TYPES)
    gross_amount  = models.DecimalField(max_digits=14, decimal_places=2)
    date_received = models.DateField()
    flow          = models.CharField(max_length=20, choices=FLOW)
    notes         = models.TextField(blank=True)
    processed     = models.BooleanField(default=False)
    processed_at  = models.DateTimeField(null=True, blank=True)
    recorded_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_received']

    def __str__(self):
        return f"{self.get_return_type_display()} – KES {self.gross_amount} ({self.investment.name})"


class ReturnDistribution(models.Model):
    """Per-member payout when a return is distributed."""
    investment_return  = models.ForeignKey(InvestmentReturn, on_delete=models.CASCADE, related_name='distributions')
    member             = models.ForeignKey('chamapro.Membership', on_delete=models.CASCADE, related_name='return_distributions')
    units_at_time      = models.DecimalField(max_digits=18, decimal_places=6)
    share_percent      = models.DecimalField(max_digits=8, decimal_places=4)
    amount             = models.DecimalField(max_digits=14, decimal_places=2)
    credited_to_wallet = models.BooleanField(default=False)
    credited_at        = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.member} – KES {self.amount} from {self.investment_return}"


class NAVHistory(models.Model):
    """Net Asset Value history for charting."""
    investment   = models.ForeignKey(Investment, on_delete=models.CASCADE, related_name='nav_history')
    date         = models.DateField()
    nav_per_unit = models.DecimalField(max_digits=14, decimal_places=6)
    total_value  = models.DecimalField(max_digits=14, decimal_places=2)
    total_units  = models.DecimalField(max_digits=18, decimal_places=6)
    note         = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['date']
        unique_together = ('investment', 'date')

    def __str__(self):
        return f"{self.investment.name} NAV {self.date}: {self.nav_per_unit}"