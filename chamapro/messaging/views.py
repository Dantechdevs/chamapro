from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q, Count

from chamapro.models import Chama, Membership
from .models import ChamaEmail, EmailRead, SMSMessage, Notification, Announcement


def get_chama_and_membership(request, chama_id):
    chama = get_object_or_404(Chama, id=chama_id)
    membership = get_object_or_404(Membership, chama=chama, user=request.user, active=True)
    return chama, membership


def is_admin(membership):
    return membership.role in ('admin', 'chairperson', 'treasurer', 'secretary')


# ── MESSAGING HUB ────────────────────────────────────────────────────────────

@login_required
def messaging_hub(request, chama_id):
    chama, membership = get_chama_and_membership(request, chama_id)
    can_manage = is_admin(membership)

    unread_emails = ChamaEmail.objects.filter(
        chama=chama, status='sent', recipients=request.user
    ).exclude(reads__user=request.user).count()

    recent_notifications = Notification.objects.filter(
        recipient=request.user, chama=chama
    )[:5]

    unread_notif_count = Notification.objects.filter(
        recipient=request.user, chama=chama, is_read=False
    ).count()

    pinned_announcements = Announcement.objects.filter(chama=chama, is_pinned=True)[:3]

    context = {
        'chama': chama,
        'membership': membership,
        'can_manage': can_manage,
        'unread_emails': unread_emails,
        'recent_notifications': recent_notifications,
        'unread_notif_count': unread_notif_count,
        'pinned_announcements': pinned_announcements,
    }
    return render(request, 'messaging/hub.html', context)


# ── EMAILS ───────────────────────────────────────────────────────────────────

@login_required
def email_inbox(request, chama_id):
    chama, membership = get_chama_and_membership(request, chama_id)
    can_manage = is_admin(membership)

    inbox_emails = ChamaEmail.objects.filter(
        chama=chama, status='sent', recipients=request.user
    ).order_by('-sent_at')

    # annotate read status
    for email in inbox_emails:
        email.is_read = email.reads.filter(user=request.user).exists()

    unread_count = sum(1 for e in inbox_emails if not e.is_read)

    context = {
        'chama': chama,
        'membership': membership,
        'can_manage': can_manage,
        'emails': inbox_emails,
        'unread_count': unread_count,
        'active_tab': 'inbox',
    }
    return render(request, 'messaging/emails.html', context)


@login_required
def email_sent(request, chama_id):
    chama, membership = get_chama_and_membership(request, chama_id)
    can_manage = is_admin(membership)

    if not can_manage:
        messages.error(request, "Access denied.")
        return redirect('email_inbox', chama_id=chama_id)

    sent_emails = ChamaEmail.objects.filter(
        chama=chama, sender=request.user, status='sent'
    ).annotate(read_count=Count('reads')).order_by('-sent_at')

    context = {
        'chama': chama,
        'membership': membership,
        'can_manage': can_manage,
        'emails': sent_emails,
        'active_tab': 'sent',
    }
    return render(request, 'messaging/emails.html', context)


@login_required
def email_drafts(request, chama_id):
    chama, membership = get_chama_and_membership(request, chama_id)
    can_manage = is_admin(membership)

    if not can_manage:
        messages.error(request, "Access denied.")
        return redirect('email_inbox', chama_id=chama_id)

    drafts = ChamaEmail.objects.filter(
        chama=chama, sender=request.user, status='draft'
    ).order_by('-updated_at')

    context = {
        'chama': chama,
        'membership': membership,
        'can_manage': can_manage,
        'emails': drafts,
        'active_tab': 'drafts',
    }
    return render(request, 'messaging/emails.html', context)


