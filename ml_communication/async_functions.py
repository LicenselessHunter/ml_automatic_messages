import json
import requests
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.utils.dateparse import parse_datetime
from .models import registered_order, ml_credentials, api_error
from django.db import transaction #module that provides a few ways to control how database transactions are managed.
#Django’s default transaction behavior:
#Django’s default behavior is to run in autocommit mode. Each query is immediately committed to the database, unless a transaction is active. Django uses transactions or savepoints automatically to guarantee the integrity of ORM operations that require multiple queries, especially delete() and update() queries.


def ml_refresh_token(user_id):
    #---- REFRESH TOKEN ----

    #Ten en cuenta que el access token generado expirará transcurridas 6 horas desde que se solicitó. Por eso, para asegurar que puedas trabajar por un tiempo prolongado y no sea necesario solicitar constantemente al usuario que se vuelva a loguear para generar un token nuevo, te brindamos la solución de trabajar con un refresh token. Además, recuerda que el refresh_token es de uso único y recibirás uno nuevo en cada proceso de actualización del token.

    #atomic() Atomicity is the defining property of database transactions. atomic allows us to create a block of code within which the atomicity on the database is guaranteed. If the block of code is successfully completed, the changes are committed to the database. If there is an exception, the changes are rolled back. 
    #En este caso, el bloque sería todo lo que encierra 'transaction.atomic()', en lugar de hacer un autocommit a los queries de inmediato (Como lo hace django tradicionalmente), esta atomicidad va a asegurar que los cambios a la base de datos se completen si el bloque de código se completa con exito.

    with transaction.atomic():
        #Los workers bloqueados esperaran aquí hasta que el worker encargado de refrescar el refresh_token termine.

        ml_creds = ml_credentials.objects.select_for_update().get(user_id=user_id) #select_for_update: Returns a queryset that will lock rows until the end of the transaction (la transaction.atomic()), generating a SELECT ... FOR UPDATE SQL statement on supported databases. Esencialmente, cuando llegue un worker, esto va a poner un lock en las credenciales de mercado libre dentro de la tabla de base de datos 'ml_credentials', para que este worker Y SOLO ESTE WORKER pueda actualizar las credenciales de mercado libre.

        #Esto va a evitar que múltiples workers concurrentes intenten actualizar las credenciales de mercado libre y se generen errores. Los workers bloqueado van a esperar en la línea anterior hasta que el worker elegido haya terminado.

        if not ml_creds.is_expired(): #Esto es para los workers bloqueados que estaban esperando. Van a confirmar que el access_token ya fue renovado y lo van a recoger. Para ellos, la función terminara aquí.
            print('')
            print('access_token ya fue restaurado')
            print('')
            return ml_creds.access_token


        headers = {
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
        }

        payload = {
            'grant_type': 'refresh_token', #refresh_token indica que la operación deseada es actualizar un token.
            'client_id': settings.ML_CLIENT_ID, #client_id que aparece en la página de credenciales de ML.
            'client_secret': settings.ML_CLIENT_SECRET, #client_secret que aparece en la página de credenciales de ML.
            'refresh_token': ml_creds.refresh_token #El refresh token que aparecio en la última respuesta de este mismo recurso, se deberá usar para generar un nuevo tojen una vez que el actual expire.
        }

        response = requests.post('https://api.mercadolibre.com/oauth/token', headers=headers, data=payload)

        if response.status_code == 200:
            token_data = response.json()
            ml_creds.access_token = token_data['access_token']
            ml_creds.refresh_token = token_data['refresh_token']
            ml_creds.expires_at = timezone.now() + timedelta(seconds=token_data['expires_in']) #Se toma el tiempo actual y se usa timedelta para sumarle los 21600 segundos (o 6 horas) con la fecha resultante siendo la fecha en donde va a expirar el nuevo access_token.
            ml_creds.save()
            print('')
            print('access_token restaurado :)')
            print('')

            return ml_creds.access_token

        else:
            api_error.objects.create(
                api_status_code = response.status_code,
                api_response_text = response.text,
                api_response_url = response.url

            )


def ml_access_token():
    ml_creds = ml_credentials.objects.get(user_id=settings.ML_SELLER_USER_ID)

    if ml_creds.is_expired():
        print('')
        print('access_token caducado :(')
        print('')
        access_token = ml_refresh_token(ml_creds.user_id)

    else:
        access_token = ml_creds.access_token

    return access_token



def get_message_data_by_id(message_id):

    access_token = ml_access_token() #Se llama a la función para obtener y/o renovar el access_token de mercado libre

    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    params = {
        'tag': 'post_sale',
    }

    response = requests.get(f'https://api.mercadolibre.com/messages/{message_id}', params=params, headers=headers)

    return response

