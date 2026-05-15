from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal


class User(AbstractUser):
    phone = models.CharField(max_length=30, unique=True, null=True, blank=True)

    # Profile fields
    national_id   = models.CharField(max_length=20, blank=True, null=True)
    kra_pin       = models.CharField(max_length=20, blank=True, null=True)
    bio           = models.TextField(blank=True, null=True)
    occupation    = models.CharField(max_length=100, blank=True, null=True)
    location      = models.CharField(max_length=100, blank=True, null=True)
    avatar        = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bank_name     = models.CharField(max_length=100, blank=True, null=True)
    bank_account  = models.CharField(max_length=30, blank=True, null=True)
    mpesa_number  = models.CharField(max_length=20, blank=True, null=True)

    KYC_CHOICES = [
        ('unverified', 'Unverified'),
        ('pending',    'Pending Review'),
        ('verified',   'Verified'),
    ]
    kyc_status = models.CharField(max_length=20, choices=KYC_CHOICES, default='unverified')

    def __str__(self):
        return self.get_full_name() or self.username

    def credit_score(self):
        score = 0
        all_contribs = self.contributions.count()
        confirmed    = self.contributions.filter(status='confirmed').count()
        if all_contribs > 0:
            score += int((confirmed / all_contribs) * 300)

        total_loans  = self.loans.exclude(status__in=['pending', 'rejected']).count()
        repaid_loans = self.loans.filter(status='repaid').count()
        if total_loans > 0:
            score += int((repaid_loans / total_loans) * 250)
        else:
            score += 150

        unpaid_fines = self.penalties.filter(status='unpaid').count()
        score += max(0, 200 - (unpaid_fines * 40))

        earliest = self.memberships.filter(active=True).order_by('joined_at').first()
        if earliest:
            months = (timezone.now() - earliest.joined_at).days // 30
            score += min(months * 5, 100)

        return min(score, 850)

    def credit_score_label(self):
        s = self.credit_score()
        if s >= 750: return 'Excellent'
        if s >= 650: return 'Very Good'
        if s >= 550: return 'Good'
        if s >= 400: return 'Fair'
        return 'Poor'

    def credit_score_color(self):
        s = self.credit_score()
        if s >= 750: return 'green'
        if s >= 550: return 'blue'
        if s >= 400: return 'amber'
        return 'red'

    def payment_rate(self):
        total = self.contributions.count()
        if total == 0:
            return 100
        confirmed = self.contributions.filter(status='confirmed').count()
        return int((confirmed / total) * 100)

    def total_contributed_all(self):
        result = self.contributions.filter(status='confirmed').aggregate(t=Sum('amount'))
        return result['t'] or Decimal('0')

    def active_loan_balance(self):
        result = self.loans.filter(status__in=['active', 'overdue']).aggregate(t=Sum('amount'))
        return result['t'] or Decimal('0')

    def outstanding_fines(self):
        result = self.penalties.filter(status='unpaid').aggregate(t=Sum('amount'))
        return result['t'] or Decimal('0')


