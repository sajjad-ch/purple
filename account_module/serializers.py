from rest_framework import serializers
from services_module.models import UserServicesModel, VisitingTimeModel, HighlightModel
from .models import User, NormalUserModel, SaloonModel, ArtistModel
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import re, json
from rest_framework_simplejwt.tokens import RefreshToken
from django.urls import reverse
from services_module.serializers import PostSerializerGet, HighlightSerializerGet
from account_module.models import *
import jdatetime


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    phone_number = serializers.CharField()

    def validate_phone_number(self, value):
        if not re.match(r'^09\d{9}$', value):
            raise serializers.ValidationError("Phone number must be exactly 11 digits and start with '09'.")
        return value

    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        user = User.objects.filter(phone_number=phone_number).first()

        if user and user.is_active:
            refresh = RefreshToken.for_user(user)
            return {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'phone_number': user.phone_number,
                }
            }
        else:
            raise serializers.ValidationError('Invalid phone number or the user is not active.')


class SignUpSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=11)

    def validate_phone_number(self, value):
        if not re.match(r'^09\d{9}$', value):
            raise serializers.ValidationError("Phone number must be exactly 11 digits and start with '09'.")
        return value


class KeySerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=11)
    key = serializers.CharField(max_length=6)

    def validate_phone_number(self, value):
        if not re.match(r'^09\d{9}$', value):
            raise serializers.ValidationError("Phone number must be exactly 11 digits and start with '09'.")
        return value


class FollowSerializer(serializers.Serializer):
    followed_user_id = serializers.IntegerField()

    def validate_followed_user_id(self, value):
        try:
            followed_user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")
        return value


class NormalUserSerializer(serializers.ModelSerializer):
    following_count = serializers.SerializerMethodField()

    class Meta:
        model = NormalUserModel
        fields = ['interests', 'following_count']

    def get_following_count(self, obj):
        return obj.get_following_count()


class SaloonSerializer(serializers.ModelSerializer):
    follower_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()

    class Meta:
        model = SaloonModel
        fields = ['id', 'name', 'management', 'follower_count', 'following_count', 'address', 'saloon_profile_picture']

    def get_follower_count(self, obj):
        return obj.get_follower_count()

    def get_following_count(self, obj):
        return obj.get_following_count()


class ArtistSerializer(serializers.ModelSerializer):
    follower_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()

    class Meta:
        model = ArtistModel
        fields = ['years_of_work', 'places_worked', 'saloon_artists', 'following_count', 'follower_count', 'address']

    def get_following_count(self, obj):
        return obj.get_following_count()

    def get_follower_count(self, obj):
        return obj.get_follower_count()


class ProfileSerializer(serializers.ModelSerializer):
    normal_user = NormalUserSerializer(read_only=True, required=False)
    saloon = SaloonSerializer(read_only=True, required=False)
    artist = ArtistSerializer(read_only=True, required=False)
    posts = PostSerializerGet(many=True, read_only=True)
    average_ranks = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'username', 'phone_number', 'age', 'profile_picture',
            'normal_user', 'saloon', 'artist', 'average_ranks', 'posts', 'city', 'birth_date'
        ]


    def get_average_ranks(self, user):
        if hasattr(user, 'saloon'):
            saloon = SaloonModel.objects.filter(saloon=user).first()
            artists = ArtistModel.objects.filter(saloon_artists=saloon).values_list('artist', flat=True) 
            services = UserServicesModel.objects.filter(artist__in=artists).all()

            average_ranks = {}
            total_sum = 0
            total_count = 0

            for service in services:
                visits = VisitingTimeModel.objects.filter(saloon=user.saloon).all()
                ranks = [visit.rank.rank for visit in visits if visit.rank is not None]
                if ranks:
                    avg_rank = sum(ranks) / len(ranks)
                else:
                    avg_rank = 0

                average_ranks[str(service.supservice)] = avg_rank
                total_sum += avg_rank
                total_count += 1

                total_average = total_sum / total_count if total_count > 0 else 0

                # Add total_average to the result dictionary
                average_ranks['total_average'] = total_average
                
            return average_ranks

        if hasattr(user, 'artist'):
            services = UserServicesModel.objects.filter(artist=user.artist).all()

            average_ranks = {}
            total_sum = 0
            total_count = 0

            for service in services:
                # Fetch all visiting times for the user and service
                visits = VisitingTimeModel.objects.filter(artist=user.artist).all()
                # Extract rank values
                ranks = [visit.rank.rank for visit in visits if visit.rank is not None]
                # Calculate average rank
                if ranks:
                    avg_rank = sum(ranks) / len(ranks)
                else:
                    avg_rank = 0

                average_ranks[str(service.supservice)] = avg_rank

                total_sum += avg_rank
                total_count += 1

                total_average = total_sum / total_count if total_count > 0 else 0

                # Add total_average to the result dictionary
                average_ranks['total_average'] = total_average

            return average_ranks
        return None