def get_order_data(order_id):
    #---- BUSCAR ÓRDENES ----

    #Una orden es una solicitud que realiza un cliente para una publicación con intención de comprarlo conforme a una serie de condiciones que seleccionará en el flujo del proceso de compra (checkout). Todas las condiciones de la venta se detallan en la orden, la cual se replicará para las cuentas del comprador y el vendedor.

    #Recuerda que actualmente se guardan órdenes creadas hasta 12 meses y si realizas la búsqueda como vendedor, filtras órdenes canceladas.

    access_token = ml_access_token() #Se llama a la función para obtener y/o renovar el access_token de mercado libre

    headers = {
        'Authorization': f'Bearer {access_token}',
    }


    response = requests.get(f'https://api.mercadolibre.com/orders/{order_id}', headers=headers)
    return response


def get_pack_data(order_id):
    access_token = ml_access_token() #Se llama a la función para obtener y/o renovar el access_token de mercado libre

    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    response = requests.get(f'https://api.mercadolibre.com/packs/{order_id}', headers=headers)
    return response


def get_pack_messages(order_id):
    
    access_token = ml_access_token() #Se llama a la función para obtener y/o renovar el access_token de mercado libre

    
    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    params = {
        'tag': 'post_sale',
        'mark_as_read': 'false', #Este parámetro permite que los mensaje aparezcan como no leidos.
    }

    #https://api.mercadolibre.com/messages/packs/$PACK_ID/sellers/$USER_ID?tag=post_sale.
    #En lugar del $PACK_ID se puede usar el id de la orden.
    response = requests.get(f'https://api.mercadolibre.com/messages/packs/{order_id}/sellers/{settings.ML_SELLER_USER_ID}?limit=100', params=params, headers=headers)

    return response


def send_message_to_client(order_id, client_user_id, message_text):
    
    access_token = ml_access_token() #Se llama a la función para obtener y/o renovar el access_token de mercado libre
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    params = {
        'tag': 'post_sale',
    }

    json_data = {
        'from': {
            'user_id': settings.ML_SELLER_USER_ID,
        },
        'to': {
            'user_id': client_user_id, #Este el id del user al cuál se le quiere dar el mensaje. La documentación de ML dice usar el agent_id en su lugar pero es puro chamullo.
        },
        'text': message_text,
    }

    response = requests.post(
        f'https://api.mercadolibre.com/messages/packs/{order_id}/sellers/{settings.ML_SELLER_USER_ID}', #https://api.mercadolibre.com/messages/packs/$PACK_ID/sellers/$USER_ID?tag=post_sale
        #En lugar del $PACK_ID se puede usar el id de la orden.
        params=params,
        headers=headers,
        json=json_data,
    )

    return response



def handle_order(order_id, order_data, processing_order):
    
    #Por si es una orden normal
    try:
        shipping_id = order_data['shipping']['id']

    #Por si es un pack
    except:
        shipping_id = order_data['shipment']['id']

    order_status = order_data['status']

    #---- Se verifica si la orden corresponde a un acuerdo de entrega y tiene status = paid (orden normal) o status = released (orden pack) ----
    if shipping_id is not None or (order_status != 'paid' and order_status != 'released'):
        print('')
        print(f'(handle_order) La orden {order_id} no tiene status pagado y/o no es acuerdo de entrega')
        print('')
        
        processing_order.delete()
        return


    #---- Verificar los mensajes de la orden de venta ----
    messages_response = get_pack_messages(order_id)
    
    if messages_response.status_code != 200:
        processing_order.delete()

        api_error.objects.create(
            api_status_code = messages_response.status_code,
            api_response_text = messages_response.text,
            api_response_url = messages_response.url
        )
        return

    messages_data = json.loads(messages_response.text)

    if len(messages_data['messages']) > 0:
        
        for message in messages_data['messages']:

            if message['from']['user_id'] == int(settings.ML_SELLER_USER_ID): #Si el mensaje es del vendedor.
                print("")
                print(f"(handle_order) La orden {order_id} ya tiene un mensaje nuestro")
                print("")
                return
    

    #---- Mandar mensaje al cliente ----
    client_user_id = order_data['buyer']['id']  
    send_message_to_client(order_id, client_user_id, "Hola, gracias por su compra. Por favor necesitamos su teléfono y dirección para gestionar la entrega. El envío es gratis para usted y una vez realizado le adjuntaremos su código de seguimiento.\n\nHorario de atención: lunes a viernes 09:00 AM - 17:00 PM\n\n*Este es un mensaje automático, un asociado de YEP le atenderá pronto*")   

    print("")
    print(f"(handle_order) Se envía mensaje para la orden {order_id} --> Hola, gracias por su compra. Por favor necesitamos su teléfono y dirección para gestionar la entrega. El envío es gratis para usted y una vez realizado le adjuntaremos su código de seguimiento.\n\nHorario de atención: lunes a viernes 09:00 AM - 17:00 PM\n\n*Este es un mensaje automático, un asociado de YEP le atenderá pronto*")
    print("")