class Chama(models.Model):
    name                = models.CharField(max_length=255)
    description         = models.TextField(blank=True, null=True)
    created_by          = models.ForeignKey(
        'User', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_chamas'
    )
    currency            = models.CharField(max_length=10, default='KES')
    contribution_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    contribution_day    = models.PositiveSmallIntegerField(default=5)
    meeting_day         = models.CharField(max_length=20, blank=True, null=True)
    max_members         = models.PositiveSmallIntegerField(default=10)
    late_penalty        = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    loan_interest       = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    settings            = models.JSONField(default=dict, blank=True)
    is_active           = models.BooleanField(default=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def member_count(self):
        return self.memberships.filter(active=True).count()

    def total_contributions(self):
        result = self.contributions.filter(status='confirmed').aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0')

    def total_loans_outstanding(self):
        result = self.loans.filter(status__in=['active', 'overdue']).aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0')

    @property
    def invite_code(self):
        import hashlib
        return hashlib.md5(f'chama-{self.id}-invite'.encode()).hexdigest()[:10].upper()


class Membership(models.Model):
    ROLE_CHOICES = [
        ('admin',     'Admin'),
        ('treasurer', 'Treasurer'),
        ('secretary', 'Secretary'),
        ('member',    'Member'),
    ]
    chama     = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name='memberships')
    user      = models.ForeignKey('User', on_delete=models.CASCADE, related_name='memberships')
    role      = models.CharField(max_length=30, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(default=timezone.now)
    active    = models.BooleanField(default=True)

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
        return result['total'] or Decimal('0')


class Contribution(models.Model):
    PAYMENT_METHODS = [
        ('mpesa',  'M-Pesa'),
        ('bank',   'Bank Transfer'),
        ('cash',   'Cash'),
        ('cheque', 'Cheque'),
    ]
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('confirmed', 'Confirmed'),
        ('rejected',  'Rejected'),
    ]
    chama          = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name='contributions')
    member         = models.ForeignKey('User', on_delete=models.CASCADE, related_name='contributions')
    amount         = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    reference      = models.CharField(max_length=255, blank=True, null=True)
    notes          = models.TextField(blank=True, null=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    date           = models.DateField(default=timezone.now)
    recorded_by    = models.ForeignKey(
        'User', null=True, blank=True, on_delete=models.SET_NULL, related_name='recorded_contributions'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.member} → {self.chama} {self.amount} ({self.status})"


class Penalty(models.Model):
    PENALTY_REASONS = [
        ('late_contribution',   'Late Contribution'),
        ('missed_contribution', 'Missed Contribution'),
        ('meeting_absence',     'Meeting Absence'),
        ('other',               'Other'),
    ]
    STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('paid',   'Paid'),
        ('waived', 'Waived'),
    ]
    chama       = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name='penalties')
    member      = models.ForeignKey('User', on_delete=models.CASCADE, related_name='penalties')
    amount      = models.DecimalField(max_digits=12, decimal_places=2)
    reason      = models.CharField(max_length=50, choices=PENALTY_REASONS, default='late_contribution')
    description = models.TextField(blank=True, null=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unpaid')
    issued_by   = models.ForeignKey(
        'User', null=True, blank=True, on_delete=models.SET_NULL, related_name='issued_penalties'
    )
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issued_at']

    def __str__(self):
        return f"Penalty {self.member} {self.amount} ({self.status})"


class Loan(models.Model):
    STATUS_CHOICES = [
        ('pending',  'Pending Approval'),
        ('approved', 'Approved'),
        ('active',   'Active'),
        ('overdue',  'Overdue'),
        ('repaid',   'Fully Repaid'),
        ('rejected', 'Rejected'),
    ]
    PURPOSE_CHOICES = [
        ('business',  'Business Investment'),
        ('education', 'Education'),
        ('medical',   'Medical Expenses'),
        ('home',      'Home Improvement'),
        ('emergency', 'Emergency'),
        ('other',     'Other'),
    ]
    chama         = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name='loans')
    member        = models.ForeignKey('User', on_delete=models.CASCADE, related_name='loans')
    amount        = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    term_months   = models.PositiveSmallIntegerField(default=3)
    purpose       = models.CharField(max_length=50, choices=PURPOSE_CHOICES, default='other')
    description   = models.TextField(blank=True, null=True)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at    = models.DateField(default=timezone.now)
    approved_at   = models.DateField(null=True, blank=True)
    due_date      = models.DateField(null=True, blank=True)
    approved_by   = models.ForeignKey(
        'User', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_loans'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Loan {self.member} {self.amount} ({self.status})"

    def interest_amount(self):
        return (self.amount * self.interest_rate / 100).quantize(Decimal('0.01'))

    def total_payable(self):
        return self.amount + self.interest_amount()

    def total_repaid(self):
        result = self.repayments.filter(status='confirmed').aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0')

    def balance(self):
        return max(self.total_payable() - self.total_repaid(), Decimal('0'))

    def repayment_percent(self):
        total = self.total_payable()
        if total == 0:
            return 0
        return int((self.total_repaid() / total) * 100)

    def is_overdue(self):
        from datetime import date
        return self.due_date and date.today() > self.due_date and self.status in ('active', 'approved')


class LoanRepayment(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('confirmed', 'Confirmed'),
        ('rejected',  'Rejected'),
    ]
    PAYMENT_METHODS = [
        ('mpesa',  'M-Pesa'),
        ('bank',   'Bank Transfer'),
        ('cash',   'Cash'),
        ('cheque', 'Cheque'),
    ]
    loan           = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='repayments')
    amount         = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    reference      = models.CharField(max_length=255, blank=True, null=True)
    notes          = models.TextField(blank=True, null=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    date           = models.DateField(default=timezone.now)
    recorded_by    = models.ForeignKey(
        'User', null=True, blank=True, on_delete=models.SET_NULL, related_name='recorded_repayments'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Repayment {self.loan.member} {self.amount}"


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('contribution',   'Contribution'),
        ('expense',        'Expense'),
        ('loan_repayment', 'Loan Repayment'),
        ('withdrawal',     'Withdrawal'),
    ]
    chama      = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name='transactions')
    member     = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='transactions')
    type       = models.CharField(max_length=50, choices=TRANSACTION_TYPES)
    amount     = models.DecimalField(max_digits=12, decimal_places=2)
    reference  = models.CharField(max_length=255, null=True, blank=True)
    notes      = models.TextField(blank=True, null=True)
    meta       = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        'User', null=True, blank=True, related_name='created_transactions', on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} {self.amount} ({self.chama})"


