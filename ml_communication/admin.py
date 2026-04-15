from django.contrib import admin
from .models import order_data_observation, message_data_observation, registered_order, ml_credentials

# Register your models here.
admin.site.register(ml_credentials)
admin.site.register(order_data_observation)
admin.site.register(message_data_observation)
admin.site.register(registered_order)