def handle_message(order_id, order_data, processing_order, message_sender):

    #---- Verificar si el emisor del mensaje es un trabajador de Yep Chile o no ----
    if message_sender == int(settings.ML_SELLER_USER_ID): #Si el mensaje es del vendedor.

        print("")
        print(f"(handle_message) La orden {order_id} ya tiene un mensaje nuestro")
        print("")
        return

    #---- Verificar que la orden tenga status = paid (orden normal) o status = released (orden pack) ----
    order_status = order_data['status']

    if order_status != 'paid' and order_status != 'released':
        print("")
        print(f"(handle_message) La orden {order_id} no tiene status paid o released")
        print("")

        processing_order.delete()  
        return

    #---- Verificar los mensajes de la orden de venta ----
    messages_response = get_pack_messages(order_id)
    
    if messages_response.status_code != 200:
        api_error.objects.create(
            api_status_code = messages_response.status_code,
            api_response_text = messages_response.text,
            api_response_url = messages_response.url

        )
        return

    messages_data = json.loads(messages_response.text)

        
    for message in messages_data['messages']:

        if message['from']['user_id'] == int(settings.ML_SELLER_USER_ID): #Si el mensaje es del vendedor.
            print("")
            print(f"(handle_message) La orden {order_id} ya tiene un mensaje nuestro")
            print("")
            return


    #---- Ver que tipo de mensaje requiere el cliente y mandarselo ----
    #Por si es una orden normal
    try:
        shipping_id = order_data['shipping']['id']

    #Por si es un pack
    except:
        shipping_id = order_data['shipment']['id']

    #Si la orden es "Acuerdo de entrega"
    if shipping_id is None:
        message_text = "Hola, gracias por su compra. Por favor necesitamos su teléfono y dirección para gestionar la entrega. El envío es gratis para usted y una vez realizado le adjuntaremos su código de seguimiento.\n\nHorario de atención: lunes a viernes 09:00 AM - 17:00 PM\n\n*Este es un mensaje automático, un asociado de YEP le atenderá pronto*"

    #Si la orden es de cualquier otro tipo logístico
    else:
        message_text = "Hola, estamos atentos a cualquier consulta. Si requiere repuestos, cambio o cualquier solución, por favor contáctenos a nuestro whatsapp disponible en la página web yeplatam para una asistencia personalizada.\n\nHorario de atención: lunes a viernes 09:00 AM - 17:00 PM\n\n*Este es un mensaje automático, un asociado de YEP le atenderá pronto*"

    client_user_id = order_data['buyer']['id'] 
    send_message_to_client(order_id, client_user_id, message_text)

    print('')
    print(f"(handle_message) Se envía mensaje para la orden {order_id} --> {message_text}")
    print('')



def process_notification(notification_data):
    topic = notification_data['topic']
    resource = notification_data['resource']

    if topic == 'orders_v2':
        order_id = resource.split('/')[-1]

    elif topic == 'messages':
        message_response = get_message_data_by_id(resource)

        if message_response.status_code == 200:
            message_data = json.loads(message_response.text)
            order_id = message_data['messages'][0]['message_resources'][0]['id']
            message_sender = message_data['messages'][0]['from']['user_id']

        else:
            api_error.objects.create(
                api_status_code = message_response.status_code,
                api_response_text = message_response.text,
                api_response_url = message_response.url

            )
            return


    #atomic() Atomicity is the defining property of database transactions. atomic allows us to create a block of code within which the atomicity on the database is guaranteed. If the block of code is successfully completed, the changes are committed to the database. If there is an exception, the changes are rolled back. 
    #En este caso, el bloque sería todo lo que encierra 'transaction.atomic()', en lugar de hacer un autocommit a los queries de inmediato (Como lo hace django tradicionalmente), esta atomicidad va a asegurar que los cambios a la base de datos se completen si el bloque de código se completa con exito.

    with transaction.atomic():
        #Los workers bloqueados esperaran aquí hasta que el worker termine de procesar la orden.
        
        #get_or_create() --> A convenience method for looking up an object with the given kwargs (may be empty if your model has defaults for all fields), creating one if necessary. Returns a tuple of (object, created), where object is the retrieved or created object and created is a boolean specifying whether a new object was created.
        processing_order, new_order = registered_order.objects.select_for_update().get_or_create(
            order_id=order_id
        )

        if not new_order:

            print("")
            print(f"La orden {order_id} ya está registrada, por lo que ya tiene un mensaje nuestro")
            print("")

            return


        #---- Determinar si el order_id corresponde a un 'pack' o a una orden normal----
        order_response = get_order_data(order_id)    
    
        if order_response.status_code == 200:
            order_data = json.loads(order_response.text)
            

        elif order_response.status_code == 404:
            pack_response = get_pack_data(order_id)

            if pack_response.status_code != 200:
                processing_order.delete()
                api_error.objects.create(
                    api_status_code = pack_response.status_code,
                    api_response_text = pack_response.text,
                    api_response_url = pack_response.url

                )   
                return
                
            print('')
            print('Procesando pack')
            print('')
            order_data = json.loads(pack_response.text)

        else:
            processing_order.delete()
            api_error.objects.create(
                api_status_code = order_response.status_code,
                api_response_text = order_response.text,
                api_response_url = order_response.url

            )
            return        
        
        
        if topic == 'orders_v2':
            handle_order(order_id, order_data, processing_order)


        elif topic == 'messages':
            handle_message(order_id, order_data, processing_order, message_sender)
        