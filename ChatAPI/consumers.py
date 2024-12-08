import base64
import json
import secrets
from datetime import datetime

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.core.files.base import ContentFile

from account_module.models import User
from .models import Message, Conversation
from .serializers import MessageSerializer

# encryption library
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.backends import default_backend


def encrypt_message(public_key_pem, message):
    public_key = load_pem_public_key(public_key_pem.encode(), backend=default_backend())
    ciphertext = public_key.encrypt(
        message.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return ciphertext

def decrypt_message(private_key_pem, ciphertext):
    private_key = load_pem_private_key(private_key_pem.encode(), password=None, backend=default_backend())
    plaintext = private_key.decrypt(
        bytes.fromhex(ciphertext),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return plaintext.decode()

class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"


        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name, self.channel_name
        )
        self.accept()

    
    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name, self.channel_name
        )

    def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        message = text_data_json.get("message")
        recipient_username = text_data_json.get("recipient")
        recipient = User.objects.get(username=recipient_username)
        encrypted_message = encrypt_message(recipient.public_key, message)
        text_data_json["message"] = encrypted_message.hex()

        # chat_type = {"type": "chat_message"}
        # return_dict = {**chat_type, **text_data_json}
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {"type": "chat_message", **text_data_json}
        )

    def chat_message(self, event):
        text_data_json = event.copy()
        text_data_json.pop("type")
        encrypted_message = text_data_json["message"]
        attachment = text_data_json.get("attachment")
        
        # TODO must be tested
        # receiver = self.scope["user"]
        receiver = User.objects.get(username=self.scope['user'])
        try:
            decrypted_message = decrypt_message(receiver.private_key, encrypted_message)
        except Exception as e:
            self.send(
                text_data=json.dumps({"error": "Failed to decrypt message", "details": str(e)})
            )
            return

        
        text_data_json["message"] = decrypted_message
        conversation = Conversation.objects.get(id=int(self.room_name))
        sender = self.scope['user']

        if attachment:
            file_str, file_ext = attachment["data"], attachment["format"]

            file_data = ContentFile(
                base64.b64decode(file_str), name=f"{secrets.token_hex(8)}.{file_ext}"
            )
            _message = Message.objects.create(
                sender=sender,
                attachment=file_data,
                text=decrypted_message,
                conversation_id=conversation
            )
        else:
            _message = Message.objects.create(
                sender=sender,
                text=decrypted_message,
                conversation_id=conversation
            )
        
        serializer = MessageSerializer(instance=_message)
        self.send(
            text_data=json.dumps(serializer.data)
        )
    # def chat_message(self, event):
    #     text_data_json = event.copy()
    #     text_data_json.pop("type")
    #     message, attachment = (
    #         text_data_json["message"],
    #         text_data_json.get("attachment"),
    #     )
    #     conversation = Conversation.objects.get(id=int(self.room_name))
    #     sender = self.scope['user']

    #     if attachment:
    #         file_str, file_ext = attachment["data"], attachment["format"]

    #         file_data = ContentFile(
    #             base64.b64decode(file_str), name=f"{secrets.token_hex(8)}.{file_ext}"
    #         )
    #         _message = Message.objects.create(
    #             sender=sender,
    #             attachment=file_data,
    #             text=message,
    #             conversation_id=conversation
    #         )
    #     else:
    #         _message = Message.objects.create(
    #             sender=sender,
    #             text=message,
    #             conversation_id=conversation
    #         )
    #     serializer = MessageSerializer(instance=_message)
    #     self.send(
    #         text_data=json.dumps(
    #             serializer.data
    #         )
    #     )