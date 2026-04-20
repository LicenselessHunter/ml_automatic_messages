from django.contrib import admin
from .models import registered_order, ml_credentials, api_error

# Register your models here.
admin.site.register(ml_credentials)
admin.site.register(registered_order)
admin.site.register(api_error)