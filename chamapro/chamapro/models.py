from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


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
    contribution_day = models.PositiveSmallIntegerField(default=5, help_text="Day of month contributions are due")
    meeting_day = models.CharField(max_length=20, blank=True, null=True)
    settings = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def member_count(self):
        return self.memberships.filter(active=True).count()

    def total_contributions(self):
        from django.db.models import Sum
        result = self.transactions.filter(type='contribution').aggregate(Sum('amount'))
        return result['amount__sum'] or 0


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