@login_required
def email_compose(request, chama_id):
    chama, membership = get_chama_and_membership(request, chama_id)
    can_manage = is_admin(membership)

    if not can_manage:
        messages.error(request, "Only admins can send emails.")
        return redirect('email_inbox', chama_id=chama_id)

    members = Membership.objects.filter(chama=chama, active=True).select_related('user').exclude(user=request.user)

    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('body', '').strip()
        action = request.POST.get('action', 'send')  # 'send' or 'draft'
        recipient_ids = request.POST.getlist('recipients')
        send_to_all = request.POST.get('send_to_all') == '1'

        if not subject or not body:
            messages.error(request, "Subject and body are required.")
        else:
            email = ChamaEmail.objects.create(
                chama=chama,
                sender=request.user,
                subject=subject,
                body=body,
                status='draft',
            )

            if send_to_all:
                all_members = Membership.objects.filter(chama=chama, active=True).exclude(user=request.user)
                email.recipients.set([m.user for m in all_members])
            elif recipient_ids:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                email.recipients.set(User.objects.filter(id__in=recipient_ids))

            if action == 'send':
                email.status = 'sent'
                email.sent_at = timezone.now()
                email.save()
                # create in-app notifications for recipients
                for recipient in email.recipients.all():
                    Notification.objects.create(
                        chama=chama,
                        recipient=recipient,
                        sender=request.user,
                        notification_type='announcement',
                        title=f"New email: {subject}",
                        message=body[:200],
                        link=f"/chama/{chama_id}/messaging/emails/",
                    )
                messages.success(request, f"Email sent to {email.recipients.count()} member(s).")
                return redirect('email_sent', chama_id=chama_id)
            else:
                email.save()
                messages.success(request, "Draft saved.")
                return redirect('email_drafts', chama_id=chama_id)

    context = {
        'chama': chama,
        'membership': membership,
        'can_manage': can_manage,
        'members': members,
    }
    return render(request, 'messaging/email_compose.html', context)


@login_required
def email_detail(request, chama_id, email_id):
    chama, membership = get_chama_and_membership(request, chama_id)
    email = get_object_or_404(ChamaEmail, id=email_id, chama=chama)

    # mark as read
    if email.status == 'sent' and request.user in email.recipients.all():
        EmailRead.objects.get_or_create(email=email, user=request.user)

    context = {
        'chama': chama,
        'membership': membership,
        'can_manage': is_admin(membership),
        'email': email,
    }
    return render(request, 'messaging/email_detail.html', context)


@login_required
def email_delete(request, chama_id, email_id):
    chama, membership = get_chama_and_membership(request, chama_id)
    email = get_object_or_404(ChamaEmail, id=email_id, chama=chama, sender=request.user)
    if request.method == 'POST':
        email.delete()
        messages.success(request, "Email deleted.")
    return redirect('email_inbox', chama_id=chama_id)


# ── SMS ──────────────────────────────────────────────────────────────────────

@login_required
def sms_list(request, chama_id):
    chama, membership = get_chama_and_membership(request, chama_id)
    can_manage = is_admin(membership)

    if not can_manage:
        messages.error(request, "Access denied.")
        return redirect('messaging_hub', chama_id=chama_id)

    sms_messages = SMSMessage.objects.filter(chama=chama).order_by('-created_at')
    members = Membership.objects.filter(chama=chama, active=True).select_related('user')

    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        recipient_ids = request.POST.getlist('recipients')
        send_to_all = request.POST.get('send_to_all') == '1'

        if not message_text:
            messages.error(request, "Message cannot be empty.")
        else:
            sms = SMSMessage.objects.create(
                chama=chama,
                sender=request.user,
                message=message_text,
                status='pending',
            )
            if send_to_all:
                all_members = [m.user for m in members]
                sms.recipients.set(all_members)
            elif recipient_ids:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                sms.recipients.set(User.objects.filter(id__in=recipient_ids))

            sms.recipient_count = sms.recipients.count()

            # TODO: integrate Africa's Talking / Twilio here
            # For now mark as sent
            sms.status = 'sent'
            sms.sent_at = timezone.now()
            sms.save()

            messages.success(request, f"SMS queued for {sms.recipient_count} member(s).")
            return redirect('sms_list', chama_id=chama_id)

    context = {
        'chama': chama,
        'membership': membership,
        'can_manage': can_manage,
        'sms_messages': sms_messages,
        'members': members,
    }
    return render(request, 'messaging/sms.html', context)


# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────

