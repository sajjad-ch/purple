from django.db import models
from django.conf import settings
from django_jalali.db import models as jmodels


# Create your models here.

class Conversation(models.Model):
    initiator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="convo_starter"
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="convo_participant"
    )
    start_time = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                              null=True, related_name='message_sender')
    text = models.CharField(max_length=200, blank=True)
    attachment = models.FileField(blank=True)
    conversation_id = models.ForeignKey(Conversation, on_delete=models.CASCADE, null=True, blank=True)
    timestamp = jmodels.jDateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-timestamp',)


class RequestVisitNotification(models.Model):
    message = models.CharField(max_length=128, verbose_name='متن اعلان')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='فرستنده اعلان', related_name='sent_notifications', null=True)
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='گیرنده اعلان', related_name='received_notifications', blank=True)
    timestamp = jmodels.jDateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False, verbose_name='دیده شده')
    # TODO: Do not forget the migration
    
    def __str__(self):
        return f'{self.sender} {self.message} {self.receiver}'
    