from rest_framework import serializers
from account_module.models import ArtistModel, SaloonModel, User
from .models import *
from django.urls import reverse
from django.utils.timezone import now


class SliderSeralizer(serializers.ModelSerializer):
    class Meta:
        model = SliderModel
        fields = ['slider_picture', 'slider_text', 'url_slider']


class ServiceSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ServiceModel
        fields = ['service_code', 'service_name_en', 'service_name_fa', 'service_icon', 'url']

    def get_url(self, obj):
        request = self.context.get('request')
        path = reverse('service_filter_artist', kwargs={'service_code': obj.service_code})
        return request.build_absolute_uri(path)


class PostSerializerGet(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()
    saloon_profile_picture_post = serializers.SerializerMethodField()

    class Meta:
        model = PostModel
        fields = ['id', 'post_content', 'caption', 'user', 'name', 'profile_picture', 'likes', 'saloon_profile_picture_post']
    
    def get_profile_picture(self, obj):
        profile_picture = obj.user.profile_picture.url
        return profile_picture
    
    def get_saloon_profile_picture_post(self, obj):
        if obj.saloon:
            return obj.saloon.saloon_profile_picture.url

    def get_name(self, obj):
        if hasattr(obj.user, 'artist'):
            return obj.user.first_name + ' ' + obj.user.last_name
        elif hasattr(obj.user, 'saloon'):
            return obj.user.saloon.name

    def get_likes(self, obj):
        return LikeModel.objects.filter(post=obj).count()
        


class PostSerializerPost(serializers.ModelSerializer):
    class Meta:
        model = PostModel
        fields = ['post_content', 'caption', 'saloon']

        def create(self, validated_data):
            validated_data['user'] = self.context['request'].user
            return super().create(validated_data)


class StorySerializerGet(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    saloon_profile_picture_story = serializers.SerializerMethodField()
    class Meta:
        model = StoryModel
        fields = ['story_content', 'name', 'profile_picture', 'saloon_profile_picture_story']

    def get_profile_picture(self, obj):
        profile_picture = obj.user.profile_picture.url
        return profile_picture

    def get_saloon_profile_picture_story(self, obj):
        if obj.saloon:
            return obj.saloon.saloon_profile_picture.url

    def get_name(self, obj):
        first_name = f'{obj.user.first_name} {obj.user.last_name}'
        return first_name

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class StorySerializerPost(serializers.ModelSerializer):
    duration_time = serializers.SerializerMethodField()
    class Meta:
        model = StoryModel
        fields = ['story_content', 'duration_time', 'saloon']

    def get_duration_time(self, obj):
        return self.context.get('duration_time', None)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data.pop('duration_time', None)  
        return super().create(validated_data)


class HighlightSerializerGet(serializers.ModelSerializer):
    saloon_profile_picture_highlight = serializers.SerializerMethodField()
    class Meta:
        model = HighlightModel
        fields = ['highlight_content', 'user', 'created', 'text', 'saloon_profile_picture_highlight']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def get_saloon_profile_picture_highlight(self, obj):
        if obj.saloon:
            return obj.saloon.saloon_profile_picture.url


class HighlightSerializerPost(serializers.ModelSerializer):
    class Meta:
        model = HighlightModel
        fields = ['highlight_content', 'text', 'saloon']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ArtistVisitsSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    artist_name = serializers.SerializerMethodField()
    GetSupservicesFromArtist = serializers.SerializerMethodField()
    profile_url = serializers.SerializerMethodField()
    average_ranks = serializers.SerializerMethodField()
    ranks = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    saloon_name = serializers.SerializerMethodField()

    class Meta:
        model = ArtistModel
        fields = ['id', 'artist', 'artist_name', 'url', 'GetSupservicesFromArtist', 'profile_url', 'average_ranks', 'ranks', 'profile_picture', 'saloon_name']

    def get_artist_name(self, obj):
        return obj.artist.first_name + ' ' + obj.artist.last_name

    def get_GetSupservicesFromArtist(self, obj):
        request = self.context.get('request')
        path = reverse('artist-service', kwargs={'artist_id': obj.id})
        return request.build_absolute_uri(path)

    def get_url(self, obj):
        request = self.context.get('request')
        path = reverse('request-visiting-time-artist', kwargs={'user_id': obj.id})
        return request.build_absolute_uri(path)

    def get_profile_url(self, obj):
        request = self.context.get('request')
        path = reverse('artist-profile', kwargs={'user_id': obj.id})
        return request.build_absolute_uri(path)
    
    def get_profile_picture(self, obj):
        return obj.artist.profile_picture.url

    def get_saloon_name(self, obj):
        return str(obj.saloon_artists)

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

                total_average = total_sum / total_count if total_count > 0 else 0

                # Add total_average to the result dictionary
                average_ranks['total_average'] = total_average

            return average_ranks
        return None

    def get_ranks(self, obj):
        visits = VisitingTimeModel.objects.filter(artist=obj).all()
        return [{"rank": visit.rank.rank, "text": visit.text} for visit in visits if visit.rank is not None]

class SaloonVisitsSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    saloonDetailForArtistAndServices = serializers.SerializerMethodField()
    GetAllServicesFromSaloon = serializers.SerializerMethodField()
    profile_url = serializers.SerializerMethodField()
    average_ranks = serializers.SerializerMethodField()
    ranks = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = SaloonModel
        fields = ['id', 'name', 'management', 'url', 'saloonDetailForArtistAndServices', 'GetAllServicesFromSaloon', 'profile_picture', 'profile_url', 'address', 'saloon_rank', 'average_ranks', 'ranks', 'saloon_profile_picture']

    def get_saloonDetailForArtistAndServices(self, obj):
        request = self.context.get('request')
        path = reverse('saloon-artists', kwargs={'saloon_id': obj.id})
        return request.build_absolute_uri(path)

    def get_GetAllServicesFromSaloon(self, obj):
        request = self.context.get('request')
        path = reverse('saloon-service', kwargs={'saloon_id': obj.id})
        return request.build_absolute_uri(path)

    def get_url(self, obj):
        request = self.context.get('request')
        path = reverse('request-visiting-time-saloon', kwargs={'user_id': obj.id})
        return request.build_absolute_uri(path)

    def get_profile_url(self, obj):
        request = self.context.get('request')
        path = reverse('saloon-profile', kwargs={'user_id': obj.id})
        return request.build_absolute_uri(path)
    
    def get_profile_picture(self, obj):
        return obj.saloon.profile_picture.url

    def get_average_ranks(self, user):
        if hasattr(user, 'saloon'):
            services = UserServicesModel.objects.filter(artist__saloon_artists=user.saloon.id).all()

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

class VisitingTimeSerializerGet(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    saloon_name = serializers.SerializerMethodField()
    artist_name = serializers.SerializerMethodField()
    service_name = serializers.SerializerMethodField()
    name_of_the_user = serializers.SerializerMethodField()
    saloon_address = serializers.SerializerMethodField()

    class Meta:
        model = VisitingTimeModel
        fields = "__all__"

    def get_url(self, obj):
        request = self.context.get('request')
        path = reverse('post_confirm_visit', kwargs={'visit_id': obj.id})
        return request.build_absolute_uri(path)

    def get_saloon_name(self, obj):
        if obj.saloon:
            return obj.saloon.name
    
    def get_artist_name(self, obj):
        if obj.artist != None:
            return obj.artist.artist.first_name + ' ' + obj.artist.artist.last_name
    
    def get_service_name(self, obj):
        if obj.service != None:
            return obj.service.supservice_name_fa

    def get_name_of_the_user(self, obj):
        if obj.user:
            return obj.user.first_name + ' ' + obj.user.last_name
        return obj.unregistered_user.name
    
    def get_saloon_address(self, obj):
        if obj.saloon:
            return obj.saloon.address


class SaloonVisitingTimeSerializerPost(serializers.ModelSerializer):
    saloon = serializers.PrimaryKeyRelatedField(queryset=SaloonModel.objects.all())
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    exact_time = serializers.DateTimeField(required=False, allow_null=True)

    class Meta:
        model = VisitingTimeModel
        fields = ['user', 'saloon', 'artist', 'service', 'suggested_time', 'suggested_date', 'suggested_hour', 'exact_time', 'status']

    def create(self, validated_data):
        validated_data['status'] = 'waiting for confirmation'
        visit = VisitingTimeModel.objects.create(**validated_data)
        return visit


class ArtistVisitingTimeSerializerPost(serializers.ModelSerializer):
    artist = serializers.PrimaryKeyRelatedField(queryset=ArtistModel.objects.all())
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    exact_time = serializers.DateTimeField(required=False, allow_null=True)

    class Meta:
        model = VisitingTimeModel
        fields = ['user', 'artist', 'saloon', 'service', 'suggested_time', 'suggested_hour', 'suggested_date', 'exact_time', 'status']

    def create(self, validated_data):
        validated_data['status'] = 'waiting for confirmation'
        visit = VisitingTimeModel.objects.create(**validated_data)
        return visit


class VisitingTimeSerializerPostNew(serializers.ModelSerializer):
    action = serializers.ChoiceField(choices=[('confirm', 'Confirm'), ('reject', 'Reject')])
    exact_time = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = VisitingTimeModel
        fields = ['action', 'exact_time', 'price', 'suggested_time']

    def validate(self, data):
            if data.get('action') == 'confirm' and not data.get('exact_time'):
                raise serializers.ValidationError({
                    'exact_time': 'This field is required when action is confirm'
                })
            return data



class VisitingTimeSerializerGetNew(serializers.ModelSerializer):

    class Meta:
        model = VisitingTimeModel
        fields = ['user', 'artist', 'saloon', 'service', 'suggested_time', 'suggested_date', 'exact_time', 'status', 'confirmation_time', 'payment_due_time', 'action', 'price']


class PaymentsSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = VisitingTimeModel
        fields = ['user', 'artist', 'saloon', 'service', 'exact_time', 'url', 'price']

    def get_url(self, obj):
        request = self.context.get('request')
        path = reverse('payment-handling', kwargs={'visit_id': obj.id})
        return request.build_absolute_uri(path)


class RankSerializer(serializers.ModelSerializer):
    class Meta:
        model = RankModel
        fields = ['rank']

        def validate_rank(self, value):
            if value < 1 or value > 5:
                raise serializers.ValidationError("Rank must be between 1 and 5.")
            return value


class CommentVisitingSerializer(serializers.ModelSerializer):
    rank = serializers.IntegerField(write_only=True)  # This handles writing the rank as an integer

    class Meta:
        model = VisitingTimeModel
        fields = ['id', 'user', 'artist', 'saloon', 'service', 'exact_time', 'rank', 'text']

    def to_representation(self, instance):
        # This will format the rank as a nested dictionary for GET requests
        representation = super().to_representation(instance)
        if instance.rank:
            representation['rank'] = {'rank': instance.rank.rank}
        else:
            representation['rank'] = None
        return representation

    def update(self, instance, validated_data):
        rank_value = validated_data.pop('rank', None)
        text_value = validated_data.pop('text', None)

        if rank_value is not None:
            if instance.rank:
                user_service = UserServicesModel.objects.filter(supservice=instance.service).first()
                rank = instance.rank
                rank.rank = rank_value
                rank.artist = instance.artist
                rank.saloon = instance.saloon
                rank.service = user_service
                rank.save()
            else:
                user_service = UserServicesModel.objects.filter(supservice=instance.service).first()
                rank = RankModel.objects.create(
                    rank=rank_value,
                    artist=instance.artist,
                    saloon=instance.saloon,
                    service=user_service
                )
                instance.rank = rank

        if text_value is not None:
            instance.text = text_value

        instance.save()
        return instance


class PaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = VisitingTimeModel
        fields = ['price', 'exact_time', 'service']


class FilterSaloonSerializer(serializers.Serializer):
    saloon_name = serializers.CharField(max_length=30, required=False)
    service = serializers.CharField(max_length=30, required=False)


class FilterArtisitSerializer(serializers.Serializer):
    artist_name = serializers.CharField(max_length=30, required=False)
    service = serializers.CharField(max_length=30, required=False)


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletModel
        fields = "__all__"


class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountModel
        fields = "__all__"


class FinancialSummarySerializer(serializers.Serializer):
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    start_price = serializers.CharField(required=False)
    end_price = serializers.CharField(required=False)

    def validate(self, data):
        # Set default values for dates if not provided
        data['start_date'] = data.get('start_date', now())
        data['end_date'] = data.get('end_date', now())

        # Set default values for prices if not provided
        data['start_price'] = data.get('start_price', 0)
        data['end_price'] = data.get('end_price', 1000)

        return data


class ManagingPaymentSerializer(serializers.Serializer):
    days = serializers.IntegerField(min_value=1)


class UserServiceSerializer(serializers.ModelSerializer):
    service_name_fa = serializers.SerializerMethodField()
    service_name_en = serializers.SerializerMethodField()
    supservice_icon = serializers.SerializerMethodField()

    class Meta:
        model = UserServicesModel
        fields = ['supservice', 'service_name_fa', 'service_name_en', 'suggested_time', 'suggested_price', 'supservice_icon']

    def get_supservice_icon(self, obj):
        return obj.supservice.supservice_icon.url

    def get_service_name_fa(self, obj):
        return obj.supservice.supservice_name_fa
    
    def get_service_name_en(self, obj):
        return obj.supservice.supservice_name_en

    def validate(self, data):
        user = self.context['request'].user

        # Ensure that either artist or saloon is set
        if not hasattr(user, 'artist') and not hasattr(user, 'saloon'):
            raise serializers.ValidationError("User must be associated with either an artist or a saloon.")

        # Check if the service is already provided by the user
        if hasattr(user, 'artist'):
            if UserServicesModel.objects.filter(artist=user.artist, service=data['service']).exists():
                raise serializers.ValidationError("This service is already provided by the artist.")
        elif hasattr(user, 'saloon'):
            if UserServicesModel.objects.filter(saloon=user.saloon, service=data['service']).exists():
                raise serializers.ValidationError("This service is already provided by the saloon.")

        return data


class SupServiceSerializer(serializers.ModelSerializer):
    suggested_price = serializers.SerializerMethodField()
    class Meta:
        model = SupServiceModel
        fields = "__all__"
    
    def get_suggested_price(self, obj):
        supservice = UserServicesModel.objects.filter(supservice=obj).first()
        return supservice.suggested_price if supservice else None



class HandigVisitSerializer(serializers.ModelSerializer):

    class Meta:
        model = VisitingTimeModel
        fields = "__all__"


class ManageArtistTeamSerializer(serializers.Serializer):
    artist_id = serializers.IntegerField()

    def validate_artist_id(self, value):
        if not ArtistModel.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Artist does not exist.")
        return value


class TagsModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TagsModel
        fields = "__all__"

    
class SavedPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedPost
        fields = "__all__"