class SaloonProfileSerializer(serializers.ModelSerializer):
    average_ranks = serializers.SerializerMethodField()
    ranks = serializers.SerializerMethodField()
    follow_url = serializers.SerializerMethodField()
    unfollow_url = serializers.SerializerMethodField()
    highlights = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    follower_count = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    phone_number_for_chat = serializers.SerializerMethodField()

    class Meta:
        model = SaloonModel
        fields = "__all__"

    def get_phone_number_for_chat(self, obj):
        return obj.saloon.phone_number

    def get_highlights(self, obj):
        highlishts = HighlightModel.objects.filter(user=obj.saloon_id)
        serialized_highlights = HighlightSerializerGet(highlishts, many=True)
        return serialized_highlights.data

    def get_follow_url(self, obj):
        request = self.context.get('request')
        path = reverse('follow', kwargs={'user_id': obj.saloon_id})
        return request.build_absolute_uri(path)

    def get_unfollow_url(self, obj):
        request = self.context.get('request')
        path = reverse('follow', kwargs={'user_id': obj.saloon_id})
        return request.build_absolute_uri(path)

    def get_profile_picture(self, obj):
        return obj.saloon.profile_picture.url

    def get_follower_count(self, obj):
        return obj.get_follower_count()

    def get_comments(self, obj):
        comments = []
        visits = VisitingTimeModel.objects.filter(saloon=obj, rank__isnull=False).all()
        for visit in visits:
            comments.append({'commenter': visit.user.first_name + ' ' + visit.user.last_name if visit.user else '',
                              'commenter_profile_picture': visit.user.profile_picture.url if visit.user else '',
                              'comment': visit.text if visit.text else '',
                              'rate': visit.rank.rank if visit.rank else 0,
                              'service': visit.service.service.service_name_fa if visit.service else ''})
        return comments

    def get_average_ranks(self, user):
        if hasattr(user, 'saloon'):
            services = UserServicesModel.objects.filter(artist__saloon_artists=user).all()
            average_ranks = {}
            total_sum = 0
            total_count = 0

            for service in services:
                visits = VisitingTimeModel.objects.filter(saloon=user).all()

                ranks = [visit.rank.rank for visit in visits if visit.rank is not None]
                if ranks:
                    avg_rank = sum(ranks) / len(ranks)
                else:
                    avg_rank = 0

                average_ranks[str(service.supservice)] = avg_rank

                # Accumulate the total sum and count for calculating the overall average
                total_sum += avg_rank
                total_count += 1

                total_average = total_sum / total_count if total_count > 0 else 0

                # Add total_average to the result dictionary
                average_ranks['total_average'] = total_average

            return average_ranks
        return None

    def get_ranks(self, obj):
        visits = VisitingTimeModel.objects.filter(saloon=obj).all()
        return [{"rank": visit.rank.rank, "text": visit.text} for visit in visits if visit.rank is not None]


