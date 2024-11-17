from django.contrib.auth.models import AbstractUser, Group, Permission
from datetime import datetime
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from .utils import random_code


class AccountManager(BaseUserManager):
    def create_user(self, phone_number, username, password=None):
        if not phone_number:
            raise ValidationError('برای ثبت نام شماره همراه راوارد کنید')

        user = self.model(
            phone_number=phone_number,
            username=username
        )
        user.is_active = False
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, username=None, password=None):
        user = self.create_user(
            phone_number=phone_number,
            username=username,
            password=password
        )
        user.is_staff = True
        user.is_active = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractUser):
    username = models.CharField(unique=True, max_length=10, verbose_name='کد ملی', null=True, blank=True)
    phone_number = models.CharField(unique=True, max_length=11, verbose_name='شماره همراه')
    key = models.CharField(max_length=6, blank=True, null=True)
    code_generated_at = models.DateTimeField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='Images/', default='default/avatar.jpg/')
    last_login = models.DateTimeField(null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)

    groups = models.ManyToManyField(
        Group,
        related_name='persons_set',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='persons_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

    objects = AccountManager()
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def generate_verification_code(self):
        self.key = random_code()
        self.code_generated_at = datetime.now()
        self.save()


class NormalUserModel(models.Model):
    normal_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='normal_user')
    interests = models.TextField(verbose_name='علایق')

    class Meta:
        verbose_name = 'کاربر عادی'
        verbose_name_plural = 'کاربران عادی'

    def __str__(self):
        return f"{self.normal_user}"

    def get_following_count(self):
        return NormalUserFollow.objects.filter(follower=self).count()


class SaloonModel(models.Model):
    saloon = models.OneToOneField(User, on_delete=models.CASCADE, related_name='saloon')
    name = models.CharField(max_length=255, verbose_name='نام سالن')
    management = models.CharField(max_length=255, verbose_name='مدیریت')
    address = models.CharField(max_length=255, verbose_name='آدرس')

    class Meta:
        verbose_name = 'سالن'
        verbose_name_plural = 'سالن‌ها'

    def __str__(self):
        return f"{self.saloon}"

    def get_follower_count(self):
        return (
                ArtistFollow.objects.filter(followed_user=self.saloon.pk).count() +
                SaloonFollow.objects.filter(followed_user=self.saloon.pk).count() +
                NormalUserFollow.objects.filter(followed_user=self.saloon.pk).count()
        )

    def get_following_count(self):
        return SaloonFollow.objects.filter(follower=self).count()


class ArtistModel(models.Model):
    artist = models.OneToOneField(User, on_delete=models.CASCADE, related_name='artist')
    years_of_work = models.PositiveIntegerField(verbose_name='سال‌های کار')
    places_worked = models.TextField(verbose_name='مکان‌های کار')
    saloon_artists = models.ForeignKey(SaloonModel, on_delete=models.CASCADE, verbose_name='محل کار')
    address = models.CharField(max_length=255, verbose_name='آدرس')

    class Meta:
        verbose_name = 'هنرمند'
        verbose_name_plural = 'هنرمندان'

    def __str__(self):
        return f"{self.artist}"

    def get_follower_count(self):
        return (
                ArtistFollow.objects.filter(followed_user=self.artist.pk).count() +
                SaloonFollow.objects.filter(followed_user=self.artist.pk).count() +
                NormalUserFollow.objects.filter(followed_user=self.artist.pk).count()
        )

    def get_following_count(self):
        return ArtistFollow.objects.filter(follower=self).count()


class NormalUserFollow(models.Model):
    follower = models.ForeignKey(NormalUserModel, related_name='following', on_delete=models.CASCADE)
    followed_user = models.ForeignKey(User, related_name='normal_followers', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'دنبال شونده کاربر عادی'
        verbose_name_plural = 'دنبال شوندگان کاربر عادی'
        unique_together = ('follower', 'followed_user')

    def __str__(self):
        return f"{self.follower.normal_user} follows {self.followed_user}"


class SaloonFollow(models.Model):
    follower = models.ForeignKey(SaloonModel, related_name='following', on_delete=models.CASCADE)
    followed_user = models.ForeignKey(User, related_name='saloon_followers', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'دنبال شونده سالن'
        verbose_name_plural = 'دنبال شوندگان سالن'
        unique_together = ('follower', 'followed_user')

    def __str__(self):
        return f"{self.follower.name} follows {self.followed_user}"


class ArtistFollow(models.Model):
    follower = models.ForeignKey(ArtistModel, related_name='following', on_delete=models.CASCADE)
    followed_user = models.ForeignKey(User, related_name='artist_followers', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'دنبال شونده هنرمند'
        verbose_name_plural = 'دنبال شوندگان هنرمند'
        unique_together = ('follower', 'followed_user')

    def __str__(self):
        return f"{self.follower.artist} follows {self.followed_user}"
