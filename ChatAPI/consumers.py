import base64
import json
import secrets
from datetime import datetime
from django.utils.timezone import now

from asgiref.sync import async_to_sync, sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
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
            message = text_data_json.get("message")
            recipient_username = text_data_json.get("recipient")
            sender_id = self.scope["user_id"]  # Get the sender's user ID

            recipient = await sync_to_async(User.objects.get)(phone_number=recipient_username)

            # Add sender ID to the data before broadcasting
            text_data_json["sender"] = sender_id
            text_data_json["message"] = message


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

    # async def receive(self, text_data=None, bytes_data=None):
    #     try:
    #         text_data_json = json.loads(text_data)
    #         message = text_data_json.get("message")
    #         recipient_username = text_data_json.get("recipient")
    #         recipient = await sync_to_async(User.objects.get)(phone_number=recipient_username)
    #         # encrypted_message = encrypt_message(recipient.public_key, message)

    #         # text_data_json["message"] = encrypted_message.hex()
    #         text_data_json["message"] = message

    #         await self.channel_layer.group_send(
    #             self.room_group_name,
    #             {"type": "chat_message", **text_data_json},
    #         )
    #     except User.DoesNotExist:
    #         await self.send(
    #             text_data=json.dumps({"error": "Recipient not found"})
    #         )
    #     except Exception as e:
    #         await self.send(
    #             text_data=json.dumps({"error": "Failed to process message", "details": str(e)})
    #         )

    async def chat_message(self, event):
        try:
            sender_id = event.get("sender")  # Get sender from event
            current_user = self.scope["user_id"]
            message_text = event.get("message")
            timestamp = now().isoformat()

            # Prevent duplicate saving by only allowing the sender to save
            if current_user != sender_id:
                await self.send(
                    text_data=json.dumps({
                        "message": "Message received",
                        "sender": sender_id,
                        "text": message_text,
                        "timestamp": timestamp
                        })
                )
                return  

            encrypted_message = event["message"]
            attachment = event.get("attachment")
            recipient_username = event.get("recipient")

            receiver = await sync_to_async(User.objects.get)(phone_number=recipient_username)
            sender_user = await sync_to_async(User.objects.get)(id=int(sender_id))
            conversation = await sync_to_async(Conversation.objects.get)(id=int(self.room_name))

            if attachment:
                file_str, file_ext = attachment["data"], attachment["format"]
                file_data = ContentFile(
                    base64.b64decode(file_str), name=f"{secrets.token_hex(8)}.{file_ext}"
                )
                _message = await sync_to_async(Message.objects.create)(
                    sender=sender_user,
                    attachment=file_data,
                    text=encrypted_message,
                    conversation=conversation,
                )
            else:
                _message = await sync_to_async(Message.objects.create)(
                    sender=sender_user,
                    text=encrypted_message,
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

    # async def chat_message(self, event):
    #     try:
    #         encrypted_message = event["message"]
    #         attachment = event.get("attachment")

    #         recipient_username = event.get("recipient")
    #         receiver = await sync_to_async(User.objects.get)(phone_number=recipient_username)
    #         # decrypted_message = decrypt_message(receiver.private_key, encrypted_message)
    #         sender = self.scope["user_id"]
    #         sender_user = await sync_to_async(User.objects.get)(id=int(sender))
    #         conversation = await sync_to_async(Conversation.objects.get)(id=int(self.room_name))

    #         if attachment:
    #             file_str, file_ext = attachment["data"], attachment["format"]
    #             file_data = ContentFile(
    #                 base64.b64decode(file_str), name=f"{secrets.token_hex(8)}.{file_ext}"
    #             )
    #             _message = await sync_to_async(Message.objects.create)(
    #                 sender=sender_user,
    #                 attachment=file_data,
    #                 text=encrypted_message,
    #                 conversation_id=conversation,
    #             )
    #         else:
    #             _message = await sync_to_async(Message.objects.create)(
    #                 sender=sender_user,
    #                 text=encrypted_message,
    #                 conversation_id=conversation,
    #             )

    #         serializer = MessageSerializer(instance=_message)
    #         print(serializer.data)
    #         await self.send(
    #             text_data=json.dumps(serializer.data)
    #         )
    #     except Exception as e:
    #         await self.send(
    #             text_data=json.dumps({"error": "Failed to process received message", "details": str(e)})
    #         )