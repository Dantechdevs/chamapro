from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    phone = models.CharField(max_length=30, unique=True, null=True, blank=True)

    def __str__(self):
        return self.get_full_name() or self.username

class Chama(models.Model):
    name = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        'User', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_chamas'
    )
    currency = models.CharField(max_length=10, default='KES')
    settings = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Membership(models.Model):
    ROLE_CHOICES = [
        ('admin','Admin'),
        ('treasurer','Treasurer'),
        ('member','Member'),
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

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('contribution','Contribution'),
        ('expense','Expense'),
        ('loan_repayment','Loan Repayment'),
        ('withdrawal','Withdrawal'),
    ]
    chama = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name='transactions')
    member = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL)
    type = models.CharField(max_length=50, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=255, null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey('User', null=True, blank=True, related_name='created_transactions', on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} {self.amount} ({self.chama})"
