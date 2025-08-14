from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, Chama, Membership, Transaction

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
