import json
import requests
from django.conf import settings
from .models import order_data_observation, message_data_observation, registered_order, ml_credentials
from django.db import transaction #module that provides a few ways to control how database transactions are managed.
#Django’s default transaction behavior:
#Django’s default behavior is to run in autocommit mode. Each query is immediately committed to the database, unless a transaction is active. Django uses transactions or savepoints automatically to guarantee the integrity of ORM operations that require multiple queries, especially delete() and update() queries.
from django_q.models import OrmQ, Failure


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
            ml_creds.access_token = data['access_token']
            ml_creds.refresh_token = data['refresh_token']
            ml_creds.expires_at = timezone.now() + timedelta(seconds=data['expires_in']) #Se toma el tiempo actual y se usa timedelta para sumarle los 21600 segundos (o 6 horas) con la fecha resultante siendo la fecha en donde va a expirar el nuevo access_token.
            ml_creds.save()

            return ml_creds.access_token


def ml_access_token()
    ml_creds = ml_credentials.objects.get()

    if ml_creds.is_expired():
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
    response = requests.get(f'https://api.mercadolibre.com/messages/packs/{order_id}/sellers/{settings.ML_SELLER_USER_ID}?limit=15', params=params, headers=headers)

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


def delete_processing_tasks(order_id, notification_id):
    processing_tasks_same_id = registered_order.objects.filter(order_id=order_id, status='processing')

    if processing_tasks_same_id.exists():
        
        for task in processing_tasks_same_id:
            Failure.objects.filter(name=notification_id).delete()
            matching_ids = [
                q.pk for q in OrmQ.objects.all() if q.name() == notification_id
            ]
            OrmQ.objects.filter(pk__in=matching_ids).delete()

        processing_tasks_same_id.delete()



def handle_order(resource, notification_id):
    '''
    order_id = resource.split('/')[-1]
    order_data_json = get_order_data(order_id)
    order_data = json.loads(order_data_json.text)

    shipping_id = order_data['shipping']['id']
    
    if shipping_id == None:
        shipping_id = "No tiene"

    order_data_observation.objects.create(order_id=order_id, shipping_id=shipping_id)

    '''

    order_id = resource.split('/')[-1]


    #---- DATA DE OBSERVACIÓN DE PRUEBA ----
    order_data_json = get_order_data(order_id)
    order_data = json.loads(order_data_json.text)

    shipping_id = order_data['shipping']['id']
    
    if shipping_id == None:
        shipping_id = "No tiene"

    order_data_observation.objects.create(order_id=order_id, shipping_id=shipping_id)
    

    #---- Se eliminan tasks ya registrados en progreso ----
    delete_processing_tasks(order_id, notification_id)

    #Se crea el task en proceso para la orden actual
    current_processing_task = registered_order.objects.create(order_id=order_id, status='processing', notification_id=notification_id)
    

    #---- Se verifica si ya hay un task completado para esta orden ----
    processed_task_same_id = registered_order.objects.filter(order_id=order_id, status='processed')

    if processed_task_same_id.exists():
        print("")
        print(f"(handle_order) La orden {order_id} ya fue registrada")
        current_processing_task.delete()
        return

    

    #---- Se verifica si la orden corresponde a un acuerdo de entrega y tiene status = paid. ----
    order_data_json = get_order_data(order_id)
    order_data = json.loads(order_data_json.text)

    shipping_id = order_data['shipping']['id']
    status = order_data['status']
    
    if shipping_id is not None or status != 'paid':
        current_processing_task.delete()
        return


    #---- Verificar los mensajes de la orden de venta ----
    messages_json = get_pack_messages(order_id)
    messages_data = json.loads(messages_json.text)

    if len(messages_data['messages']) > 0:
        
        for message_data in messages_data['messages']:

            if message_data['from']['user_id'] == int(settings.ML_SELLER_USER_ID): #Si el mensaje es del vendedor.
                current_processing_task.status = 'processed'
                current_processing_task.save()
                print("")
                print(f"(handle_order) La orden {order_id} ya tiene un mensaje nuestro")
                return
    

    client_user_id = order_data['buyer']['id']
    #send_message_to_client(order_id, client_user_id, "Hola, gracias por su compra. Por favor ne esitamos su teléfono y dirección para gestionar la entrega. El envío es gratis para usted y una vez realizado le adjuntaremos su código de seguimiento.")

    print("")
    print(f"(handle_order) Se envía mensaje para la orden {order_id} --> Hola, gracias por su compra. Por favor ne esitamos su teléfono y dirección para gestionar la entrega. El envío es gratis para usted y una vez realizado le adjuntaremos su código de seguimiento.")

    current_processing_task.status = 'processed'
    current_processing_task.save()
    
    return