# ── M-Pesa ────────────────────────────────────────────────────────────────────

class MpesaTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('success',   'Success'),
        ('failed',    'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    TYPE_CHOICES = [
        ('contribution',   'Contribution'),
        ('loan_repayment', 'Loan Repayment'),
    ]
    chama               = models.ForeignKey('Chama', on_delete=models.CASCADE, related_name='mpesa_transactions')
    member              = models.ForeignKey('User', on_delete=models.CASCADE, related_name='mpesa_transactions')
    phone               = models.CharField(max_length=20)
    amount              = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type    = models.CharField(max_length=20, choices=TYPE_CHOICES, default='contribution')
    checkout_request_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    merchant_request_id = models.CharField(max_length=100, null=True, blank=True)
    mpesa_receipt       = models.CharField(max_length=50, null=True, blank=True)
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    result_code         = models.CharField(max_length=10, null=True, blank=True)
    result_desc         = models.TextField(null=True, blank=True)
    contribution        = models.OneToOneField(
        'Contribution', null=True, blank=True, on_delete=models.SET_NULL, related_name='mpesa_tx'
    )
    loan_repayment      = models.OneToOneField(
        'LoanRepayment', null=True, blank=True, on_delete=models.SET_NULL, related_name='mpesa_tx'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'M-Pesa {self.phone} KES {self.amount} ({self.status})'


# ── Profile extras ────────────────────────────────────────────────────────────

class NotificationPreference(models.Model):
    FREQUENCY_CHOICES = [
        ('daily',   'Daily'),
        ('weekly',  'Weekly'),
        ('monthly', 'Monthly'),
        ('never',   'Never'),
    ]
    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_prefs')
    mpesa_alerts     = models.BooleanField(default=True)
    sms_reminders    = models.BooleanField(default=True)
    email_reports    = models.BooleanField(default=True)
    report_frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='weekly')
    two_fa_enabled   = models.BooleanField(default=False)

    def __str__(self):
        return f'Prefs({self.user})'


class MemberActivity(models.Model):
    EVENT_CHOICES = [
        ('contribution',  'Made Contribution'),
        ('loan_approved', 'Loan Approved'),
        ('loan_applied',  'Loan Applied'),
        ('loan_repaid',   'Loan Repaid'),
        ('fine_issued',   'Fine Issued'),
        ('fine_paid',     'Fine Paid'),
        ('chama_joined',  'Joined Chama'),
        ('chama_created', 'Created Chama'),
        ('role_changed',  'Role Changed'),
    ]
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    chama      = models.ForeignKey(
        'Chama', on_delete=models.CASCADE, related_name='activities', null=True, blank=True
    )
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    amount     = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    note       = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} – {self.event_type}'


# ── Subscription ──────────────────────────────────────────────────────────────

class SubscriptionPayment(models.Model):
    PLAN_CHOICES = [
        ('premium', 'Premium'),
        ('pro',     'Pro'),
    ]
    BILLING_CHOICES = [
        ('monthly', 'Monthly'),
        ('annual',  'Annual'),
    ]
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('completed', 'Completed'),
        ('failed',    'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    user                = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscription_payments')
    plan                = models.CharField(max_length=20, choices=PLAN_CHOICES)
    billing_cycle       = models.CharField(max_length=10, choices=BILLING_CHOICES, default='monthly')
    amount              = models.PositiveIntegerField()
    phone               = models.CharField(max_length=15)
    checkout_request_id = models.CharField(max_length=100, unique=True)
    mpesa_receipt       = models.CharField(max_length=50, blank=True)
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    failure_reason      = models.TextField(blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} — {self.plan} ({self.status})"


class UserSubscription(models.Model):
    PLAN_CHOICES = [
        ('free',    'Free'),
        ('premium', 'Premium'),
        ('pro',     'Pro'),
    ]
    BILLING_CHOICES = [
        ('monthly', 'Monthly'),
        ('annual',  'Annual'),
    ]
    user          = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan          = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CHOICES, default='monthly')
    amount_paid   = models.PositiveIntegerField(default=0)
    is_active     = models.BooleanField(default=True)
    expires_at    = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} — {self.plan}"

    @property
    def is_premium_or_above(self):
        return self.plan in ('premium', 'pro') and self.is_active

    @property
    def is_pro(self):
        return self.plan == 'pro' and self.is_active


# ── Chama Notification Settings ───────────────────────────────────────────────

