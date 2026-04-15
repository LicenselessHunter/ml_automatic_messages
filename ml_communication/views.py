import json
from django.views.decorators.csrf import csrf_exempt
from django_q.tasks import async_task

#Cross-Site Request Forgery (CSRF) is an attack that forces an end user to execute unwanted actions on a web application in which they’re currently authenticated. With a little help of social engineering (such as sending a link via email or chat), an attacker may trick the users of a web application into executing actions of the attacker’s choosing. If the victim is a normal user, a successful CSRF attack can force the user to perform state changing requests like transferring funds, changing their email address, and so forth. If the victim is an administrative account, CSRF can compromise the entire web application.



from django.views.decorators.http import require_POST #The decorators in django.views.decorators.http can be used to restrict access to views based on the request method. These decorators will return a django.http.HttpResponseNotAllowed if the conditions are not met. Para este caso solo usaremos de las requests de tipo POST.

from django.http import HttpResponse

# Create your views here.
@csrf_exempt 
@require_POST #Decorator to require that a view only accepts the POST method.
def ml_webhook(request):
    notification_data = json.loads(request.body)

    async_task('ml_communication.async_functions.identify_notification', notification_data, task_name=notification_data['_id'])

    return HttpResponse(status=200)

# ML no envía CSRF token. Sin @csrf_exempt, Django rechazaría todos los webhooks de ML con un 403 Forbidden porque no incluyen el token 

#A good example where @csrf_exempt is used is to build a webhook, that will receive informations from another site via a POST request. You then must be able to receive data even if it has no csrf token. *Quizás se podría agregar seguridad a esto.


