# wallets/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Wallet, WalletTransaction, GroupWallet, WithdrawalRequest


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display   = ['membership', 'balance_display', 'is_frozen', 'created_at']
    list_filter    = ['is_frozen']
    search_fields  = ['membership__user__first_name', 'membership__user__last_name']
    readonly_fields = ['balance', 'created_at', 'updated_at']
    actions        = ['freeze_wallets', 'unfreeze_wallets', 'recalculate_balances']

    def balance_display(self, obj):
        color = '#ef4444' if obj.balance < 0 else '#0d6e4f'
        return format_html('<span style="color:{};font-weight:700;">KES {:,.2f}</span>', color, obj.balance)
    balance_display.short_description = 'Balance'

    @admin.action(description='Freeze selected wallets')
    def freeze_wallets(self, request, qs):
        qs.update(is_frozen=True)

    @admin.action(description='Unfreeze selected wallets')
    def unfreeze_wallets(self, request, qs):
        qs.update(is_frozen=False)

    @admin.action(description='Recalculate balances from ledger')
    def recalculate_balances(self, request, qs):
        for wallet in qs:
            wallet.recalculate_balance()
        self.message_user(request, f"Recalculated {qs.count()} wallet(s).")


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display   = ['wallet', 'tx_type', 'amount_display', 'status', 'reference', 'created_at']
    list_filter    = ['tx_type', 'status']
    search_fields  = ['reference', 'wallet__membership__user__first_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering       = ['-created_at']

    def amount_display(self, obj):
        return format_html('KES {:,.2f}', obj.amount)
    amount_display.short_description = 'Amount'


@admin.register(GroupWallet)
class GroupWalletAdmin(admin.ModelAdmin):
    list_display   = ['chama', 'balance', 'total_contributions_received', 'total_disbursed', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display   = ['wallet', 'amount', 'phone_number', 'status', 'approved_by', 'created_at']
    list_filter    = ['status']
    search_fields  = ['wallet__membership__user__first_name', 'phone_number', 'mpesa_reference']
    readonly_fields = ['created_at', 'updated_at']


# ─────────────────────────────────────────────────────────
# wallets/signals.py
# Auto-create Wallet + GroupWallet when a Membership/Chama is created
# ─────────────────────────────────────────────────────────

# (put this content in wallets/signals.py, then import in wallets/apps.py)

SIGNALS_CODE = '''
from django.db.models.signals import post_save
from django.dispatch import receiver
from chamapro.models import Membership, Chama
from .models import Wallet, GroupWallet


@receiver(post_save, sender=Membership)
def create_wallet_for_member(sender, instance, created, **kwargs):
    """Auto-create a Wallet whenever a new Membership is created."""
    if created:
        Wallet.objects.get_or_create(membership=instance)


@receiver(post_save, sender=Chama)
def create_group_wallet_for_chama(sender, instance, created, **kwargs):
    """Auto-create a GroupWallet whenever a new Chama is created."""
    if created:
        GroupWallet.objects.get_or_create(chama=instance)
'''

# ─────────────────────────────────────────────────────────
# wallets/apps.py
# ─────────────────────────────────────────────────────────

APPS_CODE = '''
from django.apps import AppConfig


class WalletsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'wallets'

    def ready(self):
        import wallets.signals  # noqa: F401
'''