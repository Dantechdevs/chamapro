from django.contrib import admin
from .models import Investment, InvestmentUnit, InvestmentReturn, ReturnDistribution, NAVHistory


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display  = ('name', 'chama', 'investment_type', 'capital_invested', 'current_value', 'status', 'date_invested')
    list_filter   = ('investment_type', 'status', 'chama')
    search_fields = ('name', 'institution')
    date_hierarchy = 'date_invested'


@admin.register(InvestmentUnit)
class InvestmentUnitAdmin(admin.ModelAdmin):
    list_display  = ('investment', 'member', 'units_held', 'invested_amount', 'nav_at_entry')
    list_filter   = ('investment',)


@admin.register(InvestmentReturn)
class InvestmentReturnAdmin(admin.ModelAdmin):
    list_display  = ('investment', 'return_type', 'gross_amount', 'date_received', 'flow', 'processed')
    list_filter   = ('return_type', 'flow', 'processed')
    actions       = ['mark_processed']

    @admin.action(description='Mark selected returns as processed')
    def mark_processed(self, request, queryset):
        queryset.update(processed=True)


@admin.register(ReturnDistribution)
class ReturnDistributionAdmin(admin.ModelAdmin):
    list_display  = ('investment_return', 'member', 'amount', 'share_percent', 'credited_to_wallet')
    list_filter   = ('credited_to_wallet',)


@admin.register(NAVHistory)
class NAVHistoryAdmin(admin.ModelAdmin):
    list_display  = ('investment', 'date', 'nav_per_unit', 'total_value', 'total_units')
    list_filter   = ('investment',)
    date_hierarchy = 'date'
