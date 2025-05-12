from django.urls import re_path
import django

django.setup()
from . import consumers

websocket_urlpatterns = [
    re_path(r"wss/chat/(?P<room_name>\w+)/$", consumers.ChatConsumer.as_asgi()),
    re_path(r"wss/visit/$", consumers.VisitConsumer.as_asgi()),
]
