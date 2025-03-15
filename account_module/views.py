from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import SignUpSerializer, KeySerializer, ProfileSerializer, FollowSerializer, \
    CustomTokenObtainPairSerializer, ProfileUpdateSerializer, SaloonProfileSerializer, ArtistProfileSerializer, UserSerializerChat
from .utils import send_verification_code
from .models import User, NormalUserFollow, SaloonFollow, ArtistFollow, SaloonModel, ArtistModel, NormalUserModel
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import api_view
import json, os
from dotenv import load_dotenv
load_dotenv()

class HomeAPIView(APIView):
    def get(self, request):
        return Response({"message": "Home Page"})


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class GetPublickKeyForUser(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user_id = request.user.id
        user = User.objects.filter(id=user_id).first()
        if user:
            public_key = request.data.get('public_key')
            user.public_key = public_key
            user.save()
            return Response({'message': os.getenv('SERVER_PUBLIC_KEY')}, status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'There is no such user.'}, status=status.HTTP_400_BAD_REQUEST) 


class SignUpAPIView(APIView):
    permission_classes = [AllowAny]
    User = get_user_model()

    def get(self, request):
        serializer = SignUpSerializer()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            user, created = User.objects.get_or_create(phone_number=phone_number)
            if user:
                user.generate_verification_code()
                if created:
                    user.is_active = False
                user.save()
                sms_state = send_verification_code(phone_number, user.key)
                if sms_state:
                    redirect = 'http://127.0.0.1:8000/account/verify/'
                    return Response({'message': 'verify code sent'}, status=status.HTTP_200_OK,
                                    headers={'location': redirect})
                else:
                    return Response({'message': 'verify code didn\'t send'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyKeyView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        serializer = KeySerializer()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = KeySerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            key = serializer.validated_data['key']
            user = get_object_or_404(User, phone_number=phone_number)

            if user.key == key and user.code_generated_at and (
                    timezone.now() - user.code_generated_at).total_seconds() < 120:
                user.last_login = timezone.now()
                user.save()
                refresh = RefreshToken.for_user(user)
                return Response({'is_active': user.is_active,
                                 'success': 'Phone number verified',
                                 'access': str(refresh.access_token),
                                 'refresh': str(refresh)}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'The verification code does not match or has expired'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user = request.user
        if user.is_authenticated:
            serializer = ProfileSerializer(user)
            if serializer:
                return Response(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        phone_number = request.data.get('phone_number')
        user = User.objects.filter(phone_number=phone_number).first()
        serializer = ProfileUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            if user:
                normal_user, created = NormalUserModel.objects.get_or_create(normal_user=user, defaults={'interests': ''})
            else:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            user.is_active = True
            user.save()
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PublicAndPrivateKeySetter(APIView):
    def post(self, request):
        private_key = request.data['private_key']
        public_key = request.data['public_key']
        user = User.objects.filter(user=request.user).first()
        if private_key and public_key:
            user.private_key = private_key
            user.public_key = public_key
            user.save()
            return Response('Keys are set.', status=status.HTTP_201_CREATED)
        else:
            return Response('There are no keys to save.', status=status.HTTP_400_BAD_REQUEST)



class ViewSaloonProfile(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        saloon = SaloonModel.objects.filter(pk=user_id).first()
        if saloon:
            serializer = SaloonProfileSerializer(saloon, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_404_NOT_FOUND)


class ViewArtistProfile(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        artist = ArtistModel.objects.filter(pk=user_id).first()
        if artist:
            serializer = ArtistProfileSerializer(artist, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_404_NOT_FOUND)


class FollowView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        is_saloon = request.data.get('is_saloon')
        follower_user = request.user.id
        user = User.objects.filter(pk=follower_user).first()
        if str.lower(is_saloon) == 'false':
            artist = ArtistModel.objects.filter(pk=user_id).first()
            ArtistFollow.objects.get_or_create(follower=artist, followed_user=user)
            return Response({'message': 'Followed successfully.'}, status=status.HTTP_201_CREATED)
        elif str.lower(is_saloon) == 'true':
            saloon = SaloonModel.objects.filter(pk=user_id).first()
            SaloonFollow.objects.get_or_create(follower=saloon, followed_user=user)
            return Response({'message': 'Followed successfully.'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': 'Normal users can only follow artists and saloons.'},
                            status=status.HTTP_400_BAD_REQUEST)

        # elif hasattr(follower_user, 'saloon') and not hasattr(follower_user, 'artist'):
        #     if hasattr(followed_user, 'artist') and not hasattr(followed_user, 'saloon'):
        #         artist = ArtistModel.objects.filter(artist=followed_user).first()
        #         ArtistFollow.objects.get_or_create(follower=artist, followed_user=follower_user)
        #         return Response({'message': 'Followed successfully.'}, status=status.HTTP_201_CREATED)
        #     elif hasattr(followed_user, 'saloon') and not hasattr(followed_user, 'artist'):
        #         saloon = SaloonModel.objects.filter(saloon=followed_user).first()
        #         SaloonFollow.objects.get_or_create(follower=saloon, followed_user=follower_user)
        #         return Response({'message': 'Followed successfully.'}, status=status.HTTP_201_CREATED)
        #     else:
        #         return Response({'error': 'Normal users can only follow artists and saloons.'},
        #                         status=status.HTTP_400_BAD_REQUEST)

        # elif hasattr(follower_user, 'artist') and not hasattr(follower_user, 'saloon'):
        #     if hasattr(followed_user, 'artist') and not hasattr(followed_user, 'saloon'):
        #         artist = ArtistModel.objects.filter(artist=followed_user).first()
        #         ArtistFollow.objects.get_or_create(follower=artist, followed_user=follower_user)
        #         return Response({'message': 'Followed successfully.'}, status=status.HTTP_201_CREATED)
        #     elif hasattr(followed_user, 'saloon') and not hasattr(followed_user, 'artist'):
        #         saloon = SaloonModel.objects.filter(saloon=followed_user).first()
        #         SaloonFollow.objects.get_or_create(follower=saloon, followed_user=follower_user)
        #         return Response({'message': 'Followed successfully.'}, status=status.HTTP_201_CREATED)
        #     else:
        #         return Response({'error': 'Normal users can only follow artists and saloons.'},
        #                         status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, user_id):
        is_saloon = request.data.get('is_saloon')

        follower_user = request.user.id
        user = User.objects.filter(pk=follower_user).first()
        # if hasattr(followed_user, 'normal_user') and not NormalUserModel.objects.filter(normal_user=followed_user).exists():
        #     normal_user = NormalUserModel.objects.filter(normal_user=followed_user).first()
        #     follow_instance = NormalUserFollow.objects.filter(follower=normal_user,
        #                                                       followed_user=follower_user)
        #     if follow_instance.exists():
        #         follow_instance.delete()
        #         return Response({'message': 'Unfollowed successfully.'}, status=status.HTTP_200_OK)
        #     else:
        #         return Response({'error': 'Not following this user.'}, status=status.HTTP_400_BAD_REQUEST)

        if str.lower(is_saloon) == 'true':
            saloon = SaloonModel.objects.filter(pk=user_id).first()
            follow_instance = SaloonFollow.objects.filter(follower=saloon,
                                                          followed_user=user)
            if follow_instance.exists():
                follow_instance.delete()
                return Response({'message': 'Unfollowed successfully.'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Not following this user.'}, status=status.HTTP_400_BAD_REQUEST)
        if str.lower(is_saloon) == 'false':
            artist = ArtistModel.objects.filter(pk=user_id).first()
            follow_instance = ArtistFollow.objects.filter(follower=artist,
                                                          followed_user=user)
            if follow_instance.exists():
                follow_instance.delete()
                return Response({'message': 'Unfollowed successfully.'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Not following this user.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'error': 'User type not recognized.'}, status=status.HTTP_400_BAD_REQUEST)


class CheckFollowAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        is_saloon: str = request.data.get('is_saloon')
        current_user = request.user.id
        user = User.objects.filter(pk=current_user).first()
        followed = request.data.get('id')
        if is_saloon.lower() == 'true':
            saloon = SaloonModel.objects.filter(id=followed).first()
            follow_instance = SaloonFollow.objects.filter(follower=saloon, followed_user=user)
            if follow_instance.exists():
                return Response({'is_following': True}, status=status.HTTP_200_OK)
            else:
                return Response({'is_following': False}, status=status.HTTP_400_BAD_REQUEST)
        elif is_saloon.lower() == 'false':
            artist = ArtistModel.objects.filter(id=followed).first()
            follow_instance = ArtistFollow.objects.filter(follower=artist, followed_user=user)
            if follow_instance.exists():           
                return Response({'is_following': True}, status=status.HTTP_200_OK)
            else:
                return Response({'is_following': False}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def user_list(request, ):
    users = User.objects.all().order_by('username')
    serializer = UserSerializerChat(instance=users, many=True)
    return Response(serializer.data)


from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.models import AnonymousUser
from jwt import decode as jwt_decode, exceptions as jwt_exceptions

@api_view(['POST'])
def verify_authenticattion(request, token):
    if request.method == 'POST':
        try:
            # Decode the token
            validated_token = JWTAuthentication().get_validated_token(token)
            # Get the user from the token
            user = JWTAuthentication().get_user(validated_token)
            if user:
                return Response({'message': 'validate user'}, status=status.HTTP_200_OK)
        except jwt_exceptions.InvalidTokenError:
            return Response({'message': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({'message': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
