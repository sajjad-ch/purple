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
from .models import Message, Conversation, RequestVisitNotification
from .serializers import MessageSerializer

from decouple import config
from cryptography.hazmat.primitives import serialization

# Load keys from .env
# SERVER_PUBLIC_KEY = config("SERVER_PUBLIC_KEY").replace("\\n", "\n")
# SERVER_PRIVATE_KEY = config("SERVER_PRIVATE_KEY").replace("\\n", "\n")

# # Deserialize keys
# server_public_key = serialization.load_pem_public_key(SERVER_PUBLIC_KEY.encode())
# server_private_key = serialization.load_pem_private_key(
#     SERVER_PRIVATE_KEY.encode(),
#     password=None,
# )

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
        user_id = self.scope['user_id']
        user = await sync_to_async(User.objects.get)(pk=user_id)
        self.user = user
        # await self.update_user_status(user_id, 'online')
        await self.channel_layer.group_add(
                self.room_group_name, self.channel_name
            )
        await self.accept()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_notification",
                "message": f"{self.user.username} is online",
                "user_id": self.user.id
            }
        )


    async def disconnect(self, close_code):
        # user = self.scope['user_id']
        # await self.update_user_status(user, 'offline')
        await self.channel_layer.group_discard(
            self.room_group_name, self.channel_name
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_notification",
                "message": f"{self.user.username} is offline",
                "user_id": self.user.id,
            },
        )

    @database_sync_to_async
    def update_user_status(self, user_id, status):
        user = User.objects.filter(id=user_id).first()
        user.status = status
        user.save()


    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data)
            message_type = data.get("type")
            if message_type == "send_message":
                sender_id = self.scope["user_id"]
                data["sender"] = sender_id
                encrypted_message  = data.get("message")
                # if not is_base64(encrypted_message):
                #     await self.send(text_data=json.dumps({"error": "Invalid message format: expected base64-encoded string"}))
                #     return
                recipient_username = data.get("recipient")
                # decrypted_message = decrypt_message(encrypted_message, server_private_key)
                recipient = await sync_to_async(User.objects.get)(phone_number=recipient_username)
                # recipient_public_key_pem = recipient.public_key
                # if not recipient_public_key_pem:
                #     await self.send(text_data=json.dumps({"error": "Recipient's public key not found"}))
                #     return
                # from cryptography.hazmat.primitives import serialization
                # recipient_public_key = serialization.load_pem_public_key(recipient_public_key_pem.encode())
                # re_encrypted_message = encrypt_message(decrypted_message, recipient_public_key)

                # Add sender ID to the data before broadcasting
                data["message"] = encrypted_message     # when uncommenting it should be re_encrypted_message
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "send_message",
                        **data
                    },
                )
                

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_notification",
                        "message": f"New message from {recipient.first_name}",
                        "sender_id": sender_id,
                    },
                )
                       
            elif message_type == "edit_message":
                message_id = data.get("message_id")
                new_text = data.get("new_text")

                message = await sync_to_async (Message.objects.get)(id=message_id)
                message.text = new_text
                message.is_edited = True
                await sync_to_async (message.save)()

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "message_edited",
                        "message_id": message_id,
                        "new_text": new_text,
                    }
                )

            elif message_type == "delete_message":
                message_id = data.get("message_id")
                await sync_to_async(Message.objects.filter(id=message_id).delete)()
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "message_deleted",
                        "message_id": message_id,
                    }
                )
            
            elif message_type == "delete_chat":
                chat_id = data.get("chat_id")
                await sync_to_async(Conversation.objects.filter(id=chat_id).delete)()
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_deleted",
                        "chat_id": chat_id,
                    }
                )
            
            else:
                await self.send(text_data=json.dumps({"error": "Invalid message type"}))
        
        except Exception as e:
            await self.send(text_data=json.dumps({"error": "Invalid message structure", "details": str(e)}))

        except User.DoesNotExist:
            await self.send(
                text_data=json.dumps({"error": "Recipient not found"})
            )
        except Exception as e:
            await self.send(
                text_data=json.dumps({"error": "Failed to process message", "details": str(e)})
            )


    async def send_message(self, event):
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
            reply_to_id = event.get("reply_to")
            reply_to_message = None

            if reply_to_id:
                try:
                    reply_to_message = await sync_to_async(Message.objects.get)(id=reply_to_id)
                except Message.DoesNotExist:
                    reply_to_message = None
            
            if attachment:
                file_str, file_ext = attachment["data"], attachment["format"]
                file_data = ContentFile(
                base64.b64decode(file_str), name=f"{secrets.token_hex(8)}.{file_ext}"
                )

            # Prevent duplicate saving by only allowing the sender to save
            if current_user != sender_id:
                await self.send(
                    text_data=json.dumps({
                        "message": "Message received",
                        "sender": sender_id,
                        "text": message,
                        "timestamp": jdatetime.fromgregorian(datetime=now()).strftime("%Y-%m-%d %H:%M:%S"),
                        "reply_to": reply_to_message,
                        "attachment": file_data if file_data else None
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
                    conversation_id=conversation,
                    reply_to=reply_to_message
                )
            else:
                _message = await sync_to_async(Message.objects.create)(
                    sender=sender_user,
                    text=message,
                    conversation_id=conversation,
                    reply_to=reply_to_message
                )

            serializer = MessageSerializer(instance=_message)
            await self.send(
                text_data=json.dumps(serializer.data)
            )
        except Exception as e:
            await self.send(
                text_data=json.dumps({"error": "Failed to process received message", "details": str(e)})
            )

    
    async def message_edited(self, event):
        await self.send(text_data=json.dumps({
            "type": "edit",
            "message_id": event["message_id"],
            "new_text": event["new_text"]
        }))


    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            "type": "delete_message",
            "message_id": event["message_id"]
        }))

    async def chat_deleted(self, event):
        await self.send(text_data=json.dumps({
            "type": "delete_chat",
            "chat_id": event["chat_id"]
        }))

    async def chat_notification(self, event):
        await self.send(text_data=json.dumps({"type": "notification", "message":event["message"]}))



class VisitConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user_id = self.scope["user_id"]
        user = await sync_to_async(User.objects.get)(pk=user_id)
        self.user = user
        self.group_name = f"user_{self.user.id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        pending_notifications = await sync_to_async(
            lambda: list(
                RequestVisitNotification.objects.filter(receiver=user, seen=False).order_by('-timestamp')
            )
        )()

        for notification in pending_notifications:
            await self.send(text_data=json.dumps({
                "type": "pending_notification",
                "notification_id": notification.id,
                "message": notification.message,
                "sender_id": notification.sender.id,
                "timestamp": str(notification.timestamp),
            }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data)
            customer_id = data.get("customer_id")
            status = data.get("status")

            customer = await sync_to_async(User.objects.get)(id=customer_id)
            if status == '':
                await sync_to_async(RequestVisitNotification.objects.create)(
                    message=f"",
                    sender=self.user,
                    receiver=customer,
                )
            #TODO: add other status
            customer_group = f"user_{customer_id}"

            await self.channel_layer.group_send(
                customer_group,
                {
                    "type": "visit_notification",
                    "message": f"Your visit status has changed: {status}",
                    "customer_id": customer_id,
                },
            )
        except User.DoesNotExist:
            await self.send(text_data=json.dumps({"error": "Customer not found"}))
        except Exception as e:
            await self.send(text_data=json.dumps({"error": "Failed to process visit update", "details": str(e)}))

    async def visit_notification(self, event):
        await self.send(text_data=json.dumps({"type": "notification", "message": event["message"]}))

    async def mark_notification_seen(self, notification_id):
        try:
            notification = await sync_to_async(RequestVisitNotification.objects.get)(id=notification_id, receiver=self.user)
            notification.seen = True
            await sync_to_async(notification.save)()
            await self.send(text_data=json.dumps({"type": "seen_update", "notification_id": notification_id, "status": "success"}))
        except RequestVisitNotification.DoesNotExist:
            await self.send(text_data=json.dumps({"type": "seen_update", "notification_id": notification_id, "status": "not_found"}))
