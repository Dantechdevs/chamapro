from django.db import models
from django.conf import settings


class ChamaEmail(models.Model):
    STATUS_CHOICES = [('draft', 'Draft'), ('sent', 'Sent')]

    chama = models.ForeignKey('chamapro.Chama', on_delete=models.CASCADE, related_name='emails')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_emails')
    recipients = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='received_emails', blank=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} — {self.chama.name}"

    def unread_count_for(self, user):
        return not self.reads.filter(user=user).exists()


class EmailRead(models.Model):
    email = models.ForeignKey(ChamaEmail, on_delete=models.CASCADE, related_name='reads')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('email', 'user')


class SMSMessage(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed')]

    chama = models.ForeignKey('chamapro.Chama', on_delete=models.CASCADE, related_name='sms_messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_sms')
    recipients = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='received_sms', blank=True)
    message = models.TextField(max_length=1600)
    recipient_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"SMS ({self.recipient_count} recipients) — {self.chama.name}"

    @property
    def char_count(self):
        return len(self.message)

    @property
    def sms_count(self):
        return max(1, (self.char_count + 159) // 160)


class Notification(models.Model):
    TYPE_CHOICES = [
        ('contribution', 'Contribution'),
        ('loan', 'Loan'),
        ('fine', 'Fine'),
        ('announcement', 'Announcement'),
        ('member', 'Member'),
        ('system', 'System'),
    ]

    chama = models.ForeignKey('chamapro.Chama', on_delete=models.CASCADE,
                              related_name='notifications', null=True, blank=True)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name='notifications')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                               null=True, blank=True, related_name='sent_notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} → {self.recipient}"


class Announcement(models.Model):
    PRIORITY_CHOICES = [
        ('normal', 'Normal'),
        ('important', 'Important'),
        ('urgent', 'Urgent'),
    ]

    chama = models.ForeignKey('chamapro.Chama', on_delete=models.CASCADE, related_name='announcements')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=255)
    body = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    is_pinned = models.BooleanField(default=False)
    notify_via_sms = models.BooleanField(default=False)
    notify_via_email = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"{self.title} — {self.chama.name}"
