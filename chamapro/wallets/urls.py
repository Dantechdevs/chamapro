"""
wallets/urls.py  — include this in your main urls.py:

    path('wallets/', include('wallets.urls')),
"""
from django.urls import path
from . import views

urlpatterns = [
    # ── Member wallet dashboard ──────────────────────────────
    path('<int:chama_id>/',               views.wallet_dashboard,     name='wallet_dashboard'),
    path('<int:chama_id>/transfer/',      views.peer_transfer,        name='wallet_transfer'),

    # ── Deposits (member) ────────────────────────────────────
    path('<int:chama_id>/deposits/',                views.deposit_page,          name='deposit_page'),
    path('<int:chama_id>/deposits/topup/',          views.initiate_topup,        name='wallet_topup'),
    path('<int:chama_id>/deposits/manual/',         views.submit_manual_deposit, name='submit_manual_deposit'),

    # ── Deposits (admin queue) ───────────────────────────────
    path('<int:chama_id>/admin/deposits/',                            views.admin_deposits,  name='admin_deposits'),
    path('<int:chama_id>/admin/deposits/<int:deposit_id>/confirm/',   views.confirm_deposit, name='confirm_deposit'),
    path('<int:chama_id>/admin/deposits/<int:deposit_id>/reject/',    views.reject_deposit,  name='reject_deposit'),

    # ── Withdrawals (member) ─────────────────────────────────
    path('<int:chama_id>/withdrawals/',   views.withdrawal_page,      name='withdrawal_page'),
    path('<int:chama_id>/withdraw/',      views.request_withdrawal,   name='wallet_withdraw'),

    # ── Withdrawals (admin queue) ────────────────────────────
    path('<int:chama_id>/admin/withdrawals/',                              views.admin_withdrawals,  name='admin_withdrawals'),
    path('<int:chama_id>/admin/withdrawals/<int:req_id>/approve/',         views.approve_withdrawal, name='approve_withdrawal'),
    path('<int:chama_id>/admin/withdrawals/<int:req_id>/reject/',          views.reject_withdrawal,  name='reject_withdrawal'),

    # ── Group wallet overview (admin) ────────────────────────
    path('<int:chama_id>/group/',         views.group_wallet,         name='group_wallet'),

    # ── M-Pesa callbacks (no auth — Safaricom POSTs here) ───
    path('mpesa/stk-callback/',  views.stk_callback,  name='stk_callback'),
    path('mpesa/b2c-result/',    views.b2c_result,     name='b2c_result'),
    path('mpesa/b2c-timeout/',   views.b2c_timeout,    name='b2c_timeout'),

]