class ArtistProfileSerializer(serializers.ModelSerializer):
    artist_name = serializers.SerializerMethodField()
    average_ranks = serializers.SerializerMethodField()
    ranks = serializers.SerializerMethodField()
    follow_url = serializers.SerializerMethodField()
    unfollow_url = serializers.SerializerMethodField()
    highlights = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    follower_count = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    active = serializers.SerializerMethodField()
    supservices = serializers.SerializerMethodField()
    phone_number_for_chat = serializers.SerializerMethodField()


    class Meta:
        model = ArtistModel
        fields = "__all__"
    
    def get_active(self, obj):
        time = jdatetime.datetime.now()
        visits = VisitingTimeModel.objects.filter(artist=obj,
                                                  exact_time__gt=jdatetime.datetime(time.year, time.month, time.day),
                                                  exact_time__lt=jdatetime.datetime(time.year, time.month, time.day, 23, 59)).all()
        if visits:
            return True
        else:
            return False

    def get_supservices(self, obj):
        skills = []
        artist_services = UserServicesModel.objects.filter(artist=obj).all()
        for service in artist_services:
            skills.append(service.supservice.supservice_name_fa)
        return skills

    def get_phone_number_for_chat(self, obj):
        return obj.artist.phone_number

    def get_artist_name(self, obj):
        return obj.artist.first_name + ' ' + obj.artist.last_name

    def get_highlights(self, obj):
        highlishts = HighlightModel.objects.filter(user=obj.artist_id)
        serialized_highlights = HighlightSerializerGet(highlishts, many=True)
        return serialized_highlights.data

    def get_follow_url(self, obj):
        request = self.context.get('request')
        path = reverse('follow', kwargs={'user_id': obj.artist_id})
        return request.build_absolute_uri(path)

    def get_unfollow_url(self, obj):
        request = self.context.get('request')
        path = reverse('follow', kwargs={'user_id': obj.artist_id})
        return request.build_absolute_uri(path)

    def get_profile_picture(self, obj):
        return obj.artist.profile_picture.url

    def get_follower_count(self, obj):
        return obj.get_follower_count()

    def get_comments(self, obj):
        comments = []
        visits = VisitingTimeModel.objects.filter(artist=obj, rank__isnull=True).all()
        for visit in visits:
            comments.append({'commenter': visit.user.first_name + ' ' + visit.user.last_name if visit.user else '',
                             'commenter_profile_picture': visit.user.profile_picture.url if visit.user else '',
                             'comment': visit.text if visit.text else '',
                             'rate': visit.rank.rank if visit.rank else 0,
                             'service': visit.service.service.service_name_fa if visit.service else ''})
        return comments

    def get_average_ranks(self, user):
        if hasattr(user, 'artist'):
            services = UserServicesModel.objects.filter(artist__artist_id=user.artist).all()

            average_ranks = {}
            total_sum = 0
            total_count = 0

            for service in services:
                visits = VisitingTimeModel.objects.filter(artist=user).all()
                ranks = [visit.rank.rank for visit in visits if visit.rank is not None]

                if ranks:
                    avg_rank = sum(ranks) / len(ranks)
                else:
                    avg_rank = 0

                average_ranks[str(service.supservice)] = avg_rank

                # Accumulate the total sum and count for calculating the overall average
                total_sum += avg_rank
                total_count += 1

            # Calculate the total average
            total_average = total_sum / total_count if total_count > 0 else 0

            # Add total_average to the result dictionary
            average_ranks['total_average'] = total_average

            return average_ranks

        return None

    def get_ranks(self, obj):
        visits = VisitingTimeModel.objects.filter(artist=obj).all()
        return [{"rank": visit.rank.rank, "text": visit.text} for visit in visits if visit.rank is not None]


class NormalUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NormalUserModel
        fields = ['interests']


class SaloonUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaloonModel
        fields = ['name', 'management', 'address', 'saloon_profile_picture']


class ArtistUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtistModel
        fields = ['years_of_work', 'places_worked', 'address']


class ProfileUpdateSerializer(serializers.ModelSerializer):
    normal_user = NormalUserUpdateSerializer(required=False)
    saloon = SaloonUpdateSerializer(required=False)
    artist = ArtistUpdateSerializer(required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'age', 'profile_picture', 'normal_user', 'saloon', 'artist', 'city', 'birth_date']

    def update(self, instance, validated_data):
        # Update User fields
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.username = validated_data.get('username', instance.username)
        instance.age = validated_data.get('age', instance.age)
        instance.city = validated_data.get('city', instance.city)
        instance.birth_date = validated_data.get('birth_date', instance.birth_date)
        instance.profile_picture = validated_data.get('profile_picture', instance.profile_picture)
        instance.save()

        # Update NormalUserModel fields if exists
        normal_user_data = validated_data.get('normal_user')
        if normal_user_data and hasattr(instance, 'normal_user'):
            normal_user = instance.normal_user
            normal_user.interests = normal_user_data.get('interests', normal_user.interests)
            normal_user.save()

        # Update SaloonModel fields if exists
        saloon_data = validated_data.get('saloon')
        if saloon_data and hasattr(instance, 'saloon'):
            saloon = instance.saloon
            saloon.name = saloon_data.get('name', saloon.name)
            saloon.management = saloon_data.get('management', saloon.management)
            saloon.saloon_profile_picture = saloon_data.get('saloon_profile_picture', saloon.saloon_profile_picture)
            saloon.save()

        # Update ArtistModel fields if exists
        artist_data = validated_data.get('artist')
        if artist_data and hasattr(instance, 'artist'):
            artist = instance.artist
            # artist.expertise = artist_data.get('expertise', artist.expertise)
            artist.years_of_work = artist_data.get('years_of_work', artist.years_of_work)
            artist.places_worked = artist_data.get('places_worked', artist.places_worked)
            artist.saloon_artists = artist_data.get('saloon_artists', artist.saloon_artists)
            artist.save()

        return instance


class UserSerializerChat(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'profile_picture']