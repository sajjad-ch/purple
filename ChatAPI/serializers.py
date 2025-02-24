from account_module.serializers import UserSerializerChat
from .models import Conversation, Message
from rest_framework import serializers


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        exclude = ['conversation_id']


class ConversationListSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['id', 'initiator', 'receiver', 'other_user', 'last_message']
    
    def get_last_message(self, instance):
        message = instance.message_set.first()
        if message:
            return MessageSerializer(message).data
        return None

    def get_other_user(self, instance):
        request_user = self.context.get('request').user
        other_user = instance.receiver if instance.initiator == request_user else instance.initiator
        return {
            'name': other_user.first_name + ' ' + other_user.last_name if other_user.first_name else other_user.username,
            'username': other_user.username,
            'profile_picture': other_user.profile_picture.url if other_user.profile_picture else None
        }


class ConversationSerializer(serializers.ModelSerializer):
    initiator = UserSerializerChat()
    receiver = UserSerializerChat()
    message_set = MessageSerializer(many=True)

    class Meta:
        model = Conversation
        fields = ['initiator', 'receiver', 'message_set']