"""
wallets/services.py

All wallet mutations go through this service layer.
Every public method is wrapped in an atomic transaction so the
wallet balance + ledger entry are always consistent.
"""
import uuid
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import F

from .models import Wallet, WalletTransaction, GroupWallet, WithdrawalRequest

logger = logging.getLogger(__name__)


def _generate_ref():
    return f"WLT-{uuid.uuid4().hex[:10].upper()}"


class InsufficientFundsError(Exception):
    pass


class WalletFrozenError(Exception):
    pass


class WalletService:
    """
    Handles all member wallet operations atomically.
    Always returns the WalletTransaction created.
    """

    @staticmethod
    @transaction.atomic
    def topup(wallet: Wallet, amount: Decimal, mpesa_reference: str = '', description: str = '') -> WalletTransaction:
        """
        Credit wallet from M-Pesa STK push callback.
        """
        if wallet.is_frozen:
            raise WalletFrozenError(f"Wallet for {wallet.membership} is frozen.")

        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Top-up amount must be positive.")

        # Lock the row
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        wallet.balance = F('balance') + amount
        wallet.save(update_fields=['balance', 'updated_at'])
        wallet.refresh_from_db()

        tx = WalletTransaction.objects.create(
            wallet=wallet,
            tx_type=WalletTransaction.TxType.TOPUP,
            amount=amount,
            status=WalletTransaction.Status.COMPLETED,
            reference=mpesa_reference or _generate_ref(),
            description=description or f"M-Pesa top-up of KES {amount}",
            balance_after=wallet.balance,
        )
        logger.info("TOPUP wallet=%s amount=%s ref=%s", wallet.pk, amount, tx.reference)
        return tx

    @staticmethod
    @transaction.atomic
    def debit_contribution(wallet: Wallet, amount: Decimal, contribution=None, description: str = '') -> WalletTransaction:
        """
        Debit member wallet for a contribution and credit the chama group wallet.
        Called by AutoDeductService and by manual contribution recording.
        """
        if wallet.is_frozen:
            raise WalletFrozenError(f"Wallet for {wallet.membership} is frozen.")

        amount = Decimal(str(amount))
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        if wallet.balance < amount:
            raise InsufficientFundsError(
                f"Insufficient balance. Has KES {wallet.balance}, needs KES {amount}."
            )

        # Debit member wallet
        wallet.balance = F('balance') - amount
        wallet.save(update_fields=['balance', 'updated_at'])
        wallet.refresh_from_db()

        ref = _generate_ref()
        tx = WalletTransaction.objects.create(
            wallet=wallet,
            tx_type=WalletTransaction.TxType.CONTRIBUTION,
            amount=amount,
            status=WalletTransaction.Status.COMPLETED,
            reference=ref,
            description=description or f"Contribution of KES {amount} to {wallet.membership.chama.name}",
            balance_after=wallet.balance,
            contribution=contribution,
        )

        # Credit group wallet
        group_wallet, _ = GroupWallet.objects.select_for_update().get_or_create(
            chama=wallet.membership.chama
        )
        group_wallet.balance = F('balance') + amount
        group_wallet.total_contributions_received = F('total_contributions_received') + amount
        group_wallet.save(update_fields=['balance', 'total_contributions_received', 'updated_at'])

        logger.info("CONTRIBUTION wallet=%s amount=%s ref=%s", wallet.pk, amount, ref)
        return tx

    @staticmethod
    @transaction.atomic
    def debit_loan_repayment(wallet: Wallet, amount: Decimal, loan=None, description: str = '') -> WalletTransaction:
        """
        Debit member wallet for a loan repayment.
        """
        if wallet.is_frozen:
            raise WalletFrozenError(f"Wallet for {wallet.membership} is frozen.")

        amount = Decimal(str(amount))
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        if wallet.balance < amount:
            raise InsufficientFundsError(
                f"Insufficient balance for loan repayment. Has KES {wallet.balance}, needs KES {amount}."
            )

        wallet.balance = F('balance') - amount
        wallet.save(update_fields=['balance', 'updated_at'])
        wallet.refresh_from_db()

        ref = _generate_ref()
        tx = WalletTransaction.objects.create(
            wallet=wallet,
            tx_type=WalletTransaction.TxType.LOAN_REPAYMENT,
            amount=amount,
            status=WalletTransaction.Status.COMPLETED,
            reference=ref,
            description=description or f"Loan repayment of KES {amount}",
            balance_after=wallet.balance,
            loan=loan,
        )

        # Credit group wallet
        group_wallet, _ = GroupWallet.objects.select_for_update().get_or_create(
            chama=wallet.membership.chama
        )
        group_wallet.balance = F('balance') + amount
        group_wallet.save(update_fields=['balance', 'updated_at'])

        logger.info("LOAN_REPAYMENT wallet=%s amount=%s ref=%s", wallet.pk, amount, ref)
        return tx

    @staticmethod
    @transaction.atomic
    def peer_transfer(from_wallet: Wallet, to_wallet: Wallet, amount: Decimal, description: str = '') -> tuple:
        """
        Transfer between two member wallets in the same chama.
        Returns (debit_tx, credit_tx).
        """
        if from_wallet.membership.chama != to_wallet.membership.chama:
            raise ValueError("Peer transfers are only allowed within the same chama.")

        if from_wallet.is_frozen or to_wallet.is_frozen:
            raise WalletFrozenError("One or both wallets are frozen.")

        amount = Decimal(str(amount))

        # Lock both rows in a consistent order to avoid deadlocks
        wallets = Wallet.objects.select_for_update().filter(
            pk__in=[from_wallet.pk, to_wallet.pk]
        ).order_by('pk')
        w_map = {w.pk: w for w in wallets}
        from_w = w_map[from_wallet.pk]
        to_w   = w_map[to_wallet.pk]

        if from_w.balance < amount:
            raise InsufficientFundsError(f"Insufficient balance. Has KES {from_w.balance}, needs KES {amount}.")

        ref = _generate_ref()

        from_w.balance = F('balance') - amount
        from_w.save(update_fields=['balance', 'updated_at'])
        from_w.refresh_from_db()

        to_w.balance = F('balance') + amount
        to_w.save(update_fields=['balance', 'updated_at'])
        to_w.refresh_from_db()

        desc = description or (
            f"Transfer KES {amount} to {to_w.membership.user.get_full_name()}"
        )

        debit_tx = WalletTransaction.objects.create(
            wallet=from_w,
            tx_type=WalletTransaction.TxType.TRANSFER_OUT,
            amount=amount,
            status=WalletTransaction.Status.COMPLETED,
            reference=ref,
            description=desc,
            balance_after=from_w.balance,
        )
        credit_tx = WalletTransaction.objects.create(
            wallet=to_w,
            tx_type=WalletTransaction.TxType.TRANSFER_IN,
            amount=amount,
            status=WalletTransaction.Status.COMPLETED,
            reference=ref,
            description=f"Transfer KES {amount} from {from_w.membership.user.get_full_name()}",
            balance_after=to_w.balance,
            peer_wallet=debit_tx,
        )
        debit_tx.peer_wallet = credit_tx
        debit_tx.save(update_fields=['peer_wallet'])

        logger.info("TRANSFER from=%s to=%s amount=%s ref=%s", from_w.pk, to_w.pk, amount, ref)
        return debit_tx, credit_tx

    @staticmethod
    @transaction.atomic
    def request_withdrawal(wallet: Wallet, amount: Decimal, phone_number: str) -> WithdrawalRequest:
        """
        Member requests a withdrawal. Holds the funds (freezes amount)
        pending admin approval. Actual M-Pesa payout fires on approval.
        """
        if wallet.is_frozen:
            raise WalletFrozenError("Wallet is frozen. Contact your chama admin.")

        amount = Decimal(str(amount))
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        if wallet.balance < amount:
            raise InsufficientFundsError(f"Insufficient balance. Has KES {wallet.balance}, needs KES {amount}.")

        # Reserve the amount immediately
        wallet.balance = F('balance') - amount
        wallet.save(update_fields=['balance', 'updated_at'])
        wallet.refresh_from_db()

        # Pending transaction (will complete or reverse on admin action)
        WalletTransaction.objects.create(
            wallet=wallet,
            tx_type=WalletTransaction.TxType.WITHDRAWAL,
            amount=amount,
            status=WalletTransaction.Status.PENDING,
            reference=_generate_ref(),
            description=f"Withdrawal request of KES {amount} to {phone_number}",
            balance_after=wallet.balance,
        )

        req = WithdrawalRequest.objects.create(
            wallet=wallet,
            amount=amount,
            phone_number=phone_number,
        )
        logger.info("WITHDRAWAL_REQUEST wallet=%s amount=%s phone=%s", wallet.pk, amount, phone_number)
        return req

    @staticmethod
    @transaction.atomic
    def approve_withdrawal(request: WithdrawalRequest, approved_by) -> WithdrawalRequest:
        """
        Treasurer approves. Marks request approved and fires M-Pesa B2C.
        M-Pesa callback will flip status to PAID.
        """
        if request.status != WithdrawalRequest.Status.PENDING:
            raise ValueError("Only pending requests can be approved.")

        request.status = WithdrawalRequest.Status.APPROVED
        request.approved_by = approved_by
        request.approved_at = timezone.now()
        request.save()

        # Fire M-Pesa B2C (imported here to avoid circular imports)
        from .mpesa import initiate_b2c
        initiate_b2c(request)

        return request

    @staticmethod
    @transaction.atomic
    def reject_withdrawal(request: WithdrawalRequest, rejected_by, reason: str = '') -> WithdrawalRequest:
        """
        Treasurer rejects — refund the reserved amount back to wallet.
        """
        if request.status != WithdrawalRequest.Status.PENDING:
            raise ValueError("Only pending requests can be rejected.")

        wallet = Wallet.objects.select_for_update().get(pk=request.wallet.pk)
        wallet.balance = F('balance') + request.amount
        wallet.save(update_fields=['balance', 'updated_at'])
        wallet.refresh_from_db()

        WalletTransaction.objects.create(
            wallet=wallet,
            tx_type=WalletTransaction.TxType.REVERSAL,
            amount=request.amount,
            status=WalletTransaction.Status.COMPLETED,
            reference=_generate_ref(),
            description=f"Reversal: withdrawal rejection – {reason}",
            balance_after=wallet.balance,
        )

        # Flip the pending withdrawal tx to failed
        wallet.transactions.filter(
            tx_type=WalletTransaction.TxType.WITHDRAWAL,
            status=WalletTransaction.Status.PENDING,
        ).order_by('-created_at').first().and_update_status_if_exists(
            WalletTransaction.Status.FAILED
        ) if False else None  # handled below

        wallet.transactions.filter(
            tx_type=WalletTransaction.TxType.WITHDRAWAL,
            status=WalletTransaction.Status.PENDING,
        ).update(status=WalletTransaction.Status.FAILED)

        request.status = WithdrawalRequest.Status.REJECTED
        request.rejection_reason = reason
        request.approved_by = rejected_by
        request.approved_at = timezone.now()
        request.save()

        logger.info("WITHDRAWAL_REJECTED req=%s reason=%s", request.pk, reason)
        return request


