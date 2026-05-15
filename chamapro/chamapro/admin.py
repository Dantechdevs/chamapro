from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils import timezone
from .models import User, Chama, Membership, Transaction, PartnerApplication


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('Extra', {'fields': ('phone',)}),
    )

@admin.register(Chama)
class ChamaAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'currency', 'created_at')
    search_fields = ('name',)

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('chama', 'user', 'role', 'joined_at', 'active')
    list_filter = ('role', 'active')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('chama', 'type', 'amount', 'member', 'created_at')
    list_filter = ('type',)
    search_fields = ('reference',)

@admin.register(PartnerApplication)
class PartnerApplicationAdmin(admin.ModelAdmin):
    list_display    = ('org_name', 'org_type', 'contact_name', 'contact_email', 'offering', 'submitted_at', 'reviewed')
    list_filter     = ('org_type', 'offering', 'reviewed')
    search_fields   = ('org_name', 'contact_name', 'contact_email')
    readonly_fields = ('submitted_at',)
    actions         = ['mark_reviewed']

    @admin.action(description='Mark selected applications as reviewed')
    def mark_reviewed(self, request, queryset):
        queryset.update(reviewed=True, reviewed_at=timezone.now())