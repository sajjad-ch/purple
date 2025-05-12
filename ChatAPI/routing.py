from django.urls import re_path
import django

django.setup()
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_name>\w+)/$", consumers.ChatConsumer.as_asgi()),
    re_path(r"ws/visit/$", consumers.VisitConsumer.as_asgi()),
]
