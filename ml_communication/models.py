from django.db import models
from django.utils import timezone
from datetime import timedelta
from encrypted_fields.fields import EncryptedTextField #Aquí se importan los campos para encriptar data. Tener en cuenta que estos campos van a seguir siendo visibles en la página de admin. 

# Create your models here.

class ml_credentials(models.Model):
    user_id = models.CharField(max_length=50, unique=True)
    access_token = EncryptedTextField() #access_token para usar la api de mercado libre. Expira en 6 horas, se debe renovar con el refresh_token
    refresh_token = EncryptedTextField()
    expires_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True) #auto_now --> automatically update the field to the current date and time every time the object is saved.

    def is_expired(self): #Define custom methods on a model to add custom “row-level” functionality to your objects. Cada vez que este método sea llamado va a correr para el objeto referenciado.

        #The self (Puede tener otro nombre, pero este es el que se usa tipicamente) parameter is a reference to the current instance of the class. It is used to access properties and methods that belong to the class. Without self, Python would not know which object's properties you want to access.

        #Without self, Python would not know which object's properties you want to access

        # Usamos un margen de 5 minutos para evitar que expire durante la ejecución. 
        # In Python, timedelta is a class within the datetime module used to represent a duration or the difference between two dates or times. It allows you to perform datetime arithmetic, such as adding time to a current date or calculating the gap between two specific moments. 
        return timezone.now() >= (self.expires_at - timedelta(minutes=5))
        #Ej: expires_at = 2026-04-15 01:52:47.079295 --> expires_at - timedelta(minutes=5) = 2026-04-15 01:47:47.079295 (5 minutos menos)

class registered_order(models.Model):
    order_id = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True) #auto_now_add --> automatically set the field to the current date and time when the model instance is first created.

    def __str__(self):   #Esta función va a definir como se van a ver los productos de la base de datos en la sección de admin y en el shell.
            return f"{self.order_id}"


class api_error(models.Model):
    api_status_code = models.IntegerField()
    api_response_text = models.TextField()
    api_response_url = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True) #auto_now_add --> automatically set the field to the current date and time when the model instance is first created.

    