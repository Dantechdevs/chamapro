"""
wallets/views.py
"""
import json
import logging
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from chamapro.models import Chama, Membership
from .models import Wallet, WalletTransaction, GroupWallet, WithdrawalRequest, Deposit
from .services import WalletService, DepositService, InsufficientFundsError, WalletFrozenError
from .mpesa import initiate_stk_push, process_stk_callback, process_b2c_result

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _get_membership(user, chama):
    return get_object_or_404(Membership, user=user, chama=chama, active=True)


def _get_or_create_wallet(membership):
    wallet, _ = Wallet.objects.get_or_create(membership=membership)
    return wallet


def _is_admin_or_manager(membership):
    return membership.role in ('admin', 'manager')


# ─────────────────────────────────────────────
# Member Wallet Dashboard
# ─────────────────────────────────────────────

@login_required
def wallet_dashboard(request, chama_id):
    chama       = get_object_or_404(Chama, pk=chama_id)
    membership  = _get_membership(request.user, chama)
    wallet      = _get_or_create_wallet(membership)

    page        = request.GET.get('page', 1)
    tx_filter   = request.GET.get('type', '')

    txs = wallet.transactions.all()
    if tx_filter:
        txs = txs.filter(tx_type=tx_filter)

    paginator   = Paginator(txs, 20)
    page_obj    = paginator.get_page(page)

    # Stats
    total_topups = wallet.transactions.filter(
        tx_type=WalletTransaction.TxType.TOPUP,
        status=WalletTransaction.Status.COMPLETED,
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

    total_contributed = wallet.transactions.filter(
        tx_type=WalletTransaction.TxType.CONTRIBUTION,
        status=WalletTransaction.Status.COMPLETED,
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

    pending_withdrawals = wallet.withdrawal_requests.filter(
        status=WithdrawalRequest.Status.PENDING
    )

    # All chama members for peer transfer dropdown
    other_members = Membership.objects.filter(
        chama=chama, active=True
    ).exclude(pk=membership.pk).select_related('user', 'wallet')

    tx_types = WalletTransaction.TxType.choices

    context = {
        'chama':               chama,
        'membership':          membership,
        'wallet':              wallet,
        'page_obj':            page_obj,
        'tx_filter':           tx_filter,
        'tx_types':            tx_types,
        'total_topups':        total_topups,
        'total_contributed':   total_contributed,
        'pending_withdrawals': pending_withdrawals,
        'other_members':       other_members,
        'active_chama':        chama,
        'is_admin':            _is_admin_or_manager(membership),
    }
    return render(request, 'wallets/wallet_dashboard.html', context)


# ─────────────────────────────────────────────
# STK Push Top-Up
# ─────────────────────────────────────────────

@login_required
@require_POST
def initiate_topup(request, chama_id):
    chama      = get_object_or_404(Chama, pk=chama_id)
    membership = _get_membership(request.user, chama)
    wallet     = _get_or_create_wallet(membership)

    phone  = request.POST.get('phone_number', '').strip()
    amount = request.POST.get('amount', '').strip()

    try:
        amount = Decimal(amount)
        if amount < Decimal('10'):
            raise ValueError("Minimum top-up is KES 10.")
    except (InvalidOperation, ValueError) as e:
        messages.error(request, str(e))
        return redirect('wallet_dashboard', chama_id=chama_id)

    try:
        result = initiate_stk_push(wallet=wallet, amount=amount, phone_number=phone)
        if result.get('ResponseCode') == '0':
            messages.success(
                request,
                f"STK push sent to {phone}. Enter your M-Pesa PIN to complete the top-up.",
            )
        else:
            messages.error(request, f"M-Pesa error: {result.get('errorMessage', 'Unknown error')}")
    except Exception as exc:
        logger.exception("STK push failed for wallet=%s", wallet.pk)
        messages.error(request, "Could not initiate M-Pesa request. Try again.")

    return redirect('wallet_dashboard', chama_id=chama_id)


# ─────────────────────────────────────────────
# Peer Transfer
# ─────────────────────────────────────────────

@login_required
@require_POST
def peer_transfer(request, chama_id):
    chama      = get_object_or_404(Chama, pk=chama_id)
    membership = _get_membership(request.user, chama)
    from_wallet = _get_or_create_wallet(membership)

    to_membership_id = request.POST.get('to_membership_id')
    amount_raw       = request.POST.get('amount', '').strip()
    description      = request.POST.get('description', '').strip()

    try:
        to_membership = get_object_or_404(Membership, pk=to_membership_id, chama=chama, active=True)
        to_wallet     = _get_or_create_wallet(to_membership)
        amount        = Decimal(amount_raw)
        if amount <= 0:
            raise ValueError("Amount must be positive.")
    except (InvalidOperation, ValueError) as e:
        messages.error(request, str(e))
        return redirect('wallet_dashboard', chama_id=chama_id)

    try:
        WalletService.peer_transfer(from_wallet, to_wallet, amount, description)
        messages.success(
            request,
            f"KES {amount:,.2f} transferred to {to_membership.user.get_full_name()} successfully.",
        )
    except (InsufficientFundsError, WalletFrozenError) as exc:
        messages.error(request, str(exc))
    except Exception:
        logger.exception("Peer transfer error chama=%s", chama_id)
        messages.error(request, "Transfer failed. Please try again.")

    return redirect('wallet_dashboard', chama_id=chama_id)


# ─────────────────────────────────────────────
# Withdrawal Request
# ─────────────────────────────────────────────

@login_required
@require_POST
def request_withdrawal(request, chama_id):
    chama      = get_object_or_404(Chama, pk=chama_id)
    membership = _get_membership(request.user, chama)
    wallet     = _get_or_create_wallet(membership)

    phone      = request.POST.get('phone_number', '').strip()
    amount_raw = request.POST.get('amount', '').strip()

    try:
        amount = Decimal(amount_raw)
        if amount < Decimal('10'):
            raise ValueError("Minimum withdrawal is KES 10.")
    except (InvalidOperation, ValueError) as e:
        messages.error(request, str(e))
        return redirect('wallet_dashboard', chama_id=chama_id)

    try:
        WalletService.request_withdrawal(wallet, amount, phone)
        messages.success(
            request,
            f"Withdrawal request of KES {amount:,.2f} submitted. Your admin will process it shortly.",
        )
    except (InsufficientFundsError, WalletFrozenError) as exc:
        messages.error(request, str(exc))

    return redirect('wallet_dashboard', chama_id=chama_id)


# ─────────────────────────────────────────────
# Admin — Group Wallet & Withdrawal Queue
# ─────────────────────────────────────────────

@login_required
def group_wallet(request, chama_id):
    chama       = get_object_or_404(Chama, pk=chama_id)
    membership  = _get_membership(request.user, chama)

    if not _is_admin_or_manager(membership):
        messages.error(request, "Access denied.")
        return redirect('wallet_dashboard', chama_id=chama_id)

    group_w, _ = GroupWallet.objects.get_or_create(chama=chama)

    pending_requests = WithdrawalRequest.objects.filter(
        wallet__membership__chama=chama,
        status=WithdrawalRequest.Status.PENDING,
    ).select_related('wallet__membership__user')

    all_requests = WithdrawalRequest.objects.filter(
        wallet__membership__chama=chama,
    ).select_related('wallet__membership__user', 'approved_by').order_by('-created_at')

    paginator = Paginator(all_requests, 20)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    # Per-member wallet summary
    member_wallets = Wallet.objects.filter(
        membership__chama=chama,
        membership__active=True,
    ).select_related('membership__user').order_by('membership__user__first_name')

    context = {
        'chama':            chama,
        'membership':       membership,
        'group_wallet':     group_w,
        'pending_requests': pending_requests,
        'page_obj':         page_obj,
        'member_wallets':   member_wallets,
        'active_chama':     chama,
    }
    return render(request, 'wallets/group_wallet.html', context)


@login_required
@require_POST
def approve_withdrawal(request, chama_id, req_id):
    chama      = get_object_or_404(Chama, pk=chama_id)
    membership = _get_membership(request.user, chama)

    if not _is_admin_or_manager(membership):
        messages.error(request, "Access denied.")
        return redirect('group_wallet', chama_id=chama_id)

    wr = get_object_or_404(WithdrawalRequest, pk=req_id, wallet__membership__chama=chama)

    try:
        WalletService.approve_withdrawal(wr, request.user)
        messages.success(request, f"Withdrawal #{wr.pk} approved. M-Pesa payout initiated.")
    except Exception as exc:
        messages.error(request, f"Approval failed: {exc}")

    return redirect('group_wallet', chama_id=chama_id)


@login_required
@require_POST
def reject_withdrawal(request, chama_id, req_id):
    chama      = get_object_or_404(Chama, pk=chama_id)
    membership = _get_membership(request.user, chama)

    if not _is_admin_or_manager(membership):
        messages.error(request, "Access denied.")
        return redirect('group_wallet', chama_id=chama_id)

    wr     = get_object_or_404(WithdrawalRequest, pk=req_id, wallet__membership__chama=chama)
    reason = request.POST.get('reason', '').strip()

    try:
        WalletService.reject_withdrawal(wr, request.user, reason)
        messages.success(request, f"Withdrawal #{wr.pk} rejected and funds returned to member.")
    except Exception as exc:
        messages.error(request, f"Rejection failed: {exc}")

    return redirect('group_wallet', chama_id=chama_id)


# ─────────────────────────────────────────────
# M-Pesa Callbacks (no CSRF — Safaricom posts here)
# ─────────────────────────────────────────────

@csrf_exempt
def stk_callback(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'ignored'})
    try:
        data = json.loads(request.body)
        process_stk_callback(data)
    except Exception:
        logger.exception("STK callback processing error")
    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'})


@csrf_exempt
def b2c_result(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'ignored'})
    try:
        data = json.loads(request.body)
        process_b2c_result(data)
    except Exception:
        logger.exception("B2C result processing error")
    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'})