@login_required
def notifications_list(request, chama_id):
    chama, membership = get_chama_and_membership(request, chama_id)
    can_manage = is_admin(membership)

    notifs = Notification.objects.filter(recipient=request.user, chama=chama).order_by('-created_at')
    unread_count = notifs.filter(is_read=False).count()

    # Mark all as read on page visit
    notifs.filter(is_read=False).update(is_read=True, read_at=timezone.now())

    context = {
        'chama': chama,
        'membership': membership,
        'can_manage': can_manage,
        'notifications': notifs,
        'unread_count': unread_count,
    }
    return render(request, 'messaging/notifications.html', context)


@login_required
def notifications_mark_read(request, chama_id):
    """AJAX: mark a single notification read."""
    if request.method == 'POST':
        notif_id = request.POST.get('notif_id')
        Notification.objects.filter(id=notif_id, recipient=request.user).update(
            is_read=True, read_at=timezone.now()
        )
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False}, status=400)


@login_required
def notifications_unread_count(request, chama_id):
    """AJAX: get unread count for topbar badge."""
    count = Notification.objects.filter(
        recipient=request.user, chama_id=chama_id, is_read=False
    ).count()
    return JsonResponse({'count': count})


# ── ANNOUNCEMENTS ─────────────────────────────────────────────────────────────

@login_required
def announcements_list(request, chama_id):
    chama, membership = get_chama_and_membership(request, chama_id)
    can_manage = is_admin(membership)

    announcements = Announcement.objects.filter(chama=chama).order_by('-is_pinned', '-created_at')
    members = Membership.objects.filter(chama=chama, active=True).select_related('user')

    if request.method == 'POST' and can_manage:
        title = request.POST.get('title', '').strip()
        body = request.POST.get('body', '').strip()
        priority = request.POST.get('priority', 'normal')
        is_pinned = request.POST.get('is_pinned') == '1'
        notify_sms = request.POST.get('notify_via_sms') == '1'
        notify_email = request.POST.get('notify_via_email') == '1'

        if not title or not body:
            messages.error(request, "Title and body are required.")
        else:
            announcement = Announcement.objects.create(
                chama=chama,
                author=request.user,
                title=title,
                body=body,
                priority=priority,
                is_pinned=is_pinned,
                notify_via_sms=notify_sms,
                notify_via_email=notify_email,
                published_at=timezone.now(),
            )

            # notify all members in-app
            for m in members.exclude(user=request.user):
                Notification.objects.create(
                    chama=chama,
                    recipient=m.user,
                    sender=request.user,
                    notification_type='announcement',
                    title=title,
                    message=body[:200],
                    link=f"/chama/{chama_id}/messaging/announcements/",
                )

            # TODO: if notify_sms: send SMS via gateway
            # TODO: if notify_email: send emails

            messages.success(request, "Announcement published successfully.")
            return redirect('announcements_list', chama_id=chama_id)

    context = {
        'chama': chama,
        'membership': membership,
        'can_manage': can_manage,
        'announcements': announcements,
        'members': members,
        'priority_choices': Announcement.PRIORITY_CHOICES,
    }
    return render(request, 'messaging/announcements.html', context)


@login_required
def announcement_delete(request, chama_id, ann_id):
    chama, membership = get_chama_and_membership(request, chama_id)
    if not is_admin(membership):
        messages.error(request, "Access denied.")
        return redirect('announcements_list', chama_id=chama_id)

    ann = get_object_or_404(Announcement, id=ann_id, chama=chama)
    if request.method == 'POST':
        ann.delete()
        messages.success(request, "Announcement deleted.")
    return redirect('announcements_list', chama_id=chama_id)


@login_required
def announcement_pin_toggle(request, chama_id, ann_id):
    chama, membership = get_chama_and_membership(request, chama_id)
    if not is_admin(membership):
        return JsonResponse({'ok': False}, status=403)

    ann = get_object_or_404(Announcement, id=ann_id, chama=chama)
    ann.is_pinned = not ann.is_pinned
    ann.save()
    return JsonResponse({'ok': True, 'is_pinned': ann.is_pinned})