class ChamaNotificationSettings(models.Model):
    chama = models.OneToOneField(Chama, on_delete=models.CASCADE, related_name='notification_settings')

    # Contribution alerts
    notif_contribution_due      = models.BooleanField(default=True)
    notif_contribution_received = models.BooleanField(default=True)
    notif_contribution_overdue  = models.BooleanField(default=True)
    notif_fine_issued           = models.BooleanField(default=False)
    reminder_days_before        = models.PositiveSmallIntegerField(default=3)

    # Loan & withdrawal alerts
    notif_loan_requested       = models.BooleanField(default=True)
    notif_loan_approved        = models.BooleanField(default=True)
    notif_loan_rejected        = models.BooleanField(default=True)
    notif_loan_repayment       = models.BooleanField(default=False)
    notif_withdrawal_requested = models.BooleanField(default=True)

    # Member activity
    notif_member_joined = models.BooleanField(default=True)
    notif_member_left   = models.BooleanField(default=True)
    notif_role_changed  = models.BooleanField(default=False)

    # Delivery channels
    channel_in_app = models.BooleanField(default=True)
    channel_email  = models.BooleanField(default=True)
    channel_sms    = models.BooleanField(default=False)
    from_email     = models.EmailField(default='noreply@chamapro.app')
    sms_sender     = models.CharField(max_length=11, default='ChamaPro')

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'NotifSettings({self.chama})'


# ── Chama Billing Payment ─────────────────────────────────────────────────────

class ChamaBillingPayment(models.Model):
    PLAN_CHOICES = [
        ('starter', 'Starter'),
        ('growth',  'Growth'),
        ('pro',     'Pro'),
    ]
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('paid',      'Paid'),
        ('failed',    'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    chama               = models.ForeignKey(
        Chama, on_delete=models.CASCADE, related_name='billing_payments'
    )
    paid_by             = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='chama_billing_payments'
    )
    plan_name           = models.CharField(max_length=20, choices=PLAN_CHOICES)
    amount              = models.PositiveIntegerField()
    phone               = models.CharField(max_length=15)
    checkout_request_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    mpesa_ref           = models.CharField(max_length=50, blank=True)
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    failure_reason      = models.TextField(blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.chama} — {self.plan_name} KES {self.amount} ({self.status})'

    @property
    def next_renewal(self):
        from datetime import timedelta
        return self.created_at.date() + timedelta(days=30)

    @property
    def member_limit(self):
        limits = {'starter': 20, 'growth': 50, 'pro': 9999}
        return limits.get(self.plan_name, 10)

    @property
    def sms_limit(self):
        limits = {'starter': 100, 'growth': 500, 'pro': 9999}
        return limits.get(self.plan_name, 0)

    @property
    def storage_limit_mb(self):
        limits = {'starter': 200, 'growth': 1000, 'pro': 9999}
        return limits.get(self.plan_name, 50)
    
    # ── Partner Applications ───────────────────────────────────────────────────────

class PartnerApplication(models.Model):
    ORG_TYPES = [
        ('financial', 'Financial institution'),
        ('sacco',     'Sacco'),
        ('ngo',       'NGO'),
        ('tech',      'Technology company'),
        ('consultant','Consultant'),
        ('other',     'Other'),
    ]
    OFFERING_CHOICES = [
        ('referrals',    'Client referrals'),
        ('reselling',    'Distribution / reselling'),
        ('integration',  'Technical integration'),
        ('comarketing',  'Co-marketing'),
        ('other',        'Other'),
    ]
    SCALE_CHOICES = [
        ('1-50',    '1 – 50'),
        ('51-200',  '51 – 200'),
        ('201-1000','201 – 1,000'),
        ('1000+',   '1,000+'),
    ]

    org_type        = models.CharField(max_length=20,  choices=ORG_TYPES)
    org_name        = models.CharField(max_length=200)
    contact_name    = models.CharField(max_length=200)
    contact_email   = models.EmailField()
    contact_phone   = models.CharField(max_length=30)
    job_title       = models.CharField(max_length=200, blank=True)
    offering        = models.CharField(max_length=20,  choices=OFFERING_CHOICES)
    expectations    = models.TextField(blank=True)
    scale           = models.CharField(max_length=20,  choices=SCALE_CHOICES, blank=True)
    agreed_terms    = models.BooleanField(default=False)
    submitted_at    = models.DateTimeField(auto_now_add=True)
    reviewed        = models.BooleanField(default=False)
    reviewed_at     = models.DateTimeField(null=True, blank=True)
    notes           = models.TextField(blank=True, help_text='Internal notes')

    class Meta:
        ordering = ['-submitted_at']
        verbose_name        = 'Partner application'
        verbose_name_plural = 'Partner applications'

    def __str__(self):
        return f"{self.org_name} ({self.get_org_type_display()}) – {self.submitted_at:%Y-%m-%d}"