@csrf_exempt
def b2c_timeout(request):
    logger.warning("B2C timeout hit. Body: %s", request.body)
    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'})

# ─────────────────────────────────────────────
# DEPOSITS — Member view
# ─────────────────────────────────────────────

@login_required
def deposit_page(request, chama_id):
    chama      = get_object_or_404(Chama, pk=chama_id)
    membership = _get_membership(request.user, chama)
    wallet     = _get_or_create_wallet(membership)

    deposits   = wallet.deposits.all().order_by('-created_at')
    paginator  = Paginator(deposits, 15)
    page_obj   = paginator.get_page(request.GET.get('page', 1))

    context = {
        'chama':       chama,
        'membership':  membership,
        'wallet':      wallet,
        'page_obj':    page_obj,
        'active_chama': chama,
        'is_admin':    _is_admin_or_manager(membership),
    }
    return render(request, 'wallets/deposits.html', context)


@login_required
@require_POST
def submit_manual_deposit(request, chama_id):
    """Member submits a manual deposit record (cash/bank) for treasurer to confirm."""
    chama      = get_object_or_404(Chama, pk=chama_id)
    membership = _get_membership(request.user, chama)
    wallet     = _get_or_create_wallet(membership)

    source    = request.POST.get('source', Deposit.Source.CASH)
    reference = request.POST.get('reference', '').strip()
    notes     = request.POST.get('notes', '').strip()
    proof     = request.FILES.get('proof_file')
    amount_raw = request.POST.get('amount', '').strip()

    try:
        amount = Decimal(amount_raw)
        if amount <= 0:
            raise ValueError("Amount must be positive.")
    except (InvalidOperation, ValueError) as e:
        messages.error(request, str(e))
        return redirect('deposit_page', chama_id=chama_id)

    DepositService.record_manual(
        wallet=wallet,
        amount=amount,
        source=source,
        reference=reference,
        notes=notes,
        proof_file=proof,
        recorded_by=request.user,
    )
    messages.success(request, f"Deposit of KES {amount:,.2f} submitted. Awaiting treasurer confirmation.")
    return redirect('deposit_page', chama_id=chama_id)


