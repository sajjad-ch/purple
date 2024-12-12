"""
ASGI config for purple project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
import ChatAPI.routing
from ChatAPI.middleware import JWTAuthMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'purple.settings')

# application = get_asgi_application()

# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AllowedHostsOriginValidator(
#         JWTAuthMiddleware(URLRouter(ChatAPI.routing.websocket_urlpatterns))
#     )
# })
# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AllowedHostsOriginValidator(
#         URLRouter(ChatAPI.routing.websocket_urlpatterns)
#     ),
# })
application = ProtocolTypeRouter(
    {
        'http': get_asgi_application(),
        'websocket': 
        JWTAuthMiddleware(
            URLRouter(
                ChatAPI.routing.websocket_urlpatterns
            )
        )
    }
)