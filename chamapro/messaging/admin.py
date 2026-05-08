from django.contrib import admin
from .models import ChamaEmail, EmailRead, SMSMessage, Notification, Announcement


@admin.register(ChamaEmail)
class ChamaEmailAdmin(admin.ModelAdmin):
    list_display = ('subject', 'chama', 'sender', 'status', 'sent_at', 'created_at')
    list_filter = ('status', 'chama')
    search_fields = ('subject', 'sender__email')


@admin.register(SMSMessage)
class SMSMessageAdmin(admin.ModelAdmin):
    list_display = ('chama', 'sender', 'status', 'recipient_count', 'sent_at')
    list_filter = ('status', 'chama')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'notification_type', 'chama', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'chama')
    search_fields = ('title', 'recipient__email')


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'chama', 'author', 'priority', 'is_pinned', 'created_at')
    list_filter = ('priority', 'is_pinned', 'chama')
    search_fields = ('title',)
