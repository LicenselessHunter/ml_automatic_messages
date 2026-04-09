from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ml_communication/', include('ml_communication.urls')), #Se incluye el archivo "ml_communication.urls" y con ello acceso a sus url. en la pagina.
]
