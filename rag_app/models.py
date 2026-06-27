from django.db import models
from django.contrib.auth.models import User
import uuid


class Document(models.Model):
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),
    ]

    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    name        = models.CharField(max_length=255)
    file_type   = models.CharField(max_length=10)
    size        = models.IntegerField(default=0)
    chunk_count = models.IntegerField(default=0)
    summary     = models.TextField(blank=True, default='')
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ChatSession(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    session_id  = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    title       = models.CharField(max_length=255, default='New Chat')
    created_at  = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Message(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    session    = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role       = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"


class Source(models.Model):
    message     = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='sources')
    document    = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True)
    page_number = models.IntegerField(default=0)
    snippet     = models.TextField()

    def __str__(self):
        return f"Source for message {self.message.id}"