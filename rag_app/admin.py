from django.contrib import admin
from .models import Document,ChatSession,Message,Source

admin.site.register(Document)
admin.site.register(ChatSession)
admin.site.register(Message)
admin.site.register(Source)