import logging

logger = logging.getLogger(__name__)

import tempfile
import os, json
from itertools import groupby
from operator import itemgetter
from django.shortcuts import get_object_or_404
from django.utils.timezone import now, timedelta
from django.db.models import Sum, Q
from account_module.serializers import SaloonProfileSerializer, ArtistProfileSerializer
from account_module.utils import send_verification_code
from .serializers import *
from .models import PostModel, LikeModel, VisitingTimeModel, WalletModel, \
    DiscountModel, StoryModel, SliderModel, UserServicesModel, ServiceModel, SupServiceModel
from account_module.models import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from moviepy.editor import VideoFileClip
from PIL import Image
from django.utils import timezone
from rest_framework.pagination import LimitOffsetPagination
import jdatetime
from datetime import timedelta
from .utils import *
# Create your views here.



class SliderView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sliders = SliderModel.objects.filter(is_active=True).all()
        if sliders:
            serializer = SliderSeralizer(sliders, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({'error': 'There is no active slider.'}, status=status.HTTP_404_NOT_FOUND)


class ServicesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        services = ServiceModel.objects.all()
        if services:
            serializer = ServiceSerializer(services, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({'error': 'There is no services.'}, status=status.HTTP_404_NOT_FOUND)


class ServiceFilterArtistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, service_code):
        services = UserServicesModel.objects.filter(supservice__service__service_code=service_code, artist__isnull=False)
        if not services.exists():
            return Response({'error': 'No artists found with this service.'}, status=status.HTTP_404_NOT_FOUND)
        artists = ArtistModel.objects.filter(pk__in=services.values_list('artist__pk', flat=True)).distinct()
        serializer = ArtistVisitsSerializer(artists, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ServiceFilterSaloonView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, service_code):
        services = UserServicesModel.objects.filter(service__service_code=service_code, artist__isnull=True,
                                                    saloon__isnull=False)
        if not services.exists():
            return Response({'error': 'No artists found with this service.'}, status=status.HTTP_404_NOT_FOUND)
        saloons = SaloonModel.objects.filter(pk__in=services.values_list('saloon__pk', flat=True))
        serializer = SaloonVisitsSerializer(saloons, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class BestUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        all_saloons = SaloonModel.objects.all()
        all_artists = ArtistModel.objects.all()

        saloon_serializer = SaloonProfileSerializer(all_saloons, many=True, context={'request': request})
        artist_serializer = ArtistProfileSerializer(all_artists, many=True, context={'request': request})

        saloon_data = saloon_serializer.data
        artist_data = artist_serializer.data

        combined_data: dict = list(saloon_data) + list(artist_data)

        sorted_data = sorted(
            combined_data,
            key=lambda x: (
                x.get('average_ranks', {}).get('total_average', 0)
                if isinstance(x.get('average_ranks'), dict)
                else 0
            ),
            reverse=True
        )

        return Response(sorted_data, status=status.HTTP_200_OK)


class ManagingFinancialView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if hasattr(user, 'artist'):
            visits = VisitingTimeModel.objects.filter(artist=user.artist.pk)
        elif hasattr(user, 'saloon'):
            visits = VisitingTimeModel.objects.filter(saloon=user.saloon.pk)
        else:
            return Response({"detail": "User does not have a valid artist or saloon profile."}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate income
        daily_income = self.calculate_income(visits, days=1)
        weekly_income = self.calculate_income(visits, days=7)
        monthly_income = self.calculate_income(visits, days=30)

        data = {
            "daily_income": daily_income,
            "weekly_income": weekly_income,
            "monthly_income": monthly_income,
        }

        return Response(data, status=status.HTTP_200_OK)

    def calculate_income(self, visits, days):
        start_date = now() - timedelta(days=days)
        filtered_visits = visits.filter(confirmation_time__gte=start_date)
        total_income = filtered_visits.aggregate(total=Sum('price'))['total']
        return total_income or 0


class ActiveArtistView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        if hasattr(user, 'saloon'):
            saloon = SaloonModel.objects.filter(saloon=user).first()
            print(saloon.pk)
            artists = ArtistModel.objects.filter(saloon_artists_id=saloon.pk)
            active_artists = {}
            artists = list(artists)
            for artist in artists:
                if VisitingTimeModel.objects.filter(artist=artist, suggested_date=now().date()).first():
                    active_artists.update({str(artist): 'active'})
                    artists.remove(artist)
            for deactive_artisit in artists:
                active_artists.update({str(deactive_artisit): 'deactive'})
            return Response(active_artists, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "User does not have a valid artist or saloon profile."}, status=status.HTTP_400_BAD_REQUEST)
            


class GettingFinancialView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FinancialSummarySerializer(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data

            start_date = validated_data['start_date']
            end_date = validated_data['end_date']
            start_price = validated_data['start_price']
            end_price = validated_data['end_price']

            user = request.user
            if hasattr(user, 'artist'):
                visits = VisitingTimeModel.objects.filter(artist=user.artist.pk)
            elif hasattr(user, 'saloon'):
                visits = VisitingTimeModel.objects.filter(saloon=user.saloon.pk)
            else:
                return Response({"detail": "User does not have a valid artist or saloon profile."},
                                status=status.HTTP_400_BAD_REQUEST)

            filtered_visits = visits.filter(
                confirmation_time__range=(start_date, end_date),
                price__range=(start_price, end_price)
            )

            visits_data = [self.visit_to_dict(visit) for visit in filtered_visits]
            return Response(visits_data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def visit_to_dict(self, visit):
        return {
            "user": visit.user.username,
            "artist": visit.artist.name if visit.artist else None,
            "saloon": visit.saloon.name if visit.saloon else None,
            "service": visit.service.name if visit.service else None,
            "confirmation_time": visit.confirmation_time,
            "price": visit.price,
        }


class CalculatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ManagingPaymentSerializer(data=request.data)
        if serializer.is_valid():
            days = serializer.validated_data['days']
            start_date = now() - timedelta(days=days)
            user = request.user
            if hasattr(user, 'artist'):
                visits = VisitingTimeModel.objects.filter(artist=user.artist.pk)
            elif hasattr(user, 'saloon'):
                visits = VisitingTimeModel.objects.filter(saloon=user.saloon.pk)
            else:
                return Response({"detail": "User does not have a valid artist or saloon profile."},
                                status=status.HTTP_400_BAD_REQUEST)
            total_price = visits.aggregate(total=Sum('price'))['total'] or 0
            # todo: handlig payment gateway
            return Response({"total_price": total_price}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserServicesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        all_services = ServiceModel.objects.all()

        if hasattr(user, 'artist'):
            user_services = UserServicesModel.objects.filter(artist=user.artist.pk)
        elif hasattr(user, 'saloon'):
            user_services = UserServicesModel.objects.filter(saloon=user.saloon.pk)
        else:
            return Response({"detail": "User must be associated with either an artist or a saloon."}, status=status.HTTP_400_BAD_REQUEST)

        all_services_data = [{"service_code": service.service_code, "service_name": service.service_name} for service in all_services]
        user_services_data = UserServiceSerializer(user_services, many=True).data

        return Response({
            "all_services": all_services_data,
            "user_services": user_services_data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = UserServiceSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user

            if hasattr(user, 'artist'):
                UserServicesModel.objects.create(artist=user.artist.pk, **serializer.validated_data)
            elif hasattr(user, 'saloon'):
                UserServicesModel.objects.create(saloon=user.saloon.pk, **serializer.validated_data)
            else:
                return Response({"detail": "User must be associated with either an artist or a saloon."}, status=status.HTTP_400_BAD_REQUEST)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HandingVisitingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if hasattr(user, 'saloon') or hasattr(user, 'artist'):
            serializer = HandigVisitSerializer()
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        if hasattr(user, 'saloon'):
            serializer = HandigVisitSerializer(data=request.data)
            if serializer.is_valid():
                serializer.validated_data['saloon'] = user.saloon.pk
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        if hasattr(user, 'artist'):
            serializer = HandigVisitSerializer(data=request.data)
            if serializer.is_valid():
                username = request.data.get('username')
                user_service = UserServicesModel.objects.filter(artist=user.artist.pk).first()
                if username != None:
                    customer = User.objects.filter(username=username).first()
                    if customer != None:
                        exact_time = str(serializer.validated_data.get('exact_time'))
                        suggested_date, suggested_hour = exact_time.split(' ')
                        serializer.validated_data['artist'] = user.artist
                        serializer.validated_data['saloon'] = user.artist.saloon_artists
                        serializer.validated_data['user'] = customer
                        serializer.validated_data['suggested_hour'] = suggested_hour
                        serializer.validated_data['suggested_date'] = suggested_date
                        serializer.validated_data['price'] = user_service.suggested_price
                        serializer.validated_data['confirmation_time'] = jdatetime.datetime.now()
                        serializer.validated_data['payment_due_time'] = jdatetime.datetime.now() + timedelta(minutes=40)
                        serializer.save()
                        return Response(serializer.data, status=status.HTTP_201_CREATED)
                    else:
                        exact_time = str(serializer.validated_data.get('exact_time'))
                        suggested_date, suggested_hour = exact_time.split(' ')
                        unregistered_user_name = request.data.get('name')
                        unregistered_phone_number = request.data.get('phone_number')
                        UnregisteredUser(name=unregistered_user_name, phone_number=unregistered_phone_number).save()
                        unregistered_user = UnregisteredUser.objects.filter(phone_number=unregistered_phone_number).first()
                        serializer.validated_data['artist'] = user.artist
                        serializer.validated_data['saloon'] = user.artist.saloon_artists
                        serializer.validated_data['suggested_hour'] = suggested_hour
                        serializer.validated_data['suggested_date'] = suggested_date
                        serializer.validated_data['unregistered_user'] = unregistered_user
                        serializer.validated_data['price'] = user_service.suggested_price
                        serializer.validated_data['confirmation_time'] = jdatetime.datetime.now()
                        serializer.validated_data['payment_due_time'] = jdatetime.datetime.now() + timedelta(minutes=40)
                        serializer.save()
                        return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({'error': 'You can not make this visiting time.'}, status=status.HTTP_400_BAD_REQUEST)


class SupserviceFromArtistAPIView(APIView):
    def get(self, request):
        user = request.user
        if hasattr(user, 'artist'):
            supservices = UserServicesModel.objects.filter(artist=user.artist.pk)
            serializer = UserServiceSerializer(supservices, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response({'error': 'Only artists can get their supservices.'}, status=status.HTTP_403_FORBIDDEN)


class GetArtsitsFromSaloonAPIView(APIView):
    def get(self, request):
        user = request.user
        if hasattr(user, 'saloon'):
            saloon = SaloonModel.objects.filter(id=request.user.saloon.pk).first()
            if saloon:
                artists = ArtistModel.objects.filter(saloon_artists=saloon).all()
                if artists:
                    serializer = ArtistProfileSerializer(artists, many=True, context={'request': request})
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response({'error': 'There is no artist in this saloon.'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'error': 'Saloon not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'Only saloons can get their artists.'}, status=status.HTTP_403_FORBIDDEN)


class GetVisitsFromArtistAPIView(APIView):
    def get(self, request, artist_id):
        user = request.user
        time = jdatetime.datetime.now()
        if hasattr(user, 'saloon'):
            first_visits = VisitingTimeModel.objects.filter(artist=artist_id, saloon=user.saloon.pk,
                                                     exact_time__gt=jdatetime.datetime(time.year, time.month, time.day),
                                                     exact_time__lt=jdatetime.datetime(time.year, time.month, time.day, 23, 59)).all()
            second_visits = VisitingTimeModel.objects.filter(artist=artist_id, saloon=user.saloon.pk, suggested_date__gte=time.date()).all()
            visits = first_visits.union(second_visits)
            if visits:
                serializer = VisitingTimeSerializerGet(visits, many=True, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({'error': 'There is no visit for this artist.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'Only saloons can get their artists visits.'}, status=status.HTTP_403_FORBIDDEN)


class ManageArtistTeamView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        saloon = request.user.saloon

        if not saloon:
            return Response({"detail": "You are not associated with any saloon."}, status=status.HTTP_403_FORBIDDEN)

        artists = ArtistModel.objects.filter(saloon_artists=saloon)

        serializer = ArtistProfileSerializer(artists, many=True, context={'request': request})

        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ManageArtistTeamSerializer(data=request.data)
        if serializer.is_valid():
            artist_id = serializer.data.get('artist_id')
            artist = ArtistModel.objects.get(pk=artist_id)
            saloon = request.user.saloon

            if artist.saloon_artists == saloon:
                return Response({"detail": "Artist is already part of this saloon."}, status=status.HTTP_400_BAD_REQUEST)

            artist.saloon_artists = saloon
            artist.save()

            return Response({"detail": "Artist added to saloon's team."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        serializer = ManageArtistTeamSerializer(data=request.data)
        if serializer.is_valid():
            artist_id = serializer.validated_data['artist_id']
            artist = ArtistModel.objects.get(pk=artist_id)
            saloon = request.user.saloon

            if artist.saloon_artists != saloon:
                return Response({"detail": "Artist is not part of this saloon."}, status=status.HTTP_400_BAD_REQUEST)

            artist.saloon_artists = None
            artist.save()

            return Response({"detail": "Artist removed from saloon's team."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        posts = PostModel.objects.none()
        if hasattr(user, 'normal_user'):
            artist_followed_by_this_user = ArtistFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            artists = ArtistModel.objects.filter(id__in=artist_followed_by_this_user).values_list('artist', flat=True)
            saloon_followed_by_this_user = SaloonFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            saloons = SaloonModel.objects.filter(id__in=saloon_followed_by_this_user).values_list('saloon', flat=True)
            posts = PostModel.objects.filter(user__in=list(artists) + list(saloons))
        elif hasattr(user, 'artist'):
            artist_followed_by_this_user = ArtistFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            artists = ArtistModel.objects.filter(id__in=artist_followed_by_this_user).values_list('artist', flat=True)
            saloon_followed_by_this_user = SaloonFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            saloons = SaloonModel.objects.filter(id__in=saloon_followed_by_this_user).values_list('saloon', flat=True)
            posts = PostModel.objects.filter(user__in=list(artists) + list(saloons))
        elif hasattr(user, 'saloon'):
            artist_followed_by_this_user = ArtistFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            artists = ArtistModel.objects.filter(id__in=artist_followed_by_this_user).values_list('artist', flat=True)
            saloon_followed_by_this_user = SaloonFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            saloons = SaloonModel.objects.filter(id__in=saloon_followed_by_this_user).values_list('saloon', flat=True)
            posts = PostModel.objects.filter(user__in=list(artists) + list(saloons))
        posts = posts.order_by('-created')
        serializer = PostSerializerGet(posts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        if not hasattr(user, 'artist') and not hasattr(user, 'saloon'):
            return Response({'error': 'Only artists and saloons can create story.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = PostSerializerPost(data=request.data, context={'request': request})
        if serializer.is_valid():
            post_content = serializer.validated_data['post_content']
            file_extension = str(post_content.name).split('.')[-1].lower()

            if file_extension in ('png', 'jpg', 'jpeg'):
                image = Image.open(post_content)
                width, height = image.size
            elif file_extension in ('mp4', 'mpeg', 'mpg'):
                try:
                    # Create a temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.' + file_extension) as temp_file:
                        for chunk in post_content.chunks():
                            temp_file.write(chunk)
                        temp_file_path = temp_file.name

                    # Use VideoFileClip to check the duration and size
                    clip = VideoFileClip(temp_file_path)
                    duration = clip.duration
                    width, height = clip.size
                    clip.close()

                    # Remove the temporary file
                    os.remove(temp_file_path)

                    if duration > 60:
                        return Response({'error': 'Video duration should be less than 60 seconds.'},
                                        status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    return Response({'error': f'An error occurred while processing the video: {str(e)}'},
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'error': 'Unsupported file type.'}, status=status.HTTP_400_BAD_REQUEST)

            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        user = request.user
        try:
            post = PostModel.objects.get(pk=pk)
        except PostModel.DoesNotExist:
            return Response({'error': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)

        if post.user != user:
            return Response({'error': 'You do not have permission to edit this post.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = PostSerializerPost(post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        user = request.user
        try:
            post = PostModel.objects.get(pk=pk)
        except PostModel.DoesNotExist:
            return Response({'error': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)

        if post.user != user:
            return Response({'error': 'You do not have permission to delete this post.'}, status=status.HTTP_403_FORBIDDEN)

        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfilePostAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        current_user = request.user
        user = get_object_or_404(User, pk=user_id)
        if hasattr(user, 'saloon'):
            posts = PostModel.objects.filter(user=user).all()
            serializer = PostSerializerGet(posts, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        if hasattr(user, 'artist'):
            posts = PostModel.objects.filter(user=user).all()
            serializer = PostSerializerGet(posts, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)


class ProfileCertificateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        current_user = request.user
        user = get_object_or_404(User, pk=user_id)
        if hasattr(user, 'saloon'):
            if SaloonFollow.objects.filter(follower=user.saloon.pk, followed_user=current_user.pk).exists():
                posts = PostModel.objects.filter(user=user, is_certificate=True).all()
                serializer = PostSerializerGet(posts, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'You don\'t follow this saloon'}, status=status.HTTP_400_BAD_REQUEST)
        if hasattr(user, 'artist'):
            if ArtistFollow.objects.filter(follower=user.artist.pk, followed_user=current_user.pk).exists():
                posts = PostModel.objects.filter(user=user, is_certificate=True).all()
                serializer = PostSerializerGet(posts, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'You don\'t follow this artist'}, status=status.HTTP_400_BAD_REQUEST)


class GetCertificates(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        posts = PostModel.objects.filter(user=user, is_certificate=True).all()
        if posts:
            serializer = PostSerializerGet(posts, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'You don\'t have any certificates.'}, status=status.HTTP_400_BAD_REQUEST)
        

class CertificateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        posts = PostModel.objects.none()
        if hasattr(user, 'normal_user'):
            artist_followed_by_this_user = ArtistFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            artists = ArtistModel.objects.filter(id__in=artist_followed_by_this_user).values_list('artist', flat=True)
            saloon_followed_by_this_user = SaloonFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            saloons = SaloonModel.objects.filter(id__in=saloon_followed_by_this_user).values_list('saloon', flat=True)
            posts = PostModel.objects.filter(user__in=list(artists) + list(saloons), is_certificate=True)
        elif hasattr(user, 'artist'):
            artist_followed_by_this_user = ArtistFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            artists = ArtistModel.objects.filter(id__in=artist_followed_by_this_user).values_list('artist', flat=True)
            saloon_followed_by_this_user = SaloonFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            saloons = SaloonModel.objects.filter(id__in=saloon_followed_by_this_user).values_list('saloon', flat=True)
            posts = PostModel.objects.filter(user__in=list(artists) + list(saloons), is_certificate=True)
        elif hasattr(user, 'saloon'):
            artist_followed_by_this_user = ArtistFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            artists = ArtistModel.objects.filter(id__in=artist_followed_by_this_user).values_list('artist', flat=True)
            saloon_followed_by_this_user = SaloonFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            saloons = SaloonModel.objects.filter(id__in=saloon_followed_by_this_user).values_list('saloon', flat=True)
            posts = PostModel.objects.filter(user__in=list(artists) + list(saloons), is_certificate=True)

        serializer = PostSerializerGet(posts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        user = request.user
        if not hasattr(user, 'artist') and not hasattr(user, 'saloon'):
            return Response({'error': 'Only artists and saloons can create story.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = PostSerializerPost(data=request.data, context={'request': request})
        if serializer.is_valid():
            post_content = serializer.validated_data['post_content']
            file_extension = str(post_content.name).split('.')[-1].lower()

            if file_extension in ('png', 'jpg', 'jpeg'):
                image = Image.open(post_content)
                width, height = image.size
            else:
                return Response({'error': 'Unsupported file type.'}, status=status.HTTP_400_BAD_REQUEST)
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        user = request.user
        try:
            post = PostModel.objects.get(pk=pk)
        except PostModel.DoesNotExist:
            return Response({'error': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)

        if post.user != user:
            return Response({'error': 'You do not have permission to edit this post.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = PostSerializerPost(post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        user = request.user
        try:
            post = PostModel.objects.get(pk=pk)
        except PostModel.DoesNotExist:
            return Response({'error': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)

        if post.user != user:
            return Response({'error': 'You do not have permission to delete this post.'}, status=status.HTTP_403_FORBIDDEN)

        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



class StoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        current_time = timezone.now()  # Get the current time
        stories = StoryModel.objects.none()

        if hasattr(user, 'normal_user'):
            artist_followed_by_this_user = ArtistFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            artists = ArtistModel.objects.filter(id__in=artist_followed_by_this_user).values_list('artist', flat=True)
            saloon_followed_by_this_user = SaloonFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            saloons = SaloonModel.objects.filter(id__in=saloon_followed_by_this_user).values_list('saloon', flat=True)
            stories = StoryModel.objects.filter(
                user__in=list(artists) + list(saloons),
                created__gte=current_time - timedelta(hours=24)  # Filter out stories older than 24 hours
            )
        elif hasattr(user, 'artist'):
            artist_followed_by_this_user = ArtistFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            artists = ArtistModel.objects.filter(id__in=artist_followed_by_this_user).values_list('artist', flat=True)
            saloon_followed_by_this_user = SaloonFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            saloons = SaloonModel.objects.filter(id__in=saloon_followed_by_this_user).values_list('saloon', flat=True)
            stories = StoryModel.objects.filter(
                user__in=(list(artists) + list(saloons)),
                created__gte=current_time - timedelta(hours=24)  # Filter out stories older than 24 hours
            )
        elif hasattr(user, 'saloon'):
            artist_followed_by_this_user = ArtistFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            artists = ArtistModel.objects.filter(id__in=artist_followed_by_this_user).values_list('artist', flat=True)
            saloon_followed_by_this_user = SaloonFollow.objects.filter(followed_user=user).values_list('follower', flat=True)
            saloons = SaloonModel.objects.filter(id__in=saloon_followed_by_this_user).values_list('saloon', flat=True)
            stories = StoryModel.objects.filter(
                user__in=(list(artists) + list(saloons)),
                created__gte=current_time - timedelta(hours=24)  # Filter out stories older than 24 hours
            )
        purple_stories = StoryModel.objects.filter(user__first_name='بنفش')
        all_stories = stories.union(purple_stories)
        all_stories.order_by('-created')
        serializer = StorySerializerGet(all_stories, many=True, context={'request': request})
        serialized_data = serializer.data

        # Group stories by user (first_name and profile_picture)
        grouped_stories = []
        sorted_data = sorted(serialized_data, key=itemgetter('name', 'profile_picture'))
        for key, group in groupby(sorted_data, key=itemgetter('name', 'profile_picture')):
            grouped_stories.append({
                'first_name': key[0],
                'profile_picture': key[1],
                'stories': [story.get('story_content') for story in group]
            })

        # Pagination
        paginator = LimitOffsetPagination()
        paginated_stories = paginator.paginate_queryset(grouped_stories, request)

        return Response(paginated_stories, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        duration = 0
        if not hasattr(user, 'artist') and not hasattr(user, 'saloon'):
            return Response({'error': 'Only artists and saloons can create story.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = StorySerializerPost(data=request.data, context={'request': request, 'duration_time': duration})
        if serializer.is_valid():
            story_content = serializer.validated_data.get('story_content')
            file_extension = str(story_content.name).split('.')[-1].lower()
            if file_extension in ('png', 'jpg', 'jpeg'):
                image = Image.open(story_content)
                width, height = image.size
            elif file_extension in ('mp4', 'mpeg', 'mpg'):
                try:
                    # Create a temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.' + file_extension) as temp_file:
                        for chunk in story_content.chunks():
                            temp_file.write(chunk)
                        temp_file_path = temp_file.name

                    # Use VideoFileClip to check the duration and size
                    clip = VideoFileClip(temp_file_path)
                    duration = clip.duration
                    width, height = clip.size
                    clip.close()

                    # Remove the temporary file
                    os.remove(temp_file_path)

                    if duration > 36:
                        return Response({'error': 'Video duration should be less than 10 seconds.'},
                                        status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    return Response({'error': f'An error occurred while processing the video: {str(e)}'},
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'error': 'Unsupported file type.'}, status=status.HTTP_400_BAD_REQUEST)
            serializer.save(user=user, duration_time=duration)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        user = request.user
        try:
            story = PostModel.objects.get(pk=pk)
        except PostModel.DoesNotExist:
            return Response({'error': 'Story not found.'}, status=status.HTTP_404_NOT_FOUND)

        if story.user != user:
            return Response({'error': 'You do not have permission to edit this story.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = StorySerializerPost(story, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        user = request.user
        try:
            story = PostModel.objects.get(pk=pk)
        except PostModel.DoesNotExist:
            return Response({'error': 'Story not found.'}, status=status.HTTP_404_NOT_FOUND)

        if story.user != user:
            return Response({'error': 'You do not have permission to delete this story.'}, status=status.HTTP_403_FORBIDDEN)

        story.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HighlightAPIView(APIView):
    def get(self, request):
        user = request.user
        if not hasattr(user, 'artist') and not hasattr(user, 'saloon'):
            return Response({'error': 'Only artists and saloons can create Highlight.'}, status=status.HTTP_403_FORBIDDEN)
        highlights = HighlightModel.objects.filter(user=user)
        serializer: HighlightSerializerGet = HighlightSerializerGet(highlights, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user  = request.user
        if not hasattr(user, 'artist') and not hasattr(user, 'saloon'):
            return Response({'error': 'Only artists and saloons can create Highlight.'}, status=status.HTTP_403_FORBIDDEN)
        highlight_serializer: HighlightSerializerPost = HighlightSerializerPost(data=request.data, context={'request': request})
        if highlight_serializer.is_valid():
            highlight_content = highlight_serializer.validated_data['highlight_content']

            file_extension = str(highlight_content.name).split('.')[-1].lower()

            if file_extension in ('png', 'jpg', 'jpeg'):
                image = Image.open(highlight_content)
                width, height = image.size
            elif file_extension in ('mp4', 'mpeg', 'mpg'):
                try:
                    # Create a temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.' + file_extension) as temp_file:
                        for chunk in highlight_content.chunks():
                            temp_file.write(chunk)
                        temp_file_path = temp_file.name

                    # Use VideoFileClip to check the duration and size
                    clip = VideoFileClip(temp_file_path)
                    duration = clip.duration
                    width, height = clip.size
                    clip.close()

                    # Remove the temporary file
                    os.remove(temp_file_path)

                    if duration > 60:
                        return Response({'error': 'Video duration should be less than 10 seconds.'},
                                        status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    return Response({'error': f'An error occurred while processing the video: {str(e)}'},
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'error': 'Unsupported file type.'}, status=status.HTTP_400_BAD_REQUEST)
            highlight_serializer.save(user=user)
            return Response(highlight_serializer.data, status=status.HTTP_201_CREATED)
        return Response(highlight_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            updated_highlight = HighlightModel.objects.get(pk=pk)
        except HighlightModel.DoesNotExist:
            return Response({'error': 'Highlight not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        if updated_highlight.user != request.user:
            return Response({'error': 'You do not have permission to edit this Highlight.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = HighlightSerializerPost(updated_highlight, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        user = request.user
        try:
            deleted_highlight = HighlightModel.objects.get(pk=pk)
        except PostModel.DoesNotExist:
            return Response({'error': 'Story not found.'}, status=status.HTTP_404_NOT_FOUND)

        if deleted_highlight.user != user:
            return Response({'error': 'You do not have permission to delete this story.'}, status=status.HTTP_403_FORBIDDEN)

        deleted_highlight.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReturnLikeAPIView(APIView):
    def get(self, request, post_id):
        post = PostModel.objects.filter(id=post_id).first()
        return Response({'like_amount': post.likes}, status=status.HTTP_200_OK)


class LikeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        post = get_object_or_404(PostModel, id=post_id)
        if LikeModel.objects.filter(post=post, user=request.user).exists():
            return Response({'liked': True}, status=status.HTTP_200_OK)
        return Response({'liked': False}, status=status.HTTP_400_BAD_REQUEST)


    def post(self, request, post_id):
        post = get_object_or_404(PostModel, id=post_id)
        user = request.user

        # Check if the user already liked the post
        if LikeModel.objects.filter(user=user, post=post).exists():
            return Response({'error': 'You have already liked this post.'}, status=status.HTTP_400_BAD_REQUEST)

        LikeModel.objects.create(user=user, post=post)
        post.likes = LikeModel.Like_count(post)
        post.save()

        return Response({'message': 'Post liked successfully.', 'like_count': post.likes}, status=status.HTTP_201_CREATED)

    def delete(self, request, post_id):
        post = get_object_or_404(PostModel, id=post_id)
        user = request.user
        Liked = LikeModel.objects.filter(user=user, post=post).first()
        if Liked:
            Liked.delete()
            post.likes = LikeModel.Like_count(post)
            post.save()
            return Response({'message': 'Like removed successfully.', 'like_count': post.likes}, status=status.HTTP_200_OK)

        return Response({'error': 'You have\'t liked this post.'}, status=status.HTTP_400_BAD_REQUEST)


class SaloonVisitsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        saloons = SaloonModel.objects.all()
        user = request.user
        if hasattr(user, 'saloon'):
            saloons = saloons.exclude(id=request.user.saloon.pk)
        serializer = SaloonVisitsSerializer(saloons, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ArtistVisitsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        artists = ArtistModel.objects.all()
        user = request.user
        if hasattr(user, 'artist'):
            artists = artists.exclude(id=request.user.artist.pk)
        serializer = ArtistVisitsSerializer(artists, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetAllArtistsFromSaloon(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, saloon_id):
        saloon_artists = ArtistModel.objects.filter(saloon_artists=saloon_id).values_list('saloon_artists', flat=True)
        if saloon_artists:
            artists = ArtistModel.objects.filter(saloon_artists__in=saloon_artists)
            serializer = ArtistProfileSerializer(artists, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'No artists found in this saloon.'}, status=status.HTTP_404_NOT_FOUND)


class GetAllServicesFromSaloon(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, saloon_id):
        saloon_artist = ArtistModel.objects.filter(saloon_artists=saloon_id).all()
        if saloon_artist:
            supservice = UserServicesModel.objects.filter(artist__in=saloon_artist).values_list('supservice__service', flat=True).distinct()
            if supservice:
                services = ServiceModel.objects.filter(service_code__in=supservice)
                serializer = ServiceSerializer(services, many=True, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({'error': 'No services found in this saloon.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'No saloon found'}, status=status.HTTP_404_NOT_FOUND)        


class GetSupservicesFromArtist(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, artist_id):
        artist = ArtistModel.objects.filter(id=artist_id).first()
        if artist:
            supservices = UserServicesModel.objects.filter(artist=artist).values_list('supservice', flat=True).distinct()
            if supservices:
                supservices = SupServiceModel.objects.filter(id__in=supservices)
                serializer = SupServiceSerializer(supservices, many=True, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({'error': 'No supservices found in this artist.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'No services found in this artist.'}, status=status.HTTP_404_NOT_FOUND)


class GetSupserviceFromServiceAndSaloon(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, saloon_id, service_id):
        saloon_artists = ArtistModel.objects.filter(saloon_artists=saloon_id).all()
        if saloon_artists:
            usersupservices = UserServicesModel.objects.filter(artist__in=saloon_artists, supservice__service__service_code=service_id).all()
            if usersupservices:
                serializer = UserServiceSerializer(usersupservices, many=True, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({'error': 'No usersupservices found in this saloon.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'No artists found in this saloon.'}, status=status.HTTP_404_NOT_FOUND)


class GetArtistFromSaloonAndSupservice(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, saloon_id, supservice_id):
        saloon_artists = ArtistModel.objects.filter(saloon_artists=saloon_id).values_list('id', flat=True)
        if saloon_artists:
            artists_id = UserServicesModel.objects.filter(artist__in=saloon_artists, supservice=supservice_id).values_list('artist', flat=True).distinct()
            artists = ArtistModel.objects.filter(id__in=artists_id).all()
            if artists:
                serializer = ArtistProfileSerializer(artists, many=True, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({'error': 'No artists found with this supservice.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'No artists found in this saloon.'}, status=status.HTTP_404_NOT_FOUND)


class GetServiceFromArtist(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, artist_id):
        services_id = UserServicesModel.objects.filter(artist=artist_id).values_list('supservice__service', flat=True).distinct()
        if services_id:
            services = ServiceModel.objects.filter(service_code__in=services_id).all()
            serializer = ServiceSerializer(services, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({'error': 'No services found in this artist.'}, status=status.HTTP_404_NOT_FOUND)


class GetSupserviceFromArtistAndService(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, artist_id, service_id):
        supservices_ids = UserServicesModel.objects.filter(artist=artist_id, supservice__service__service_code=service_id).values_list('supservice', flat=True)
        if supservices_ids:
            supservices = SupServiceModel.objects.filter(id__in=supservices_ids).all()
            serializer = SupServiceSerializer(supservices, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({'error': 'No supservices found in this artist.'}, status=status.HTTP_404_NOT_FOUND)


class UserConfirmedVisitingTimeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        visits = VisitingTimeModel.objects.filter(user=user, status='confirmed').all()
        serializer = VisitingTimeSerializerGet(visits, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserOtherVisitingTimeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        visits = VisitingTimeModel.objects.filter(user=user).exclude(status='completed').exclude(status='rejected').all()
        serializer = VisitingTimeSerializerGet(visits, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserCompletedVisitingTimeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # if not (hasattr(user, 'artist') or hasattr(user, 'saloon')):
        visits = VisitingTimeModel.objects.filter(user=user, status='completed').all()
        serializer = VisitingTimeSerializerGet(visits, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class RequestVisitingTimeSaloonAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        saloon = get_object_or_404(SaloonModel, pk=user_id)
        user = request.user
        visits = VisitingTimeModel.objects.filter(saloon=saloon, user=user)

        if visits.exists():
            serializer = SaloonVisitingTimeSerializerPost(visits, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # If no visits exist, return the saloon and user details for creating a visit
            response_data = {
                'saloon': {
                    'id': saloon.id,
                    'name': saloon.name,
                    'artist': int(),
                },
                'user': {
                    'id': user.id,
                    'username': user.username,
                },
                'supservice': int(),
                'suggested_time': '',
                'suggested_date': '',
                'exact_time': '',
                'status': '',
            }
            return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request, user_id):
        user = request.user
        data = request.data.copy()
        data['user'] = user.id
        data['saloon'] = user_id
        saloon = json.loads(request.data.get('saloon'))
        saloon_id = saloon.get('id')
        saloon_obj: SaloonModel = SaloonModel.objects.get(id=saloon_id).id
        saloon_real: SaloonModel = SaloonModel.objects.get(id=saloon_id)
        artist_id = saloon.get('artist')
        artist: ArtistModel = ArtistModel.objects.get(id=artist_id).id
        artist_real: ArtistModel = ArtistModel.objects.get(id=artist_id)
        data['artist'] = artist
        supservice_name = request.data.get('service')
        price = UserServicesModel.objects.filter(artist=artist, supservice=supservice_name).first().suggested_price
        supservice = SupServiceModel.objects.filter(id=supservice_name).first()
        if supservice != None:
            data['service'] = supservice.id
            data['price'] = price
        else:
            data['service'] = None
        if 'exact_time' not in data or data['exact_time'] == '':
            data['exact_time'] = None
        # TODO: The serializer must be convert so I can get the artist for the saloon or the saloon for the artist
        serializer = SaloonVisitingTimeSerializerPost(data=data, context={'request': request})

        if serializer.is_valid():
            visit = serializer.save()
            # TODO: uncomment this
            # artist_user_id = artist.artist_id
            # saloon_user_id = saloon.saloon_id
            # send_visit_notification(artist_user_id, 'یک نوبت جدید دارید.') # TODO: Uncomment the notification function   
            # send_visit_notification(saloon_user_id, 'یک نوبت جدید دارید.') # TODO: Uncomment the notification function
            message = "یک نوبت جدید برای شما ارسال شد."
            # phone_number = visit.saloon.saloon.phone_number
            url = "http://127.0.0.1:8000/service/visits/"
            sms_for_new_visiting_time_saloon(saloon_real.saloon.phone_number, saloon_real.saloon.first_name) # TODO: Uncomment the notification function  
            sms_for_new_visiting_time_artist(artist_real.artist.phone_number, artist_real.artist.first_name)   # TODO: Uncomment the notification function              
            return Response(serializer.data, status=status.HTTP_201_CREATED)        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RequestVisitingTimeArtistAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        artist = get_object_or_404(ArtistModel, pk=user_id)
        user = request.user
        visits = VisitingTimeModel.objects.filter(artist=artist, user=user)

        if visits.exists():
            serializer = ArtistVisitingTimeSerializerPost(visits, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # If no visits exist, return the saloon and user details for creating a visit
            response_data = {
                'artist': {
                    'id': artist.id,
                    'name': artist.artist.first_name,
                },
                'user': {
                    'id': user.id,
                    'username': user.username,
                },
                'supservice': int(),
                'suggested_time': '',
                'suggested_hour': '',
                'suggested_date': '',
                'exact_time': '',
                'status': '',
            }
            return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request, user_id):
        user = request.user
        data = request.data.copy()
        data['user'] = user.id
        data['artist'] = user_id
        saloon = SaloonModel.objects.get(id=user_id)
        data['saloon'] = saloon
        if 'exact_time' not in data or data['exact_time'] == '':
            data['exact_time'] = None

        serializer = ArtistVisitingTimeSerializerPost(data=data, context={'request': request})

        if serializer.is_valid():
            visit = serializer.save()
            message = "یک نوبت جدید برای شما ارسال شد."
            phone_number = visit.artist.artist.phone_number
            url = "http://127.0.0.1:8000/service/visits/"
            # send_verification_code(message, phone_number, url)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetConfirmVisitAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        dates = list(request.data.get('dates'))
        if hasattr(user, 'artist'):
            user_morning_visiting_time = VisitingTimeModel.objects.filter(artist=user.artist.pk, suggested_date__in=dates, suggested_time='morning', status__in=['waiting for deposit', 'waiting for confirmation', 'confirmed', 'rejected', 'completed']).all().order_by('-suggested_date')
            if user_morning_visiting_time:
                morning_serializer = VisitingTimeSerializerGet(user_morning_visiting_time, many=True, context={'request': request})
            else:
                morning_serializer = []
            user_noon_visiting_time = VisitingTimeModel.objects.filter(artist=user.artist.pk, suggested_date__in=dates, suggested_time='noon', status__in=['waiting for deposit', 'waiting for confirmation', 'confirmed', 'rejected', 'completed']).all().order_by('-suggested_date')
            if user_noon_visiting_time:
                noon_serializer = VisitingTimeSerializerGet(user_noon_visiting_time, many=True, context={'request': request})
            else:
                noon_serializer = []
            user_evening_visiting_time = VisitingTimeModel.objects.filter(artist=user.artist.pk, suggested_date__in=dates, suggested_time='evening', status__in=['waiting for deposit', 'waiting for confirmation', 'confirmed', 'rejected', 'completed']).all().order_by('-suggested_date')
            if user_evening_visiting_time:
                evening_serializer = VisitingTimeSerializerGet(user_evening_visiting_time, many=True, context={'request': request})
            else:
                evening_serializer = []
            user_night_visiting_time = VisitingTimeModel.objects.filter(artist=user.artist.pk, suggested_date__in=dates, suggested_time='night', status__in=['waiting for deposit', 'waiting for confirmation', 'confirmed', 'rejected', 'completed']).all().order_by('-suggested_date')
            if user_night_visiting_time:
                night_serializer = VisitingTimeSerializerGet(user_night_visiting_time, many=True, context={'request': request})
            else:
                night_serializer = []
            queries = user_morning_visiting_time | user_noon_visiting_time | user_evening_visiting_time | user_night_visiting_time
            waiting_for_confirmation_number = 0
            rejected_number = 0
            confirmed_number = 0
            for visit in queries:
                if visit.status == 'waiting for confirmation':
                    waiting_for_confirmation_number += 1
                elif visit.status == 'confirmed':
                    confirmed_number += 1
                elif visit.status == 'rejected':
                    rejected_number += 1
            
            waiting_for_deposit_visits = VisitingTimeModel.objects.filter(artist=user.artist.pk, status='waiting for deposit').all()
            if waiting_for_deposit_visits:
                waiting_for_deposit_serializer = VisitingTimeSerializerGet(waiting_for_deposit_visits, many=True, context={'request': request})
            else:
                waiting_for_deposit_serializer = []

            waiting_for_confirmation_visits = VisitingTimeModel.objects.filter(artist=user.artist.pk, status='waiting for confirmation').all()
            if waiting_for_confirmation_visits:
                waiting_for_confirmation_serializer = VisitingTimeSerializerGet(waiting_for_deposit_visits, many=True, context={'request': request})
            else:
                waiting_for_confirmation_serializer = []

            confirmed_visits = VisitingTimeModel.objects.filter(artist=user.artist.pk, status='confirmed').all()
            if confirmed_visits:
                confirmed_serializer = VisitingTimeSerializerGet(waiting_for_deposit_visits, many=True, context={'request': request})
            else:
                confirmed_serializer = []

            return Response({'morning': morning_serializer if isinstance(morning_serializer, list) else morning_serializer.data,
                            'noon': noon_serializer if isinstance(noon_serializer, list) else noon_serializer.data,
                            'evening': evening_serializer if isinstance(evening_serializer, list) else evening_serializer.data,
                            'night': night_serializer if isinstance(night_serializer, list) else night_serializer.data,
                            'waiting_for_confirmation_number': str(waiting_for_confirmation_number),
                            'rejected_number': str(rejected_number),
                            'confirmed_number': str(confirmed_number),
                            'waiting_for_deposit': waiting_for_deposit_serializer if isinstance(waiting_for_deposit_serializer, list) else waiting_for_deposit_serializer.data,
                            'waiting_for_deposit': waiting_for_deposit_serializer if isinstance(waiting_for_deposit_serializer, list) else waiting_for_deposit_serializer.data,
                            'waiting_for_confirmation': waiting_for_confirmation_serializer if isinstance(waiting_for_confirmation_serializer, list) else waiting_for_confirmation_serializer.data,
                            'confirmed': confirmed_serializer if isinstance(confirmed_serializer, list) else confirmed_serializer.data},
                            status=status.HTTP_200_OK)

        elif hasattr(user, 'saloon'):
            user_morning_visiting_time = VisitingTimeModel.objects.filter(saloon=user.saloon.pk, suggested_date__in=dates, suggested_time='morning', status__in=['waiting for deposit', 'waiting for confirmation', 'confirmed', 'rejected', 'completed']).all().order_by('-suggested_date')
            if user_morning_visiting_time:
                morning_serializer = VisitingTimeSerializerGet(user_morning_visiting_time, many=True, context={'request': request})
            else:
                morning_serializer = []
            user_noon_visiting_time = VisitingTimeModel.objects.filter(saloon=user.saloon.pk, suggested_date__in=dates, suggested_time='noon', status__in=['waiting for deposit', 'waiting for confirmation', 'confirmed', 'rejected', 'completed']).all().order_by('-suggested_date')
            if user_noon_visiting_time:
                noon_serializer = VisitingTimeSerializerGet(user_noon_visiting_time, many=True, context={'request': request})
            else:
                noon_serializer = []
            user_evening_visiting_time = VisitingTimeModel.objects.filter(saloon=user.saloon.pk, suggested_date__in=dates, suggested_time='evening', status__in=['waiting for deposit', 'waiting for confirmation', 'confirmed', 'rejected', 'completed']).all().order_by('-suggested_date')
            if user_evening_visiting_time:
                evening_serializer = VisitingTimeSerializerGet(user_evening_visiting_time, many=True, context={'request': request})
            else:
                evening_serializer = []
            user_night_visiting_time = VisitingTimeModel.objects.filter(saloon=user.saloon.pk, suggested_date__in=dates, suggested_time='night', status__in=['waiting for deposit', 'waiting for confirmation', 'confirmed', 'rejected', 'completed']).all().order_by('-suggested_date')
            if user_night_visiting_time:
                night_serializer = VisitingTimeSerializerGet(user_night_visiting_time, many=True, context={'request': request})
            else:
                night_serializer = []
            queries = user_morning_visiting_time | user_noon_visiting_time | user_evening_visiting_time | user_night_visiting_time
            waiting_for_confirmation_number = 0
            rejected_number = 0
            confirmed_number = 0
            for visit in queries:
                if visit.status == 'waiting for confirmation':
                    waiting_for_confirmation_number += 1
                elif visit.status == 'confirmed':
                    confirmed_number += 1
                elif visit.status == 'rejected':
                    rejected_number += 1
            
            waiting_for_deposit_visits = VisitingTimeModel.objects.filter(saloon=user.saloon.pk, status='waiting for deposit').all()
            if waiting_for_deposit_visits:
                waiting_for_deposit_serializer = VisitingTimeSerializerGet(waiting_for_deposit_visits, many=True, context={'request': request})
            else:
                waiting_for_deposit_serializer = []

            waiting_for_confirmation_visits = VisitingTimeModel.objects.filter(saloon=user.saloon.pk, status='waiting for confirmation').all()
            if waiting_for_confirmation_visits:
                waiting_for_confirmation_serializer = VisitingTimeSerializerGet(waiting_for_deposit_visits, many=True, context={'request': request})
            else:
                waiting_for_confirmation_serializer = []

            confirmed_visits = VisitingTimeModel.objects.filter(saloon=user.saloon.pk, status='confirmed').all()
            if confirmed_visits:
                confirmed_serializer = VisitingTimeSerializerGet(waiting_for_deposit_visits, many=True, context={'request': request})
            else:
                confirmed_serializer = []

        return Response({'morning': morning_serializer if isinstance(morning_serializer, list) else morning_serializer.data,
                         'noon': noon_serializer if isinstance(noon_serializer, list) else noon_serializer.data,
                         'evening': evening_serializer if isinstance(evening_serializer, list) else evening_serializer.data,
                         'night': night_serializer if isinstance(night_serializer, list) else night_serializer.data,
                         'waiting_for_confirmation_number': str(waiting_for_confirmation_number),
                         'rejected_number': str(rejected_number),
                         'confirmed_number': str(confirmed_number),
                         'waiting_for_deposit': waiting_for_deposit_serializer if isinstance(waiting_for_deposit_serializer, list) else waiting_for_deposit_serializer.data,
                         'waiting_for_confirmation': waiting_for_confirmation_serializer if isinstance(waiting_for_confirmation_serializer, list) else waiting_for_confirmation_serializer.data,
                         'confirmed': confirmed_serializer if isinstance(confirmed_serializer, list) else confirmed_serializer.data},
                         status=status.HTTP_200_OK)


class PostConfirmVisitAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, visit_id):
        visit = get_object_or_404(VisitingTimeModel, id=visit_id)
        if visit:
            serializer = VisitingTimeSerializerGetNew(visit, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, visit_id):
        visit = get_object_or_404(VisitingTimeModel, id=visit_id, status__in=['waiting for confirmation', 'waiting for deposit', 'confirmed'])
        user_id = request.user.pk
        user = request.user
        supservice_price = UserServicesModel.objects.filter(supservice=visit.service, artist=visit.artist).first().suggested_price
        
        if (visit.artist is None or visit.artist.artist is None) and (visit.saloon is None or visit.saloon.saloon is None):
            logger.warning(f"[Visit {visit_id}] No associated artist or saloon. User: {request.user}")
            return Response({'error': 'This visit does not have an associated artist or saloon.'}, status=status.HTTP_400_BAD_REQUEST)

        artist_pk = visit.artist.artist.pk if visit.artist and visit.artist.artist else None
        saloon_pk = visit.saloon.saloon.pk if visit.saloon and visit.saloon.saloon else None

        if not (user_id == artist_pk or user_id == saloon_pk):
            logger.warning(f"[Visit {visit_id}] Permission denied. User: {request.user}")
            return Response({'error': 'You do not have permission to confirm or reject this visit.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = VisitingTimeSerializerPostNew(data=request.data)
        if serializer.is_valid():
            action = serializer.validated_data.get('action')
            suggested_time = serializer.validated_data.get('suggested_time', '1 1')
            exact_time = serializer.validated_data.get('exact_time', '1 1')
            exact_time_str = str(exact_time)

            try:
                date_part, time_part = exact_time_str.strip().split(' ')
                j_year, j_month, j_day = map(int, date_part.split('-'))
                hour, minute = map(int, time_part.split(':'))

                # بررسی معتبر بودن تاریخ شمسی
                if not is_valid_jalali_date(j_year, j_month, j_day):
                    error_message = 'تاریخ شمسی وارد شده معتبر نیست.'
                    logger.warning(f"[Visit {visit_id}] Invalid Jalali date: {exact_time_str} | User: {request.user}")
                    return Response({'error': error_message}, status=status.HTTP_400_BAD_REQUEST)

                jdt = jdatetime.datetime(j_year, j_month, j_day, hour, minute)
                exact_time = jdt.togregorian()
                suggested_date = jdatetime.date(j_year, j_month, j_day)

            except ValueError as e:
                logger.warning(f"[Visit {visit_id}] Invalid date/time format: {exact_time_str} | Error: {e} | User: {request.user}")
                return Response({'error': f'فرمت تاریخ یا ساعت نادرست است: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

            if action == 'confirm':
                suggested_date, suggested_hour = exact_time_str.split(' ')

            if action == 'confirm':
                if not exact_time:
                    logger.warning(f"[Visit {visit_id}] Exact time missing for confirmation | User: {request.user}")
                    return Response({'error': 'Exact time is required for confirmation.'}, status=status.HTTP_400_BAD_REQUEST)

                visit.status = 'waiting for deposit'
                visit.exact_time = exact_time
                visit.suggested_time = suggested_time
                visit.suggested_hour = suggested_hour
                visit.suggested_date = suggested_date
                visit.confirmation_time = timezone.now()
                visit.payment_due_time = timezone.now() + timezone.timedelta(minutes=40)
                visit.price = supservice_price
                visit.save()

                phone_number = visit.user.phone_number
                sms_for_result_of_appointment(phone_number, 'تایید', visit_id)
                paying_url = ''
                sms_for_reminding_deposit(phone_number, paying_url, visit.saloon.saloon.first_name, visit.artist.artist.first_name, visit_id)

                logger.info(f"[Visit {visit_id}] Visit confirmed by user {request.user}")
                return Response({'message': 'Visit confirmed and user notified.'}, status=status.HTTP_200_OK)

            elif action == 'reject':
                visit.status = 'rejected'
                visit.save()

                phone_number = visit.user.phone_number
                sms_for_result_of_appointment(phone_number, 'رد', visit_id)

                logger.info(f"[Visit {visit_id}] Visit rejected by user {request.user}")
                return Response({'message': 'Visit rejected and user notified.'}, status=status.HTTP_200_OK)

        logger.warning(f"[Visit {visit_id}] Serializer errors: {serializer.errors} | User: {request.user}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    # def post(self, request, visit_id):
    #     visit = get_object_or_404(VisitingTimeModel, id=visit_id, status__in=['waiting for confirmation', 'waiting for deposit', 'confirmed'])
    #     user_id = request.user.pk
    #     user = request.user
    #     supservice_price = UserServicesModel.objects.filter(supservice=visit.service, artist=visit.artist).first().suggested_price
    #     if (visit.artist is None or visit.artist.artist is None) and (visit.saloon is None or visit.saloon.saloon is None):
    #         return Response({'error': 'This visit does not have an associated artist or saloon.'}, status=status.HTTP_400_BAD_REQUEST)

    #     artist_pk = visit.artist.artist.pk if visit.artist and visit.artist.artist else None
    #     saloon_pk = visit.saloon.saloon.pk if visit.saloon and visit.saloon.saloon else None

    #     if not (user_id == artist_pk or user_id == saloon_pk):
    #         return Response({'error': 'You do not have permission to confirm or reject this visit.'}, status=status.HTTP_403_FORBIDDEN)

    #     serializer = VisitingTimeSerializerPostNew(data=request.data)
    #     if serializer.is_valid():
    #         action = serializer.validated_data.get('action')
    #         suggested_time = serializer.validated_data.get('suggested_time', '1 1')
    #         exact_time = serializer.validated_data.get('exact_time', '1 1')
    #         exact_time_str = str(exact_time)

    #         try:
    #             # جدا کردن بخش تاریخ و زمان
    #             date_part, time_part = exact_time_str.strip().split(' ')
    #             j_year, j_month, j_day = map(int, date_part.split('-'))
    #             hour, minute = map(int, time_part.split(':'))

    #             # بررسی معتبر بودن تاریخ شمسی
    #             if not is_valid_jalali_date(j_year, j_month, j_day):
    #                 error_message = 'تاریخ شمسی وارد شده معتبر نیست.'
    #                 logger.warning(f"[VisitingTimeModel] Invalid Jalali date: {exact_time_str} | User: {request.user}")
    #                 return Response({'error': error_message}, status=status.HTTP_400_BAD_REQUEST)

    #             # تبدیل به datetime میلادی
    #             jdt = jdatetime.datetime(j_year, j_month, j_day, hour, minute)
    #             exact_time = jdt.togregorian()  # datetime.datetime میلادی
    #             suggested_date = jdatetime.date(j_year, j_month, j_day)

    #         except ValueError as e:
    #             return Response({'error': f'فرمت تاریخ یا ساعت نادرست است: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
            
    #         if action == 'confirm':
    #             suggested_date, suggested_hour = exact_time_str.split(' ') 

    #         if action == 'confirm':
    #             if not exact_time:
    #                 return Response({'error': 'Exact time is required for confirmation.'}, status=status.HTTP_400_BAD_REQUEST)

    #             visit.status = 'waiting for deposit'
    #             visit.exact_time = exact_time
    #             visit.suggested_time = suggested_time
    #             visit.suggested_hour = suggested_hour
    #             visit.suggested_date = suggested_date
    #             visit.confirmation_time = timezone.now()
    #             visit.payment_due_time = timezone.now() + timezone.timedelta(minutes=40)
    #             visit.price = supservice_price
    #             visit.save()
    #             # visiting_user = visit.user
    #             # real_user: User = User.objects.filter(user=visiting_user).first()
    #             # phone_number = real_user.phone_number
    #             # send_visit_notification(visit.user.pk, 'نوبت شما تایید شد برای پرداخت بیعانه 40 دقیقه وقت دارید.') # TODO: Uncomment the notification function
    #             phone_number = visit.user.phone_number
    #             sms_for_result_of_appointment(phone_number, 'تایید', visit_id)     # TODO: UNcomment this function
    #             paying_url = ''
    #             sms_for_reminding_deposit(phone_number, paying_url, visit.saloon.saloon.first_name, visit.artist.artist.first_name, visit_id)     # TODO: UNcomment this function
    #             message = "نوبت شما تایید شد برای پرداخت بیعانه 40 دقیقه وقت دارید."
    #             url = "http://127.0.0.1:8000/service/visits/payment/"
    #             # send_verification_code(message, phone_number, url)
    #             return Response({'message': 'Visit confirmed and user notified.'}, status=status.HTTP_200_OK)

    #         elif action == 'reject':
    #             visit.status = 'rejected'
    #             visit.save()
    #             # visiting_user = visit.user
    #             # real_user: User = User.objects.filter(user=visiting_user).first()
    #             # send_visit_notification(visit.user.pk, 'نوبت شما به علت نبود وقت رد شد.') # TODO: Uncomment the notification function
    #             phone_number = visit.user.phone_number
    #             sms_for_result_of_appointment(phone_number, 'رد', visit_id)     # TODO: UNcomment this function
    #             message = "نوبت شما به علت نبود وقت رد شد."
    #             url = ""
    #             # send_verification_code(message, phone_number, url)
    #             return Response({'message': 'Visit rejected and user notified.'}, status=status.HTTP_200_OK)

    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserVisitAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        visits = VisitingTimeModel.objects.filter(user=user).all().order_by('-suggested_date')
        if visits:
            serializer = PaymentsSerializer(visits, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_404_NOT_FOUND)


class PaymentHandlingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, visit_id):
        user = request.user
        visit = VisitingTimeModel.objects.filter(pk=visit_id, status='waiting for deposit').first()
        if visit:
            serializer = PaymentSerializer(visit)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def post(self, request, visit_id):
        visit = get_object_or_404(VisitingTimeModel, id=visit_id, status='waiting for deposit')
        user = request.user
        serializer = DiscountSerializer(data=request.data)
        if visit.user != user:
            return Response({'error': 'You do not have permission to make this payment.'}, status=status.HTTP_403_FORBIDDEN)
        if timezone.now() > visit.payment_due_time:
            visit.status = 'deleted'
            visit.save()
            return Response({'message': 'Visit deleted due to payment timeout.'}, status=status.HTTP_200_OK)
        if serializer.is_valid():
            discount_code = serializer.validated_data['discount_code']
            discount = get_object_or_404(DiscountModel, discount_code=discount_code)
            if discount:
                if discount.end_date < datetime.now() or discount.start_date > datetime.now():
                    return Response(status=status.HTTP_400_BAD_REQUEST)
                else:
                    price = visit.price
                    discount_percentage = discount.percentage
                    main_price = price - ((price * discount_percentage) / 100)
                    visit.price = main_price
                    visit.save()
        # Todo: handling the payment gateway
        visit.status = 'confirmed'
        visit.save()
        # TODO: Uncomment this section
        # send_visit_notification(visit.user.pk, 'بیعانه پرداخت شد.')
        # send_visit_notification(visit.saloon.saloon.pk, 'بیعانه پرداخت شد.')
        # send_visit_notification(visit.artist.artist.pk, 'بیعانه پرداخت شد.')
        sms_for_deposit_paid(visit.saloon.saloon.phone_number, visit.user.first_name, visit_id)
        sms_for_deposit_paid(visit.artist.artist.phone_number, visit.user.first_name, visit_id)
        message = "بیعانه پرداخت شد."
        if visit.saloon:
            phone_number = visit.saloon.saloon.phone_number
        else:
            phone_number = visit.artist.artist.phone_number
        url = f"http://127.0.0.1:8000/service/visits/{visit_id}/payment/"
        # send_verification_code(message, phone_number, url)

        return Response({'message': 'Payment received. Visiting time confirmed.'}, status=status.HTTP_200_OK)


class PayingDepositAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, visit_id):
        user = request.user
        visit = get_object_or_404(VisitingTimeModel, id=visit_id, user=user, status='waiting for deposit')
        if visit.user != user:
            return Response({'error': 'You do not have permission to make this payment.'}, status=status.HTTP_403_FORBIDDEN)
        if timezone.now() > visit.payment_due_time:
            visit.status = 'deleted'
            visit.save()
            return Response({'message': 'Visit deleted due to payment timeout.'}, status=status.HTTP_200_OK)
        
        price = visit.price
        # TODO: handling the payment gateway
        visit.status = 'confirmed'
        visit.save()
        # TODO: UNcomment this section
        # send_visit_notification(visit.user.pk, 'نوبت شما تایید شد.')
        # send_visit_notification(visit.artist.artist.pk, 'بیعانه پرداخت شد. ')
        # send_visit_notification(visit.saloon.saloon.pk, 'بیعانه پرداخت شد. ')
        message = "بیعانه پرداخت شد."
        if visit.saloon:
            phone_number = visit.saloon.saloon.phone_number
        else:
            phone_number = visit.artist.artist.phone_number
        url = f"http://127.0.0.1:8000/service/visits/{visit_id}/payment/"
        sms_for_deposit_paid(phone_number, customer=visit.user.first_name, appointmet_id=visit.id)
        return Response({'message': 'Payment received. Visiting time confirmed.'}, status=status.HTTP_200_OK)


class GradeNotificationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, visit_id):
        visit = get_object_or_404(VisitingTimeModel, id=visit_id, status='confirmed')
        supservice = UserServicesModel.objects.filter(artist=visit.artist, supservice=visit.service).first()
        user = request.user

        if visit.user != user:
            return Response({'error': 'You do not have permission to grade this visit.'}, status=status.HTTP_403_FORBIDDEN)
        # todo: why it isn't working : because I made up some random time now It's working.
        if timezone.now() < visit.exact_time + timezone.timedelta(minutes=supservice.suggested_time):
            return Response({'error': 'Grading is only available 1 hour after the visiting time.'}, status=status.HTTP_400_BAD_REQUEST)
        message = "برای امتیاز دهی به نوبت به لینک زیر وارد شوید."
        # send_visit_notification(visit.user.pk, message)   # TODO: Uncomment this section
        if visit.saloon:
            phone_number = visit.saloon.saloon.phone_number
        else:
            phone_number = visit.artist.artist.phone_number
        url = "http://127.0.0.1:8000/service/visits/grade/"
        # send_verification_code(message, phone_number, url)
        return Response({'message': 'Notification sent. Please grade your visit.'}, status=status.HTTP_200_OK)


class ChangeConfirmedToCompleted(APIView):
    def get(self, request):
        current_time = jdatetime.datetime.now().togregorian()
        current_time = timezone.make_aware(current_time)

        user = request.user
        visits = VisitingTimeModel.objects.filter(user=user, status='confirmed').all()
        if visits:
            for visit in visits:
                service_obj = UserServicesModel.objects.filter(supservice=visit.service).first()
                if service_obj:
                    service_time = service_obj.suggested_time
                    visit_end_time = visit.exact_time + timedelta(minutes=service_time)

                    if timezone.is_naive(visit_end_time):
                        visit_end_time = timezone.make_aware(visit_end_time)

                    if visit_end_time < current_time:
                        visit.status = 'completed'
                        visit.save()

            return Response({'message': 'visits status changed.'}, status=status.HTTP_200_OK)

        return Response(status=status.HTTP_400_BAD_REQUEST)


class ChangeWaitingForDepositToRejectedByArtistOrSaloon(APIView):
    def get(self, request):
        current_time = jdatetime.datetime.now().togregorian()
        current_time = timezone.make_aware(current_time)

        user = request.user

        if hasattr(user, 'saloon'):
            visits = VisitingTimeModel.objects.filter(saloon=user.saloon.pk, status='waiting for deposit')
        elif hasattr(user, 'artist'):
            visits = VisitingTimeModel.objects.filter(artist=user.artist.pk, status='waiting for deposit')
        else:
            return Response({'message': 'User type not recognized.'}, status=status.HTTP_400_BAD_REQUEST)

        if visits.exists():
            for visit in visits:
                if timezone.is_naive(visit.payment_due_time):
                    visit.payment_due_time = timezone.make_aware(visit.payment_due_time)

                if visit.payment_due_time < current_time:
                    visit.status = 'rejected'
                    visit.save()

            return Response({'message': 'Visits status changed.'}, status=status.HTTP_200_OK)

        return Response({'message': 'No matching visits found.'}, status=status.HTTP_400_BAD_REQUEST)



class ChangeWaitingForDepositToRejectedByUser(APIView):
    def get(self, request):
        current_time = jdatetime.datetime.now().togregorian()
        current_time = timezone.make_aware(current_time)

        user = request.user
        visits = VisitingTimeModel.objects.filter(user=user, status='waiting for deposit')

        if visits.exists():
            for visit in visits:
                if timezone.is_naive(visit.payment_due_time):
                    visit.payment_due_time = timezone.make_aware(visit.payment_due_time)

                if visit.payment_due_time < current_time:
                    visit.status = 'rejected'
                    visit.save()

            return Response({'message': 'Visits status changed.'}, status=status.HTTP_200_OK)

        return Response({'message': 'No matching visits found.'}, status=status.HTTP_400_BAD_REQUEST)


class GradingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        visits = VisitingTimeModel.objects.filter(user=user, status='completed').all()
        if visits:
            serializer = CommentVisitingSerializer(visits, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def post(self, request, visit_id):
        time = jdatetime.datetime.now()
        user = request.user
        visit = VisitingTimeModel.objects.filter(id=visit_id, user=user, status='completed').first()
        if not visit:
            return Response({"error": "No confirmed visit found"}, status=status.HTTP_404_NOT_FOUND)

        rank_value = request.data.get('rank', None)
        text_value = request.data.get('text', None)

        if rank_value is None:
            return Response({"error": "Rank is required"}, status=status.HTTP_400_BAD_REQUEST)

        # The data needs to be prepared for update
        data = {'rank': rank_value, 'text': text_value}
        serializer = CommentVisitingSerializer(visit, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FilterSaloonAPIView(APIView):
    def get(self, request):
        serializer = FilterSaloonSerializer()
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = FilterSaloonSerializer(data=request.data)
        if serializer.is_valid():
            saloon_name = serializer.data.get('saloon_name')
            service = serializer.data.get('service')
            if saloon_name and service:
                # TODO needs to be handeled on the filter area
                artists = UserServicesModel.objects.filter(supservice__service__service_name_en=service).values_list('artist', flat=True)
                saloons = ArtistModel.objects.filter(id__in=artists).values_list('saloon_artists', flat=True).distinct()
                filtered_saloons = SaloonModel.objects.filter(name__icontains=saloon_name, id__in=saloons).all()
                saloon_serializer = SaloonVisitsSerializer(filtered_saloons, many=True, context={'request': request})
                return Response(saloon_serializer.data, status=status.HTTP_200_OK)
            elif service == None and saloon_name == None:
                saloons = SaloonModel.objects.all()
                saloon_serializer = SaloonVisitsSerializer(saloons, many=True, context={'request': request})
                return Response(saloon_serializer.data, status=status.HTTP_200_OK)
            elif saloon_name and service == None:
                saloons = SaloonModel.objects.filter(name__icontains=saloon_name).all()
                saloon_serializer = SaloonVisitsSerializer(saloons, many=True, context={'request': request})
                return Response(saloon_serializer.data, status=status.HTTP_200_OK)
            elif service and saloon_name == None:
                artists = UserServicesModel.objects.filter(supservice__service__service_name_en=service).values_list('artist', flat=True)
                saloons = ArtistModel.objects.filter(id__in=artists).values_list('saloon_artists', flat=True).distinct()
                filtered_saloon = SaloonModel.objects.filter(id__in=saloons).all()
                saloon_serializer = SaloonVisitsSerializer(filtered_saloon, many=True, context={'request': request})
                return Response(saloon_serializer.data, status=status.HTTP_200_OK)
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FilterArtistAPIView(APIView):
    def get(self, request):
        serializer = FilterArtisitSerializer()
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = FilterArtisitSerializer(data=request.data)
        if serializer.is_valid():
            artist_name = serializer.data.get('artist_name')
            service = serializer.data.get('service')
            if artist_name and service:
                artists_ids = UserServicesModel.objects.filter(supservice__service__service_name_en=service).values_list('artist', flat=True).distinct()
                artists = ArtistModel.objects.filter(artist__first_name__icontains=artist_name, id__in=artists_ids).distinct()
                artist_serializer = ArtistVisitsSerializer(artists, many=True, context={'request': request})
                return Response(artist_serializer.data, status=status.HTTP_200_OK)
            elif artist_name and service == None:
                artists = ArtistModel.objects.filter(artist__first_name__icontains=artist_name).all()
                artist_serializer = ArtistVisitsSerializer(artists, many=True, context={'request': request})
                return Response(artist_serializer.data, status=status.HTTP_200_OK)
            elif artist_name == None and service == None:
                artists = ArtistModel.objects.all()
                artist_serializer = ArtistVisitsSerializer(artists, many=True, context={'request': request})
                return Response(artist_serializer.data, status=status.HTTP_200_OK)
            elif service and artist_name == None:
                artists_ids = UserServicesModel.objects.filter(supservice__service__service_name_en=service).values_list('artist', flat=True).distinct()
                artsits = ArtistModel.objects.filter(id__in=artists_ids).all()
                artist_serializer = ArtistVisitsSerializer(artsits, many=True, context={'request': request})
                return Response(artist_serializer.data, status=status.HTTP_200_OK)
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WalletAPIView(APIView):
    def get(self, request):
        user = request.user
        user_wallet = WalletModel.objects.filter(user=user).first()
        serializer = WalletSerializer(user_wallet)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def post(self, request):
        user = request.user
        amount = request.data.get('amount')

        if not amount or amount <= 0:
            return Response({'error': 'A valid amount is required.'}, status=status.HTTP_400_BAD_REQUEST)

        wallet, created = WalletModel.objects.get_or_create(user=user)

        # Here we would normally handle the payment process
        # For now, we'll just add the amount to the wallet
        wallet.amount += amount
        wallet.save()

        serializer = WalletSerializer(wallet)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DiscountsAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Retrieve all discount entries
        discounts = DiscountModel.objects.all()
        serializer = DiscountSerializer(discounts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        # Create a new discount entry
        serializer = DiscountSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class TagView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        if hasattr(user, 'artist') or hasattr(user, 'saloon'):
            serializer = TagsModelSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
