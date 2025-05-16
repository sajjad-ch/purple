from django.shortcuts import render, redirect, reverse
from .models import Conversation
from rest_framework.decorators import api_view
from rest_framework.response import Response
from account_module.models import User
from .serializers import ConversationListSerializer, ConversationSerializer
from django.db.models import Q
# TODO: install Redis
# Create your views here.


@api_view(['POST'])
def start_convo(request):
    data = request.data
    username = data.get('username')
    
    if not username:
        return Response({'message': 'Username is required'}, status=400)

    try:
        participant = User.objects.get(phone_number=username)
    except User.DoesNotExist:
        return Response({'message': 'You cannot chat with a non-existent user'}, status=404)

    conversation = Conversation.objects.filter(
        (Q(initiator=request.user, receiver=participant) | Q(initiator=participant, receiver=request.user))
    ).first()

    if conversation:
        return Response(ConversationSerializer(instance=conversation, context={'request': request}).data)

    conversation = Conversation.objects.create(initiator=request.user, receiver=participant)

    return Response(ConversationSerializer(instance=conversation, context={'request': request}).data)


@api_view(['GET'])
def get_conversation(request, convo_id):
    conversation = Conversation.objects.filter(id=convo_id)
    if not conversation.exists():
        return Response({'message': 'Conversation does not exist'})
    else:
        serializer = ConversationSerializer(instance=conversation[0], context={'request': request})
        return Response(serializer.data)
    

@api_view(['GET'])
def conversations(request):
    conversation_list = Conversation.objects.filter(Q(initiator=request.user) | Q(receiver=request.user)).reverse()
    serializer = ConversationListSerializer(instance=conversation_list, many=True, context={'request': request})
    return Response(serializer.data)