# ─────────────────────────────────────────────
# DEPOSITS — Admin queue
# ─────────────────────────────────────────────

@login_required
def admin_deposits(request, chama_id):
    chama      = get_object_or_404(Chama, pk=chama_id)
    membership = _get_membership(request.user, chama)

    if not _is_admin_or_manager(membership):
        messages.error(request, "Access denied.")
        return redirect('deposit_page', chama_id=chama_id)

    status_filter = request.GET.get('status', 'pending')
    deposits = Deposit.objects.filter(
        wallet__membership__chama=chama,
    ).select_related('wallet__membership__user', 'confirmed_by')

    if status_filter != 'all':
        deposits = deposits.filter(status=status_filter)

    deposits = deposits.order_by('-created_at')
    paginator = Paginator(deposits, 20)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    context = {
        'chama':         chama,
        'membership':    membership,
        'page_obj':      page_obj,
        'status_filter': status_filter,
        'active_chama':  chama,
        'is_admin':      True,
        'status_choices': Deposit.Status.choices,
    }
    return render(request, 'wallets/admin_deposits.html', context)


@login_required
@require_POST
def confirm_deposit(request, chama_id, deposit_id):
    chama      = get_object_or_404(Chama, pk=chama_id)
    membership = _get_membership(request.user, chama)

    if not _is_admin_or_manager(membership):
        messages.error(request, "Access denied.")
        return redirect('admin_deposits', chama_id=chama_id)

    deposit = get_object_or_404(Deposit, pk=deposit_id, wallet__membership__chama=chama)
    try:
        DepositService.confirm(deposit, request.user)
        messages.success(request, f"Deposit #{deposit.pk} confirmed — KES {deposit.amount:,.2f} credited to {deposit.wallet.membership.user.get_full_name()}.")
    except Exception as exc:
        messages.error(request, f"Could not confirm: {exc}")

    return redirect('admin_deposits', chama_id=chama_id)


