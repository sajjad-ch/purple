from rest_framework import serializers
from services_module.models import UserServicesModel, VisitingTimeModel
from .models import User, NormalUserModel, SaloonModel, ArtistModel
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import re
from rest_framework_simplejwt.tokens import RefreshToken
from django.urls import reverse
from services_module.serializers import PostSerializerGet


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


# class ProfileSerializer(serializers.ModelSerializer):
#     phone_number = serializers.CharField(max_length=11)
#     follower_count = serializers.SerializerMethodField()
#     following_count = serializers.SerializerMethodField()
#
#     class Meta:
#         model = User
#         fields = ['first_name', 'last_name', 'username', 'phone_number', 'age', 'profile_picture', 'follower_count', 'following_count']
#
#     def validate_phone_number(self, value):
#         if not re.match(r'^09\d{9}$', value):
#             raise serializers.ValidationError("Phone number must be exactly 11 digits and start with '09'.")
#         return value
#
#     def get_follower_count(self, obj):
#         if hasattr(obj, 'normal_user'):
#             return 0
#         normal_followers = NormalUserFollow.objects.filter(followed_user=obj).count()
#         saloon_followers = SaloonFollow.objects.filter(followed_user=obj).count()
#         artist_followers = ArtistFollow.objects.filter(followed_user=obj).count()
#         return normal_followers + saloon_followers + artist_followers
#
#     def get_following_count(self, obj):
#         # Aggregate followings from all follow models
#         if hasattr(obj, 'saloon'):
#             normal_following = NormalUserFollow.objects.filter(followed_user=obj.saloon).count()
#             saloon_following = SaloonFollow.objects.filter(followed_user=obj.saloon).count()
#             artist_following = ArtistFollow.objects.filter(followed_user=obj.saloon).count()
#             return normal_following + saloon_following + artist_following
#
#         elif hasattr(obj, 'artist'):
#             normal_following = NormalUserFollow.objects.filter(followed_user=obj.artist).count()
#             saloon_following = SaloonFollow.objects.filter(followed_user=obj.artist).count()
#             artist_following = ArtistFollow.objects.filter(followed_user=obj.artist).count()
#             return normal_following + saloon_following + artist_following
#
#         elif hasattr(obj, 'normal_user'):
#             return 0


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
        fields = ['name', 'management', 'follower_count', 'following_count', 'address']

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
            'normal_user', 'saloon', 'artist', 'average_ranks', 'posts'
        ]

    # def get_posts(self, user):
    #     if hasattr(user, 'saloon'):
    #         posts = PostModel.objects.filter(user=user).all()
    #         return posts
    #     if hasattr(user, 'artist'):
    #         posts = PostModel.objects.filter(user=user).all()
    #         return posts
    #     return None

    def get_average_ranks(self, user):
        if hasattr(user, 'saloon'):
            services = UserServicesModel.objects.filter(saloon=user.saloon).all()

            average_ranks = {}

            for service in services:
                visits = VisitingTimeModel.objects.filter(saloon=user.saloon).all()
                for visit in visits:
                    print(visit)
                ranks = [visit.rank.rank for visit in visits if visit.rank is not None]
                if ranks:
                    avg_rank = sum(ranks) / len(ranks)
                else:
                    avg_rank = 0

                average_ranks[service.service_name] = avg_rank

            return average_ranks

        if hasattr(user, 'artist'):
            services = UserServicesModel.objects.filter(artist=user.artist).all()

            average_ranks = {}

            for service in services:
                # Fetch all visiting times for the user and service
                visits = VisitingTimeModel.objects.filter(artist=user.artist).all()
                for visit in visits:
                    print(visit)
                # Extract rank values
                ranks = [visit.rank.rank for visit in visits if visit.rank is not None]
                # Calculate average rank
                if ranks:
                    avg_rank = sum(ranks) / len(ranks)
                else:
                    avg_rank = 0

                average_ranks[str(service.service)] = avg_rank

            return average_ranks
        return None


class SaloonProfileSerializer(serializers.ModelSerializer):
    average_ranks = serializers.SerializerMethodField()
    ranks = serializers.SerializerMethodField()
    follow_url = serializers.SerializerMethodField()
    unfollow_url = serializers.SerializerMethodField()

    class Meta:
        model = SaloonModel
        fields = "__all__"

    def get_follow_url(self, obj):
        request = self.context.get('request')
        path = reverse('follow', kwargs={'user_id': obj.saloon_id})
        return request.build_absolute_uri(path)

    def get_unfollow_url(self, obj):
        request = self.context.get('request')
        path = reverse('follow', kwargs={'user_id': obj.saloon_id})
        return request.build_absolute_uri(path)

    def get_average_ranks(self, user):
        if hasattr(user, 'saloon'):
            services = UserServicesModel.objects.filter(saloon__saloon_id=user.saloon).all()

            average_ranks = {}
            total_sum = 0
            total_count = 0

            for service in services:
                visits = VisitingTimeModel.objects.filter(saloon=user).all()
                for visit in visits:
                    print(visit)
                ranks = [visit.rank.rank for visit in visits if visit.rank is not None]
                if ranks:
                    avg_rank = sum(ranks) / len(ranks)
                else:
                    avg_rank = 0

                average_ranks[str(service.service)] = avg_rank

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
    average_ranks = serializers.SerializerMethodField()
    ranks = serializers.SerializerMethodField()
    follow_url = serializers.SerializerMethodField()
    unfollow_url = serializers.SerializerMethodField()

    class Meta:
        model = ArtistModel
        fields = "__all__"

    def get_follow_url(self, obj):
        request = self.context.get('request')
        path = reverse('follow', kwargs={'user_id': obj.artist_id})
        return request.build_absolute_uri(path)

    def get_unfollow_url(self, obj):
        request = self.context.get('request')
        path = reverse('follow', kwargs={'user_id': obj.artist_id})
        return request.build_absolute_uri(path)

    def get_average_ranks(self, user):
        if hasattr(user, 'saloon'):
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

                average_ranks[str(service.service)] = avg_rank

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
        fields = ['name', 'management', 'address']


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
        fields = ['first_name', 'last_name', 'username', 'phone_number', 'age', 'profile_picture', 'normal_user', 'saloon', 'artist']

    def update(self, instance, validated_data):
        # Update User fields
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.username = validated_data.get('username', instance.username)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.age = validated_data.get('age', instance.age)
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
        fields = ['username']