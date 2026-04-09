from django.contrib import admin
from django.urls import path
from . import views #Referencio al archivo views para usar sus funciones.

app_name = 'ml_communication'

urlpatterns = [
    path("", views.ml_webhook, name="ml_webhook"), #Este path va a establecer la url https://tudominio.com/ml_communication/ como 'endpoint' o 'Callback URL' para recibir automáticamente la data de las solicitudes POST de las notificaciones de la API de mercado libre. La data de estas POST requests van a ser recibidas por el view 'ml_webhook'.
]

#Esta comunicación es lo que llamamos 'webhook'. Los webhooks también se conocen como API inversas o API push porque, al usarlos, quien debe encargarse de la comunicación es el servidor (mercado libre), en vez del cliente (Esta aplicación). Es decir, el servidor le envía al cliente una solicitud POST única de HTTP cuando los datos están disponibles, en lugar de que el cliente le envíe solicitudes de HTTP hasta obtener una respuesta. A pesar de las denominaciones que se utilizan para los webhooks, no son API, sino que ambos funcionan en conjunto. Las aplicaciones deben tener una API para usar un webhook. 

