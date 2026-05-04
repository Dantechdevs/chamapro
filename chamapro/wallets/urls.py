"""
wallets/urls.py  — include this in your main urls.py:

    path('wallets/', include('wallets.urls')),
"""
from django.urls import path
from . import views

urlpatterns = [
    # Member wallet
    path('<int:chama_id>/',                        views.wallet_dashboard,   name='wallet_dashboard'),
    path('<int:chama_id>/topup/',                  views.initiate_topup,     name='wallet_topup'),
    path('<int:chama_id>/transfer/',               views.peer_transfer,      name='wallet_transfer'),
    path('<int:chama_id>/withdraw/',               views.request_withdrawal, name='wallet_withdraw'),

    # Admin / group wallet
    path('<int:chama_id>/group/',                         views.group_wallet,      name='group_wallet'),
    path('<int:chama_id>/group/approve/<int:req_id>/',    views.approve_withdrawal, name='approve_withdrawal'),
    path('<int:chama_id>/group/reject/<int:req_id>/',     views.reject_withdrawal,  name='reject_withdrawal'),

    # M-Pesa callbacks (no auth — Safaricom POSTs here)
    path('mpesa/stk-callback/',  views.stk_callback,  name='stk_callback'),
    path('mpesa/b2c-result/',    views.b2c_result,     name='b2c_result'),
    path('mpesa/b2c-timeout/',   views.b2c_timeout,    name='b2c_timeout'),
]