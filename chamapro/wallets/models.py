from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Wallet(models.Model):
    """
    One wallet per Membership (member inside a specific chama).
    Balance is always the ground truth — derived from WalletTransaction
    records but cached here for fast reads.
    """
    membership = models.OneToOneField(
        'chamapro.Membership',
        on_delete=models.CASCADE,
        related_name='wallet',
    )
    balance    = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    is_frozen  = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Member Wallet'
        verbose_name_plural = 'Member Wallets'
        ordering            = ['-created_at']

    def __str__(self):
        return (
            f"{self.membership.user.get_full_name()} – "
            f"{self.membership.chama.name} Wallet (KES {self.balance})"
        )

    def recalculate_balance(self):
        """
        Recalculate balance from completed transactions.
        Call this after bulk imports or audits.
        """
        credits = self.transactions.filter(
            status=WalletTransaction.Status.COMPLETED,
            tx_type__in=[
                WalletTransaction.TxType.TOPUP,
                WalletTransaction.TxType.TRANSFER_IN,
            ]
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        debits = self.transactions.filter(
            status=WalletTransaction.Status.COMPLETED,
            tx_type__in=[
                WalletTransaction.TxType.CONTRIBUTION,
                WalletTransaction.TxType.LOAN_REPAYMENT,
                WalletTransaction.TxType.WITHDRAWAL,
                WalletTransaction.TxType.TRANSFER_OUT,
            ]
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        self.balance = credits - debits
        self.save(update_fields=['balance', 'updated_at'])
        return self.balance


class WalletTransaction(models.Model):
    """
    Immutable ledger entry for every wallet movement.
    Never delete or update a completed transaction — reverse with a new entry.
    """

    class TxType(models.TextChoices):
        TOPUP          = 'topup',          'M-Pesa Top-Up'
        CONTRIBUTION   = 'contribution',   'Contribution'
        LOAN_REPAYMENT = 'loan_repayment', 'Loan Repayment'
        WITHDRAWAL     = 'withdrawal',     'Withdrawal to M-Pesa'
        TRANSFER_IN    = 'transfer_in',    'Transfer In'
        TRANSFER_OUT   = 'transfer_out',   'Transfer Out'
        REVERSAL       = 'reversal',       'Reversal'

    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED    = 'failed',    'Failed'
        REVERSED  = 'reversed',  'Reversed'

    wallet        = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    tx_type       = models.CharField(max_length=20, choices=TxType.choices)
    amount        = models.DecimalField(max_digits=12, decimal_places=2)
    status        = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reference     = models.CharField(max_length=100, blank=True, db_index=True)
    description   = models.TextField(blank=True)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Audit trail links
    contribution = models.ForeignKey(
        'chamapro.Contribution',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='wallet_transactions',
    )
    loan = models.ForeignKey(
        'chamapro.Loan',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='wallet_transactions',
    )
    peer_wallet = models.ForeignKey(
        'self',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='paired_transaction',
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Wallet Transaction'
        verbose_name_plural = 'Wallet Transactions'
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', 'status', 'tx_type']),
            models.Index(fields=['reference']),
        ]

    def __str__(self):
        return f"[{self.get_tx_type_display()}] KES {self.amount} – {self.wallet} ({self.status})"


class GroupWallet(models.Model):
    """
    Chama-level treasury wallet.
    Credited when member wallet contributions are deducted.
    Debited on approved group expenses or disbursements.
    """
    chama                        = models.OneToOneField(
        'chamapro.Chama',
        on_delete=models.CASCADE,
        related_name='group_wallet',
    )
    balance                      = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total_contributions_received = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total_disbursed              = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    created_at                   = models.DateTimeField(auto_now_add=True)
    updated_at                   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Group Wallet'
        verbose_name_plural = 'Group Wallets'

    def __str__(self):
        return f"{self.chama.name} Group Wallet (KES {self.balance})"


class WithdrawalRequest(models.Model):
    """
    Member requests to pull money from their wallet back to M-Pesa.
    Admin/treasurer approves or rejects before M-Pesa B2C fires.
    """

    class Status(models.TextChoices):
        PENDING  = 'pending',  'Pending Approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        PAID     = 'paid',     'Paid Out'
        FAILED   = 'failed',   'Payout Failed'

    wallet           = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='withdrawal_requests')
    amount           = models.DecimalField(max_digits=12, decimal_places=2)
    phone_number     = models.CharField(max_length=15)
    status           = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    rejection_reason = models.TextField(blank=True)
    mpesa_reference  = models.CharField(max_length=100, blank=True)
    approved_by      = models.ForeignKey(
        settings.AUTH_USER_MODEL,           # ← fixed: was 'auth.User'
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_withdrawals',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Withdrawal Request'
        verbose_name_plural = 'Withdrawal Requests'
        ordering            = ['-created_at']

    def __str__(self):
        return (
            f"Withdrawal KES {self.amount} – "
            f"{self.wallet.membership.user.get_full_name()} ({self.status})"
        )

class Deposit(models.Model):
    """
    Formal deposit record for all sources: M-Pesa STK, cash, bank transfer.
    Created by member (STK) or treasurer (manual/bank).
    Status flows: pending → confirmed → credited (or rejected).
    """

    class Source(models.TextChoices):
        MPESA  = 'mpesa',  'M-Pesa'
        CASH   = 'cash',   'Cash'
        BANK   = 'bank',   'Bank Transfer'

    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        CREDITED  = 'credited',  'Credited to Wallet'
        REJECTED  = 'rejected',  'Rejected'

    wallet       = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='deposits')
    source       = models.CharField(max_length=10, choices=Source.choices, default=Source.MPESA)
    amount       = models.DecimalField(max_digits=12, decimal_places=2)
    status       = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    reference    = models.CharField(max_length=100, blank=True, db_index=True,
                                    help_text='M-Pesa receipt, bank ref, or manual note')
    phone_number = models.CharField(max_length=15, blank=True,
                                    help_text='For M-Pesa STK deposits')
    proof_file   = models.FileField(upload_to='deposit_proofs/', blank=True, null=True,
                                    help_text='Receipt image or bank slip (optional)')
    notes        = models.TextField(blank=True)

    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='confirmed_deposits',
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Deposit'
        verbose_name_plural = 'Deposits'
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', 'status']),
            models.Index(fields=['reference']),
        ]

    def __str__(self):
        return (
            f"[{self.get_source_display()}] KES {self.amount} – "
            f"{self.wallet.membership.user.get_full_name()} ({self.status})"
        )