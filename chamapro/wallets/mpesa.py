"""
wallets/mpesa.py

M-Pesa Daraja API integration for the wallet module.
Handles:
  - STK Push (C2B) for wallet top-ups
  - B2C for withdrawal payouts
  - Callback processing for both

Settings required in settings.py / .env:
    MPESA_CONSUMER_KEY
    MPESA_CONSUMER_SECRET
    MPESA_SHORTCODE
    MPESA_PASSKEY            (STK push)
    MPESA_B2C_SHORTCODE
    MPESA_B2C_INITIATOR_NAME
    MPESA_B2C_SECURITY_CREDENTIAL
    MPESA_CALLBACK_BASE_URL  (publicly reachable, e.g. via ngrok in dev)
"""
import base64
import logging
import re
import requests
from datetime import datetime
from decimal import Decimal
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

DARAJA_BASE = "https://api.safaricom.co.ke"   # prod
# DARAJA_BASE = "https://sandbox.safaricom.co.ke"  # sandbox


# ─────────────────────────────────────────────
# Auth helper
# ─────────────────────────────────────────────

def _get_access_token() -> str:
    url = f"{DARAJA_BASE}/oauth/v1/generate?grant_type=client_credentials"
    resp = requests.get(
        url,
        auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()['access_token']


def _stk_password() -> tuple[str, str]:
    """Returns (password_b64, timestamp)"""
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    raw = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{ts}"
    password = base64.b64encode(raw.encode()).decode()
    return password, ts


# ─────────────────────────────────────────────
# Normalize Kenyan phone
# ─────────────────────────────────────────────

def normalize_phone(phone: str) -> str:
    """Convert 07xx / +2547xx → 2547xx"""
    phone = re.sub(r'\s+', '', phone)
    if phone.startswith('+'):
        phone = phone[1:]
    if phone.startswith('07') or phone.startswith('01'):
        phone = '254' + phone[1:]
    return phone


# ─────────────────────────────────────────────
# STK Push — Wallet Top-Up
# ─────────────────────────────────────────────

def initiate_stk_push(wallet, amount: Decimal, phone_number: str) -> dict:
    """
    Trigger an M-Pesa STK push to top up `wallet`.
    Returns the raw Daraja response dict.
    The actual credit happens in `stk_callback` when M-Pesa confirms.
    """
    from .models import WalletTransaction

    phone = normalize_phone(phone_number)
    token = _get_access_token()
    password, ts = _stk_password()
    amount_int = int(amount)  # Daraja rejects decimals

    callback_url = (
        f"{settings.MPESA_CALLBACK_BASE_URL}/wallets/mpesa/stk-callback/"
    )

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": ts,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount_int,
        "PartyA": phone,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": f"WALLET-{wallet.pk}",
        "TransactionDesc": f"ChamaPro wallet top-up KES {amount_int}",
    }

    resp = requests.post(
        f"{DARAJA_BASE}/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    data = resp.json()
    logger.info("STK_PUSH wallet=%s phone=%s response=%s", wallet.pk, phone, data)

    # Create a pending transaction immediately so we can match the callback
    if data.get('ResponseCode') == '0':
        WalletTransaction.objects.create(
            wallet=wallet,
            tx_type=WalletTransaction.TxType.TOPUP,
            amount=amount,
            status=WalletTransaction.Status.PENDING,
            reference=data.get('CheckoutRequestID', ''),
            description=f"M-Pesa STK push to {phone}",
        )

    return data


def process_stk_callback(callback_data: dict):
    """
    Called by the STK callback view when M-Pesa posts back.
    Finds the pending WalletTransaction and completes or fails it.
    """
    from .models import WalletTransaction
    from .services import WalletService

    body = callback_data.get('Body', {}).get('stkCallback', {})
    result_code = body.get('ResultCode')
    checkout_id = body.get('CheckoutRequestID', '')

    tx = WalletTransaction.objects.filter(
        reference=checkout_id,
        tx_type=WalletTransaction.TxType.TOPUP,
        status=WalletTransaction.Status.PENDING,
    ).first()

    if not tx:
        logger.warning("STK callback: no matching pending tx for %s", checkout_id)
        return

    if result_code != 0:
        tx.status = WalletTransaction.Status.FAILED
        tx.description += f" | FAILED: {body.get('ResultDesc')}"
        tx.save()
        logger.warning("STK_PUSH failed: checkout=%s reason=%s", checkout_id, body.get('ResultDesc'))
        return

    # Extract metadata
    items = {
        item['Name']: item.get('Value')
        for item in body.get('CallbackMetadata', {}).get('Item', [])
    }
    mpesa_ref   = items.get('MpesaReceiptNumber', '')
    amount_paid = Decimal(str(items.get('Amount', tx.amount)))

    # Complete the top-up via service (handles balance update)
    WalletService.topup(
        wallet=tx.wallet,
        amount=amount_paid,
        mpesa_reference=mpesa_ref,
        description=f"M-Pesa top-up confirmed. Ref: {mpesa_ref}",
    )
    # Mark original pending tx as superseded
    tx.status = WalletTransaction.Status.COMPLETED
    tx.reference = mpesa_ref
    tx.save()

    logger.info("STK_PUSH completed: wallet=%s amount=%s ref=%s", tx.wallet.pk, amount_paid, mpesa_ref)


# ─────────────────────────────────────────────
# B2C — Withdrawal Payout
# ─────────────────────────────────────────────

def initiate_b2c(withdrawal_request) -> dict:
    """
    Fire an M-Pesa Business-to-Customer payout for an approved withdrawal.
    """
    token = _get_access_token()
    phone = normalize_phone(withdrawal_request.phone_number)
    amount_int = int(withdrawal_request.amount)

    result_url  = f"{settings.MPESA_CALLBACK_BASE_URL}/wallets/mpesa/b2c-result/"
    timeout_url = f"{settings.MPESA_CALLBACK_BASE_URL}/wallets/mpesa/b2c-timeout/"

    payload = {
        "InitiatorName": settings.MPESA_B2C_INITIATOR_NAME,
        "SecurityCredential": settings.MPESA_B2C_SECURITY_CREDENTIAL,
        "CommandID": "BusinessPayment",
        "Amount": amount_int,
        "PartyA": settings.MPESA_B2C_SHORTCODE,
        "PartyB": phone,
        "Remarks": f"ChamaPro withdrawal #{withdrawal_request.pk}",
        "QueueTimeOutURL": timeout_url,
        "ResultURL": result_url,
        "Occasion": f"Withdrawal-{withdrawal_request.pk}",
    }

    resp = requests.post(
        f"{DARAJA_BASE}/mpesa/b2c/v3/paymentrequest",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    data = resp.json()
    logger.info("B2C_INIT req=%s phone=%s response=%s", withdrawal_request.pk, phone, data)
    return data


def process_b2c_result(result_data: dict):
    """
    Called by the B2C result view when M-Pesa posts back.
    Marks the WithdrawalRequest as PAID or FAILED.
    """
    from .models import WithdrawalRequest, WalletTransaction

    result = result_data.get('Result', {})
    result_code = result.get('ResultCode')
    occasion    = result.get('ReferenceData', {}).get('ReferenceItem', {}).get('Value', '')

    try:
        req_id = int(occasion.replace('Withdrawal-', ''))
        req = WithdrawalRequest.objects.get(pk=req_id)
    except (ValueError, WithdrawalRequest.DoesNotExist):
        logger.warning("B2C result: cannot find WithdrawalRequest from occasion=%s", occasion)
        return

    if result_code == 0:
        items = {
            item['Key']: item.get('Value')
            for item in result.get('ResultParameters', {}).get('ResultParameter', [])
        }
        mpesa_ref = items.get('TransactionReceipt', '')
        req.status = WithdrawalRequest.Status.PAID
        req.mpesa_reference = mpesa_ref
        req.save()

        # Complete the pending withdrawal tx
        req.wallet.transactions.filter(
            tx_type=WalletTransaction.TxType.WITHDRAWAL,
            status=WalletTransaction.Status.PENDING,
        ).update(
            status=WalletTransaction.Status.COMPLETED,
            reference=mpesa_ref,
        )
        logger.info("B2C_PAID req=%s ref=%s", req.pk, mpesa_ref)
    else:
        from .services import WalletService
        req.status = WithdrawalRequest.Status.FAILED
        req.save()

        # Reverse the reserved amount back to wallet
        WalletService.reject_withdrawal(
            request=req,
            rejected_by=None,
            reason=f"M-Pesa B2C failed: {result.get('ResultDesc')}",
        )
        logger.warning("B2C_FAILED req=%s reason=%s", req.pk, result.get('ResultDesc'))