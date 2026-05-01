from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.db.models import Sum


class User(AbstractUser):
    phone = models.CharField(max_length=30, unique=True, null=True, blank=True)

    def __str__(self):
        return self.get_full_name() or self.username


class Chama(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        'User', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_chamas'
    )
    currency = models.CharField(max_length=10, default='KES')
    contribution_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    contribution_day = models.PositiveSmallIntegerField(default=5)
    meeting_day = models.CharField(max_length=20, blank=True, null=True)
    settings = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def member_count(self):
        return self.memberships.filter(active=True).count()

    def total_contributions(self):
        result = self.contributions.filter(
            status='confirmed'
        ).aggregate(total=Sum('amount'))
        return result['total'] or 0

    def total_penalties(self):
        result = self.penalties.aggregate(total=Sum('amount'))
        return result['total'] or 0


class Membership(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('treasurer', 'Treasurer'),
        ('secretary', 'Secretary'),
        ('member', 'Member'),
    ]
    chama = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('chama', 'user')

    def __str__(self):
        return f"{self.user} @ {self.chama} ({self.role})"

    def is_admin(self):
        return self.role == 'admin'

    def is_treasurer(self):
        return self.role in ('admin', 'treasurer')

    def total_contributed(self):
        result = self.chama.contributions.filter(
            member=self.user, status='confirmed'
        ).aggregate(total=Sum('amount'))
        return result['total'] or 0

    def total_arrears(self):
        """How much this member owes based on expected vs paid."""
        paid = self.total_contributed()
        expected = self.chama.contribution_amount
        shortfall = expected - paid
        return max(shortfall, 0)


class Contribution(models.Model):
    PAYMENT_METHODS = [
        ('mpesa', 'M-Pesa'),
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
    ]

    chama = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name='contributions')
    member = models.ForeignKey('User', on_delete=models.CASCADE, related_name='contributions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    reference = models.CharField(max_length=255, blank=True, null=True, help_text="M-Pesa code or bank ref")
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    date = models.DateField(default=timezone.now)
    recorded_by = models.ForeignKey(
        'User', null=True, blank=True, on_delete=models.SET_NULL, related_name='recorded_contributions'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.member} → {self.chama} KES {self.amount} ({self.status})"


class Penalty(models.Model):
    PENALTY_REASONS = [
        ('late_contribution', 'Late Contribution'),
        ('missed_contribution', 'Missed Contribution'),
        ('meeting_absence', 'Meeting Absence'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('waived', 'Waived'),
    ]

    chama = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name='penalties')
    member = models.ForeignKey('User', on_delete=models.CASCADE, related_name='penalties')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=50, choices=PENALTY_REASONS, default='late_contribution')
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unpaid')
    issued_by = models.ForeignKey(
        'User', null=True, blank=True, on_delete=models.SET_NULL, related_name='issued_penalties'
    )
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issued_at']

    def __str__(self):
        return f"Penalty {self.member} {self.amount} ({self.status})"


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('contribution', 'Contribution'),
        ('expense', 'Expense'),
        ('loan_repayment', 'Loan Repayment'),
        ('withdrawal', 'Withdrawal'),
    ]
    chama = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name='transactions')
    member = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='transactions')
    type = models.CharField(max_length=50, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    meta = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey('User', null=True, blank=True, related_name='created_transactions', on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} {self.amount} ({self.chama})"