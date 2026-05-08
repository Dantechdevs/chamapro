from django.urls import path
from . import views

urlpatterns = [
    # Hub
    path('', views.messaging_hub, name='messaging_hub'),

    # Emails
    path('emails/', views.email_inbox, name='email_inbox'),
    path('emails/sent/', views.email_sent, name='email_sent'),
    path('emails/drafts/', views.email_drafts, name='email_drafts'),
    path('emails/compose/', views.email_compose, name='email_compose'),
    path('emails/<int:email_id>/', views.email_detail, name='email_detail'),
    path('emails/<int:email_id>/delete/', views.email_delete, name='email_delete'),

    # SMS
    path('sms/', views.sms_list, name='sms_list'),

    # Notifications
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/mark-read/', views.notifications_mark_read, name='notifications_mark_read'),
    path('notifications/unread-count/', views.notifications_unread_count, name='notifications_unread_count'),

    # Announcements
    path('announcements/', views.announcements_list, name='announcements_list'),
    path('announcements/<int:ann_id>/delete/', views.announcement_delete, name='announcement_delete'),
    path('announcements/<int:ann_id>/pin/', views.announcement_pin_toggle, name='announcement_pin_toggle'),
]