@login_required
@require_POST
def reject_deposit(request, chama_id, deposit_id):
    chama      = get_object_or_404(Chama, pk=chama_id)
    membership = _get_membership(request.user, chama)

    if not _is_admin_or_manager(membership):
        messages.error(request, "Access denied.")
        return redirect('admin_deposits', chama_id=chama_id)

    deposit = get_object_or_404(Deposit, pk=deposit_id, wallet__membership__chama=chama)
    reason  = request.POST.get('reason', '').strip()

    try:
        DepositService.reject(deposit, request.user, reason)
        messages.success(request, f"Deposit #{deposit.pk} rejected.")
    except Exception as exc:
        messages.error(request, f"Could not reject: {exc}")

    return redirect('admin_deposits', chama_id=chama_id)


# ─────────────────────────────────────────────
# WITHDRAWALS — Dedicated member page
# ─────────────────────────────────────────────

@login_required
def withdrawal_page(request, chama_id):
    chama      = get_object_or_404(Chama, pk=chama_id)
    membership = _get_membership(request.user, chama)
    wallet     = _get_or_create_wallet(membership)

    withdrawals = wallet.withdrawal_requests.all().order_by('-created_at')
    paginator   = Paginator(withdrawals, 15)
    page_obj    = paginator.get_page(request.GET.get('page', 1))

    context = {
        'chama':       chama,
        'membership':  membership,
        'wallet':      wallet,
        'page_obj':    page_obj,
        'active_chama': chama,
        'is_admin':    _is_admin_or_manager(membership),
    }
    return render(request, 'wallets/withdrawals.html', context)


# ─────────────────────────────────────────────
# WITHDRAWALS — Admin queue
# ─────────────────────────────────────────────

@login_required
def admin_withdrawals(request, chama_id):
    chama      = get_object_or_404(Chama, pk=chama_id)
    membership = _get_membership(request.user, chama)

    if not _is_admin_or_manager(membership):
        messages.error(request, "Access denied.")
        return redirect('withdrawal_page', chama_id=chama_id)

    status_filter = request.GET.get('status', 'pending')
    withdrawals = WithdrawalRequest.objects.filter(
        wallet__membership__chama=chama,
    ).select_related('wallet__membership__user', 'approved_by')

    if status_filter != 'all':
        withdrawals = withdrawals.filter(status=status_filter)

    withdrawals = withdrawals.order_by('-created_at')
    paginator   = Paginator(withdrawals, 20)
    page_obj    = paginator.get_page(request.GET.get('page', 1))

    context = {
        'chama':          chama,
        'membership':     membership,
        'page_obj':       page_obj,
        'status_filter':  status_filter,
        'active_chama':   chama,
        'is_admin':       True,
        'status_choices': WithdrawalRequest.Status.choices,
    }
    return render(request, 'wallets/admin_withdrawals.html', context)