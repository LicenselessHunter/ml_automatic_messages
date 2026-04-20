from django.db import models
from django.utils import timezone
from datetime import timedelta

# Create your models here.

class ml_credentials(models.Model):
    user_id = models.CharField(max_length=50, unique=True)
    access_token = models.TextField(null=True, blank=True)
    refresh_token = models.TextField()
    expires_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_expired(self):
        # Usamos un margen de 5 minutos para evitar que expire durante la ejecución. 
        # In Python, timedelta is a class within the datetime module used to represent a duration or the difference between two dates or times. It allows you to perform datetime arithmetic, such as adding time to a current date or calculating the gap between two specific moments. 
        return timezone.now() >= (self.expires_at - timedelta(minutes=5))
        #Ej: expires_at = 2026-04-15 01:52:47.079295 --> expires_at - timedelta(minutes=5) = 2026-04-15 01:47:47.079295 (5 minutos menos)

class registered_order(models.Model):
    order_id = models.CharField(max_length=50, unique=True)
    seller_message_sent = models.BooleanField(default=False)
    last_notification_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):   #Esta función va a definir como se van a ver los productos de la base de datos en la sección de admin y en el shell.
            return f"{self.order_id} - MESSAGE_SENT: {self.seller_message_sent}"


class api_error(models.Model):
    api_status_code = models.IntegerField()
    api_response_text = models.TextField()
    api_response_url = models.TextField()
    created_at = models.DateTimeField(auto_now=True)