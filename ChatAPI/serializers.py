from account_module.serializers import UserSerializerChat
from .models import Conversation, Message
from rest_framework import serializers


class MessageSerializer(serializers.ModelSerializer):
    reply_to = serializers.SerializerMethodField()

    class Meta:
        model = Message
        exclude = ['conversation_id']

    def get_reply_to(self, obj: Message):
        if obj.reply_to:
            return {
                "id": obj.reply_to.id,
                "text": obj.reply_to.text,
                "sender": obj.reply_to.sender.id,
                "created_at": obj.reply_to.created_at.isoformat()
            }
        return None


class ConversationListSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    requested_user =serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['id', 'initiator', 'receiver', 'other_user', 'last_message', 'requested_user']
    
    def get_last_message(self, instance):
        message = instance.message_set.first()
        if message:
            return MessageSerializer(message).data
        return None

    def get_other_user(self, instance):
        request_user = self.context.get('request').user
        other_user = instance.receiver if instance.initiator == request_user else instance.initiator
        return {
            'roll': 'saloon' if hasattr(other_user, 'saloon') else 'artist' if hasattr(other_user, 'artist') else 'normal_user',
            'name': other_user.first_name + ' ' + other_user.last_name if other_user.first_name else other_user.username,
            'username': other_user.username,
            'phone_number': other_user.phone_number,
            'profile_picture': other_user.profile_picture.url if other_user.profile_picture else None
        }

    def get_requested_user(self, instance):
        request_user = self.context.get('request').user.id
        return request_user
        

class ConversationSerializer(serializers.ModelSerializer):
    initiator = UserSerializerChat()
    receiver = UserSerializerChat()
    message_set = MessageSerializer(many=True)
    requested_user =serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'initiator', 'receiver', 'message_set', 'other_user', 'requested_user']

    def get_other_user(self, instance):
        request_user = self.context.get('request').user
        other_user = instance.receiver if instance.initiator == request_user else instance.initiator
        return {
            'name': other_user.first_name + ' ' + other_user.last_name if other_user.first_name else other_user.username,
            'username': other_user.username,
            'phone_number': other_user.phone_number,
            'profile_picture': other_user.profile_picture.url if other_user.profile_picture else None
        }

    def get_requested_user(self, instance):
        request_user = self.context.get('request').user.id
        return request_user