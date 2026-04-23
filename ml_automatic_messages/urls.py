from django.contrib import admin
from django.urls import path, include
from django.conf import settings

admin_url = settings.ADMIN_URL

urlpatterns = [
    path(f'{admin_url}', admin.site.urls),
    path('ml_communication/', include('ml_communication.urls')), #Se incluye el archivo "ml_communication.urls" y con ello acceso a sus url. en la pagina.
]
