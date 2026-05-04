"""
ChamaPro M-Pesa Daraja Integration
Handles STK Push (Lipa na M-Pesa), access token, and callback processing.

Setup in settings.py:
    MPESA_CONSUMER_KEY    = 'your-consumer-key'
    MPESA_CONSUMER_SECRET = 'your-consumer-secret'
    MPESA_SHORTCODE       = '174379'          # Paybill or Till number
    MPESA_PASSKEY         = 'your-passkey'
    MPESA_CALLBACK_URL    = 'https://yourdomain.com/mpesa/callback/'
    MPESA_ENV             = 'sandbox'          # 'sandbox' or 'production'
"""

import base64
import requests
import datetime
from django.conf import settings


class MpesaClient:

    def __init__(self):
        self.env          = getattr(settings, 'MPESA_ENV', 'sandbox')
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.shortcode    = settings.MPESA_SHORTCODE
        self.passkey      = settings.MPESA_PASSKEY
        self.callback_url = settings.MPESA_CALLBACK_URL

        if self.env == 'production':
            self.base_url = 'https://api.safaricom.co.ke'
        else:
            self.base_url = 'https://sandbox.safaricom.co.ke'

    # ── Access Token ──────────────────────────────────────────────────────────

    def get_access_token(self):
        """Get OAuth access token from Safaricom."""
        url = f'{self.base_url}/oauth/v1/generate?grant_type=client_credentials'
        credentials = base64.b64encode(
            f'{self.consumer_key}:{self.consumer_secret}'.encode()
        ).decode('utf-8')

        response = requests.get(
            url,
            headers={'Authorization': f'Basic {credentials}'},
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get('access_token')

    # ── Password ──────────────────────────────────────────────────────────────

    def generate_password(self):
        """Generate base64 password and timestamp."""
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        raw = f'{self.shortcode}{self.passkey}{timestamp}'
        password = base64.b64encode(raw.encode()).decode('utf-8')
        return password, timestamp

    # ── STK Push ──────────────────────────────────────────────────────────────

    def stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """
        Trigger M-Pesa STK Push to member's phone.

        Args:
            phone_number (str): Phone in format 254XXXXXXXXX
            amount (int): Amount in KES (whole number)
            account_reference (str): e.g. "CHAMA-001" or member name
            transaction_desc (str): Short description e.g. "Monthly Contribution"

        Returns:
            dict: Safaricom response with CheckoutRequestID
        """
        access_token = self.get_access_token()
        password, timestamp = self.generate_password()

        # Normalize phone number
        phone = self._normalize_phone(phone_number)

        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(amount),
            'PartyA': phone,
            'PartyB': self.shortcode,
            'PhoneNumber': phone,
            'CallBackURL': self.callback_url,
            'AccountReference': account_reference[:12],  # max 12 chars
            'TransactionDesc': transaction_desc[:13],    # max 13 chars
        }

        response = requests.post(
            f'{self.base_url}/mpesa/stkpush/v1/processrequest',
            json=payload,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            },
            timeout=30,
        )
        return response.json()

    # ── STK Query ─────────────────────────────────────────────────────────────

    def stk_query(self, checkout_request_id):
        """Check the status of an STK push request."""
        access_token = self.get_access_token()
        password, timestamp = self.generate_password()

        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'CheckoutRequestID': checkout_request_id,
        }

        response = requests.post(
            f'{self.base_url}/mpesa/stkpushquery/v1/query',
            json=payload,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            },
            timeout=30,
        )
        return response.json()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _normalize_phone(self, phone):
        """Convert any Kenyan phone format to 254XXXXXXXXX."""
        phone = str(phone).strip().replace(' ', '').replace('-', '').replace('+', '')
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('7') or phone.startswith('1'):
            phone = '254' + phone
        return phone


# Singleton for easy import
mpesa = MpesaClient()