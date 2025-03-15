import base64
import json, os
import secrets
from datetime import datetime
from django.utils.timezone import now
from jdatetime import datetime as jdatetime 

from asgiref.sync import async_to_sync, sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.generic.websocket import WebsocketConsumer
from django.core.files.base import ContentFile

from account_module.models import User
from .models import Message, Conversation
from .serializers import MessageSerializer

from decouple import config
from cryptography.hazmat.primitives import serialization

# Load keys from .env
SERVER_PUBLIC_KEY = config("SERVER_PUBLIC_KEY").replace("\\n", "\n")
SERVER_PRIVATE_KEY = config("SERVER_PRIVATE_KEY").replace("\\n", "\n")

# Deserialize keys
server_public_key = serialization.load_pem_public_key(SERVER_PUBLIC_KEY.encode())
server_private_key = serialization.load_pem_private_key(
    SERVER_PRIVATE_KEY.encode(),
    password=None,
)

import base64

def is_base64(s):
    try:
        base64.b64decode(s)
        return True
    except Exception:
        return False

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

def decrypt_message(encrypted_message, private_key):
    """
    Decrypt a message using the provided private key.

    Args:
        encrypted_message (str): The base64-encoded encrypted message.
        private_key (Union[str, RSAPrivateKey]): The private key as a PEM-encoded string or RSAPrivateKey object.

    Returns:
        str: The decrypted message.
    """
    # If private_key is a PEM-encoded string, deserialize it
    if isinstance(private_key, str):
        private_key = serialization.load_pem_private_key(
            private_key.encode(),  # Convert the PEM string to bytes
            password=None,
        )

    # Decrypt the message
    decrypted_message = private_key.decrypt(
        base64.b64decode(encrypted_message),  # Decode the base64-encoded message
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return decrypted_message.decode('utf-8') 


# def encrypt_message(message, public_key_pem):
#     public_key = serialization.load_pem_public_key(public_key_pem)
#     encrypted_message = public_key.encrypt(
#         message.encode('utf-8'),
#         padding.OAEP(
#             mgf=padding.MGF1(algorithm=hashes.SHA256()),
#             algorithm=hashes.SHA256(),
#             label=None
#         )
#     )
#     return base64.b64encode(encrypted_message).decode('utf-8')
def encrypt_message(message, public_key):
    if isinstance(message, str):
        message = message.encode('utf-8')
    encrypted_message = public_key.encrypt(
        message,  # Ensure this is bytes
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return base64.b64encode(encrypted_message).decode('utf-8')

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"
        # user_id = self.scope['user_id']
        # await self.update_user_status(user_id, 'online')
        await self.channel_layer.group_add(
                self.room_group_name, self.channel_name
            )
        await self.accept()


    async def disconnect(self, close_code):
        # user = self.scope['user_id']
        # await self.update_user_status(user, 'offline')
        await self.channel_layer.group_discard(
            self.room_group_name, self.channel_name
        )

    @database_sync_to_async
    def update_user_status(self, user_id, status):
        user = User.objects.filter(id=user_id).first()
        user.status = status
        user.save()


    async def receive(self, text_data=None, bytes_data=None):
        try:
            text_data_json = json.loads(text_data)
            encrypted_message  = text_data_json.get("message")
            # print('103: Encrypted message received:', encrypted_message)
            # if not is_base64(encrypted_message):
            #     await self.send(text_data=json.dumps({"error": "Invalid message format: expected base64-encoded string"}))
            #     return
            recipient_username = text_data_json.get("recipient")
            sender_id = self.scope["user_id"]  # Get the sender's user ID
            # print('Type of server_private_key:', type(server_private_key))
            # decrypted_message = decrypt_message(encrypted_message, server_private_key)
            # print('106: Decrypted message:', decrypted_message)
            recipient = await sync_to_async(User.objects.get)(phone_number=recipient_username)
            # recipient_public_key_pem = recipient.public_key
            # if not recipient_public_key_pem:
            #     await self.send(text_data=json.dumps({"error": "Recipient's public key not found"}))
            #     return
            # from cryptography.hazmat.primitives import serialization
            # recipient_public_key = serialization.load_pem_public_key(recipient_public_key_pem.encode())
            # print('114: Recipient public key loaded:', recipient_public_key)
            # re_encrypted_message = encrypt_message(decrypted_message, recipient_public_key)
            # print('116: Re-encrypted message:', re_encrypted_message)

            # Add sender ID to the data before broadcasting
            text_data_json["sender"] = sender_id
            text_data_json["message"] = encrypted_message     # when uncommenting it should be re_encrypted_message


            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "chat_message", **text_data_json},
            )
        except User.DoesNotExist:
            await self.send(
                text_data=json.dumps({"error": "Recipient not found"})
            )
        except Exception as e:
            await self.send(
                text_data=json.dumps({"error": "Failed to process message", "details": str(e)})
            )


    async def chat_message(self, event):
        try:
            sender_id = event.get("sender")  # Get sender from event
            current_user = self.scope["user_id"]
            message = event.get("message")
            recipient_username = event.get("recipient")
            timestamp = now().isoformat()
            receiver = await sync_to_async(User.objects.get)(phone_number=recipient_username)
            sender_user = await sync_to_async(User.objects.get)(id=int(sender_id))
            conversation = await sync_to_async(Conversation.objects.get)(id=int(self.room_name))
            encrypted_message = event["message"]
            attachment = event.get("attachment")

            # Prevent duplicate saving by only allowing the sender to save
            if current_user != sender_id:
                await self.send(
                    text_data=json.dumps({
                        "message": "Message received",
                        "sender": sender_id,
                        "text": message,
                        "timestamp": jdatetime.fromgregorian(datetime=now()).strftime("%Y-%m-%d %H:%M:%S")
                        })
                )
                return  

            if attachment:
                file_str, file_ext = attachment["data"], attachment["format"]
                file_data = ContentFile(
                    base64.b64decode(file_str), name=f"{secrets.token_hex(8)}.{file_ext}"
                )
                _message = await sync_to_async(Message.objects.create)(
                    sender=sender_user,
                    attachment=file_data,
                    text=message,
                    conversation=conversation,
                )
            else:
                _message = await sync_to_async(Message.objects.create)(
                    sender=sender_user,
                    text=message,
                    conversation_id=conversation,
                )

            serializer = MessageSerializer(instance=_message)
            await self.send(
                text_data=json.dumps(serializer.data)
            )
        except Exception as e:
            await self.send(
                text_data=json.dumps({"error": "Failed to process received message", "details": str(e)})
            )
