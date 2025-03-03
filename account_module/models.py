from django.contrib.auth.models import AbstractUser, Group, Permission
from datetime import datetime, timedelta
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from .utils import send_verification_code, random_number
from django_jalali.db import models as jmodels

# encryption library
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend 

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
    is_active = models.BooleanField(default=False, verbose_name='فعال / غیرفعال (0/1)')
    key = models.CharField(max_length=6, blank=True, null=True)
    code_generated_at = models.DateTimeField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='Images/', default='Images/avatar.jpg/', null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    city = models.CharField(max_length=128, null=True, blank=True)
    birth_date = jmodels.jDateField(verbose_name='تاریخ تولد', null=True, blank=True)
    public_key = models.TextField(blank=True, null=True)
    private_key = models.TextField(blank=True, null=True)
    status = models.CharField(choices=[('online', 'online'), ('offline', 'offline')], max_length=10, default='offline', blank=True, null=True, verbose_name='آنلاین / آفلاین (0/1)')
    total_active_time = models.DurationField(default=timedelta(0)) 
    last_activity_time = models.DateTimeField(null=True, blank=True)
    bank_account_number = models.CharField(max_length=16, null=True, blank=True)  

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
#        self.key = send_verification_code()
        self.key = random_number()
        self.code_generated_at = datetime.now()
        self.save()
    
    # def generate_keys(self):
    #     private_key = rsa.generate_private_key(
    #         public_exponent=65537,
    #         key_size=2048,
    #         backend=default_backend()
    #     )
    #     public_key = private_key.public_key()

    #     # Serialize keys to store as text
    #     self.private_key = private_key.private_bytes(
    #         encoding=serialization.Encoding.PEM,
    #         format=serialization.PrivateFormat.PKCS8,
    #         encryption_algorithm=serialization.NoEncryption()
    #     ).decode('utf-8')

    #     self.public_key = public_key.public_bytes(
    #         encoding=serialization.Encoding.PEM,
    #         format=serialization.PublicFormat.SubjectPublicKeyInfo
    #     ).decode('utf-8')

    # def save(self, *args, **kwargs):
    #     if not self.private_key or not self.public_key:
    #         self.generate_keys()
    #     super().save(*args, **kwargs)

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

rank_choices = (
    ("A+", "A+"),
    ("A", "A"),
    ("B+", "B+"),
    ("B", "B"),
)
class SaloonModel(models.Model):
    saloon = models.OneToOneField(User, on_delete=models.CASCADE, related_name='saloon')
    name = models.CharField(max_length=255, verbose_name='نام سالن')
    management = models.CharField(max_length=255, verbose_name='مدیریت')
    address = models.CharField(max_length=255, verbose_name='آدرس')
    saloon_rank = models.CharField(choices=rank_choices, max_length=10, verbose_name='رنک سالن')

    class Meta:
        verbose_name = 'سالن'
        verbose_name_plural = 'سالن‌ها'

    def __str__(self):
        return f"{self.name}"

    def get_follower_count(self):
        return SaloonFollow.objects.filter(follower=self).count()


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
        return ArtistFollow.objects.filter(follower=self).count()
        

    def get_following_count(self):
        return ArtistFollow.objects.filter(follower=self).count()


class UnregisteredUser(models.Model):
    phone_number = models.CharField(max_length=11, verbose_name='شماره همراه', unique=True)
    name = models.CharField(max_length=255, verbose_name='نام و نام خانوادگی')

    class Meta:
        verbose_name = 'کاربر ثبت نام نشده'
        verbose_name_plural = 'کاربران ثبت نام نشده'

    def __str__(self):
        return f"{self.phone_number}"


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
    follower = models.ForeignKey(SaloonModel, related_name='following', on_delete=models.CASCADE, verbose_name='سالن دنبال شده')
    followed_user = models.ForeignKey(User, related_name='saloon_followers', on_delete=models.CASCADE, verbose_name='دنبال کننده سالن')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'دنبال شونده سالن'
        verbose_name_plural = 'دنبال شوندگان سالن'
        unique_together = ('follower', 'followed_user')

    def __str__(self):
        return f"{self.followed_user} follows {self.follower.name}"


class ArtistFollow(models.Model):
    follower = models.ForeignKey(ArtistModel, related_name='following', on_delete=models.CASCADE, verbose_name='هنرمند دنبال شده')
    followed_user = models.ForeignKey(User, related_name='artist_followers', on_delete=models.CASCADE, verbose_name='دنبال کننده هنرمند')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'دنبال شونده هنرمند'
        verbose_name_plural = 'دنبال شوندگان هنرمند'
        unique_together = ('follower', 'followed_user')

    def __str__(self):
        return f" {self.followed_user} follows {self.follower.artist}"