def handle_message(message_id, notification_id):

    message_data_json = get_message_data_by_id(message_id)
    message_data = json.loads(message_data_json.text)
    order_id = message_data['messages'][0]['message_resources'][0]['id']


    #---- DATA DE PRUEBA ----
    order_data_json = get_order_data(order_id)
    order_data = json.loads(order_data_json.text)

    shipping_id = order_data['shipping']['id']
    
    if shipping_id == None:
        shipping_id = "No tiene"

    message_data_observation.objects.create(order_id=order_id, shipping_id=shipping_id, message_id=message_id)

    #---- Verificar si el emisor del mensaje es un trabajador de Yep Chile o no
    if message_data['messages'][0]['from']['user_id'] == int(settings.ML_SELLER_USER_ID): #Si el mensaje es del vendedor.
        print("")
        print(f"(handle_message) La orden {order_id} ya tiene un mensaje nuestro")
        return

    #---- Se eliminan tasks ya registrados en progreso ----
    delete_processing_tasks(order_id, notification_id)
    
    #Se crea el task en proceso para la orden actual
    current_processing_task = registered_order.objects.create(order_id=order_id, status='processing', notification_id=notification_id)
    

    #---- Se verifica si ya hay un task completado para esta orden ----
    processed_task_same_id = registered_order.objects.filter(order_id=order_id, status='processed')

    if processed_task_same_id.exists():
        print("")
        print(f"(handle_message) La orden {order_id} ya fue registrada")
        current_processing_task.delete()
        return


    #---- Se va a revisar el tipo logístico de la orden ----
    order_data_json = get_order_data(order_id)
    order_data = json.loads(order_data_json.text)

    status = order_data['status']
    
    if status != 'paid':
        current_processing_task.delete()
        return


    #---- Verificar los mensajes de la orden de venta ----
    messages_json = get_pack_messages(order_id)
    messages_data = json.loads(messages_json.text)
        
    for message_data in messages_data['messages']:

        if message_data['from']['user_id'] == int(settings.ML_SELLER_USER_ID): #Si el mensaje es del vendedor.
            current_processing_task.status = 'processed'
            current_processing_task.save()
            print("")
            print(f"(handle_message) La orden {order_id} ya tiene un mensaje nuestro")
            return


    #---- Ver que tipo de mensaje requiere el cliente y mandarselo ----
    shipping_id = order_data['shipping']['id']

    #Si la orden es "Acuerdo de entrega"
    if shipping_id is None:
        message_text = "Hola, gracias por su compra. Por favor necesitamos su teléfono y dirección para gestionar la entrega. El envío es gratis para usted y una vez realizado le adjuntaremos su código de seguimiento."

    #Si la orden es de cualquier otro tipo logístico
    else:
        message_text = "Hola, estamos atentos a cualquier consulta. Si requiere repuestos, cambio o cualquier solución, por favor contáctenos a nuestro whatsapp disponible en la página web yeplatam para una asistencia personalizada."

    #send_message_to_client(order_id, client_user_id, message_text)
    
    print('')
    print(f"(handle_message) Se envía mensaje para la orden {order_id} --> {message_text}")

    current_processing_task.status = 'processed'
    current_processing_task.save()

def identify_notification(notification_data):
    #print(notification_data)

    if notification_data['attempts'] > 1:
        return
    
    topic = notification_data['topic']
    resource = notification_data['resource']
    notification_id = notification_data['_id']


    if topic == 'orders_v2':
        handle_order(resource, notification_id)


    elif topic == 'messages':
        handle_message(resource, notification_id)