class AutoDeductService:
    """
    Runs daily (via Celery beat or management command).
    Finds all active memberships with a contribution due today,
    checks wallet balance, and auto-deducts if sufficient.
    Skips members with insufficient balance (logged + flagged).
    """

    @staticmethod
    def run_for_chama(chama):
        """
        Process all due contributions for one chama.
        Returns a summary dict.
        """
        from chamas.models import Membership  # local import to avoid circular

        results = {'success': [], 'skipped': [], 'errors': []}
        today = timezone.now().date()

        memberships = Membership.objects.filter(
            chama=chama,
            active=True,
        ).select_related('wallet', 'user')

        for membership in memberships:
            if not AutoDeductService._is_due_today(chama, today):
                continue

            try:
                wallet = membership.wallet
            except Wallet.DoesNotExist:
                results['skipped'].append({
                    'member': str(membership),
                    'reason': 'No wallet found',
                })
                continue

            amount = chama.contribution_amount
            if wallet.balance < amount:
                results['skipped'].append({
                    'member': str(membership),
                    'reason': f'Insufficient balance (KES {wallet.balance} < KES {amount})',
                })
                logger.warning(
                    "AUTO_DEDUCT skipped: member=%s balance=%s required=%s",
                    membership.pk, wallet.balance, amount,
                )
                continue

            try:
                tx = WalletService.debit_contribution(
                    wallet=wallet,
                    amount=amount,
                    description=f"Auto-deduction: {chama.name} contribution {today}",
                )
                results['success'].append({
                    'member': str(membership),
                    'amount': str(amount),
                    'ref': tx.reference,
                })
                logger.info(
                    "AUTO_DEDUCT success: member=%s amount=%s ref=%s",
                    membership.pk, amount, tx.reference,
                )
            except (InsufficientFundsError, WalletFrozenError) as exc:
                results['skipped'].append({
                    'member': str(membership),
                    'reason': str(exc),
                })
            except Exception as exc:
                results['errors'].append({
                    'member': str(membership),
                    'error': str(exc),
                })
                logger.exception("AUTO_DEDUCT error: member=%s", membership.pk)

        return results

    @staticmethod
    def _is_due_today(chama, today):
        """
        Basic due-date check. Extend this to support
        weekly/monthly/custom schedules as needed.
        """
        # If chama has a contribution_day field (day of month):
        if hasattr(chama, 'contribution_day') and chama.contribution_day:
            return today.day == chama.contribution_day

        # Fallback: first of every month
        return today.day == 1

    @staticmethod
    def run_all_chamas():
        """
        Entry point called by Celery beat task or management command.
        """
        from chamas.models import Chama
        summary = {}
        for chama in Chama.objects.filter(is_active=True):
            summary[chama.name] = AutoDeductService.run_for_chama(chama)
        return summary