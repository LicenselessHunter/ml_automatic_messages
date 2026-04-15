from django.db import models
from django.utils import timezone
from datetime import timedelta

# Create your models here.

class ml_credentials(models.Model):
    user_id = models.CharField(max_length=50, unique=True)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    def is_expired(self):
        # Usamos un margen de 5 minutos para evitar que expire durante la ejecución. 
        # In Python, timedelta is a class within the datetime module used to represent a duration or the difference between two dates or times. It allows you to perform datetime arithmetic, such as adding time to a current date or calculating the gap between two specific moments. 
        return timezone.now() >= (self.expires_at - timedelta(minutes=5))
        #Ej: expires_at = 2026-04-15 01:52:47.079295 --> expires_at - timedelta(minutes=5) = 2026-04-15 01:47:47.079295 (5 minutos menos)



class order_data_observation(models.Model):
    order_id = models.CharField(max_length=100)
    shipping_id = models.CharField(max_length=100)
    notification_recieved_time = models.DateTimeField(default=timezone.now)

    def __str__(self):   #Esta función va a definir como se van a ver los productos de la base de datos en la sección de admin y en el shell.
        return f"{self.order_id} - Shipping id: {self.shipping_id} - {self.notification_recieved_time})"

class message_data_observation(models.Model):
    order_id = models.CharField(max_length=100)
    message_id = models.CharField(max_length=100)
    notification_recieved_time = models.DateTimeField(default=timezone.now)
    shipping_id = models.CharField(max_length=100)

    def __str__(self):   #Esta función va a definir como se van a ver los productos de la base de datos en la sección de admin y en el shell.
        return f"{self.order_id} - Shipping id: {self.shipping_id} - {self.notification_recieved_time})"

class registered_order(models.Model):
    PROCESS_STATUS = [
        ('processing', 'processing'),
        ('processed', 'processed'),
    ]

    order_id = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=PROCESS_STATUS)
    notification_id = models.CharField(max_length=100)

    def __str__(self):   #Esta función va a definir como se van a ver los productos de la base de datos en la sección de admin y en el shell.
            return f"{self.order_id} - STATUS: {self.status} - {self.notification_id})"