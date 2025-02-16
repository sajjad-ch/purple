from django.db import models
from django.contrib.auth import get_user_model
from datetime import datetime
from .utils import random_code
from account_module.models import ArtistModel, SaloonModel
from django.core.validators import MaxValueValidator, MinValueValidator 
from django_jalali.db import models as jmodels

User = get_user_model()

times = (
    ('morning', 'صبح'),
    ('noon', 'ظهر'),
    ('afternoon', 'بعد از ظهر'),
    ('evening', 'عصر'),
    ('night', 'شب'),
)

status = (
    ('waiting for confirmation', 'در انتظار تایید'),
    ('confirmed', 'تایید شده'),
    ('rejected', 'رد شده'),
    ('waiting for deposit', 'در انتظار بیعانه'),
    ('completed', 'تکمیل شده'),
    ('deleted', 'حذف شده'),
)

ranks = (
    (1, 1),
    (2, 2),
    (3, 3),
    (4, 4),
    (5, 5),
)

discounts = (
    ('holiday', 'holiday'),
    ('admin', 'admin')
)


class PostModel(models.Model):
    user = models.ForeignKey(User, verbose_name='کاربر', on_delete=models.CASCADE, related_name='posts')
    post_content = models.FileField(upload_to='posts/', verbose_name='محتوای پست')
    caption = models.TextField(blank=True, verbose_name='توضیحات متن')
    created = models.DateTimeField(auto_now_add=True, verbose_name='ساخته شده در')
    likes = models.PositiveIntegerField(default=0, verbose_name='تعداد لایک ها')
    tag = models.ManyToManyField('services_module.TagsModel', verbose_name='تگ ها')
    is_certificate = models.BooleanField(default=False, verbose_name='گواهی نامه')

    class Meta:
        verbose_name = 'پست'
        verbose_name_plural = 'پست ها'

    def __str__(self):
        return f"{self.user} created a post on {self.created.date()}"


class TagsModel(models.Model):
    tag_name = models.CharField(max_length=128, verbose_name='نام تگ')

    class Meta:
        verbose_name = 'تگ'
        verbose_name_plural = 'تگ ها'

    def __str__(self):
        return f"{self.tag_name}"
    

class StoryModel(models.Model):
    user = models.ForeignKey(User, verbose_name='کاربر', on_delete=models.CASCADE)
    story_content = models.FileField(upload_to='stories/', verbose_name='محتوای استوری')
    created = models.DateTimeField(auto_now_add=True, verbose_name='ساخته شده در')
    duration = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='گذشته از')
    reply = models.CharField(max_length=255, null=True, blank=True)
    

    class Meta:
        verbose_name = 'استوری'
        verbose_name_plural = 'استوری ها'

    def time_passed(self):
        self.duration = datetime.now() - self.created

    def __str__(self):
        return f"{self.user} created a story on {self.created.date()}"


class HighlightModel(models.Model):
    user = models.ForeignKey(User, verbose_name='کاربر', on_delete=models.CASCADE)
    highlight_content = models.FileField(upload_to='highlights/', verbose_name='محتوای هایلایت')
    created = models.DateTimeField(auto_now_add=True, verbose_name='ساخته شده در')
    text = models.TextField(verbose_name='توضیحات متن', null=True, blank=True)

    class Meta:
        verbose_name = 'هایلایت'
        verbose_name_plural = 'هایلایت ها'

    def __str__(self):
        return f"{self.user} created a highlight on {self.created.date()}"


class ServiceModel(models.Model):
    service_code = models.PositiveIntegerField(primary_key=True, verbose_name='کد محصول')
    service_name_en = models.CharField(max_length=40, verbose_name='نام خدمت به انگلیسی', null=True, blank=True)
    service_name_fa = models.CharField(max_length=40, verbose_name='نام خدمت به فارسی', null=True, blank=True)
    service_icon = models.FileField(upload_to='service_icons/', verbose_name='تصویر لاین اصلی خدمت', null=True, blank=True)

    class Meta:
        verbose_name = 'خدمت'
        verbose_name_plural = 'خدمت ها'

    def __str__(self):
        return f"{self.service_name_fa} + {self.service_code}"


class SupServiceModel(models.Model):
    service = models.ForeignKey(ServiceModel, on_delete=models.CASCADE, verbose_name='خدمت')
    supservice_name_en = models.CharField(max_length=40, verbose_name='نام زیر خدمت به انگلیسی', null=True, blank=True)
    supservice_name_fa = models.CharField(max_length=40, verbose_name='نام زیر خدمت به فارسی', null=True, blank=True)
    supservice_icon = models.FileField(upload_to='supservice_icons/', verbose_name='تصویر زیر خدمت', null=True, blank=True)


    class Meta:
        verbose_name = 'زیر خدمت'
        verbose_name_plural = 'زیر خدمت ها'

    def __str__(self):
        return f'{self.supservice_name_fa} {self.pk} is under {self.service.service_name_fa}'


class UserServicesModel(models.Model):
    supservice = models.ForeignKey(SupServiceModel, on_delete=models.CASCADE, verbose_name='کد محصول', related_name='code', null=True, blank=True)
    artist = models.ForeignKey(ArtistModel, verbose_name='هنرمند', null=True, blank=True, on_delete=models.CASCADE)
    suggested_time = models.PositiveIntegerField(verbose_name='زمان پیشنهادی خدمت')
    suggested_price =  models.PositiveIntegerField(verbose_name='قیمت بیعانه', validators=[MinValueValidator(100000), MaxValueValidator(1000000)], default=100000)

    class Meta:
        verbose_name = 'خدمت هنرمند'
        verbose_name_plural = 'خدمات هنرمندان'

    def __str__(self):
        return f"{self.supservice} {self.artist}"


class RankModel(models.Model):
    artist = models.ForeignKey('account_module.ArtistModel', on_delete=models.CASCADE, verbose_name='هنرمند', null=True, blank=True)
    saloon = models.ForeignKey('account_module.SaloonModel', on_delete=models.CASCADE, verbose_name='سالن', null=True, blank=True)
    service = models.ForeignKey(UserServicesModel, on_delete=models.CASCADE, verbose_name='نام خدمت', null=True, blank=True)
    rank = models.IntegerField(choices=ranks, verbose_name='مقدار امتیاز')

    class Meta:
        verbose_name = 'امتیاز'
        verbose_name_plural = 'امتیاز ها'

    def __str__(self):
        if self.artist:
            return f"{self.artist} has ranks."
        else:
            return f"{self.saloon} has ranks."


class VisitingTimeModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='user', null=True, blank=True)
    unregistered_user = models.ForeignKey('account_module.UnregisteredUser', on_delete=models.CASCADE, verbose_name='کاربر ثبت نام نشده', null=True, blank=True)
    artist = models.ForeignKey('account_module.ArtistModel', on_delete=models.CASCADE, verbose_name='هنرمند', null=True, blank=True)
    saloon = models.ForeignKey('account_module.SaloonModel', on_delete=models.CASCADE, verbose_name='سالن', null=True, blank=True)
    service = models.ForeignKey(UserServicesModel, on_delete=models.CASCADE, verbose_name='نام خدمت', null=True, blank=True)
    suggested_time = models.CharField(choices=times, max_length=10, verbose_name='زمان پیشنهادی', null=True, blank=True)
    suggested_hour = models.TimeField(verbose_name='ساعت پیشنهادی', null=True, blank=True)
    suggested_date = jmodels.jDateField(verbose_name='تاریخ پیشنهادی', null=True, blank=True)
    exact_time = jmodels.jDateTimeField(null=True, blank=True, verbose_name='زمان دقیق نوبت')
    action = models.CharField(max_length=10, null=True, blank=True)
    status = models.CharField(choices=status, max_length=25, verbose_name='وضعیت نوبت', null=True, blank=True)
    confirmation_time = jmodels.jDateTimeField(null=True, blank=True, verbose_name='زمان تایید')
    payment_due_time = jmodels.jDateTimeField(null=True, blank=True, verbose_name='مهلت پرداخت')
    price = models.IntegerField(verbose_name='قیمت بیعانه', null=True, blank=True)
    rank = models.ForeignKey(RankModel, on_delete=models.CASCADE, verbose_name='امتیاز دهی', null=True, blank=True)
    text = models.TextField(verbose_name='متن نظردهی', null=True, blank=True)

    class Meta:
        verbose_name = 'نوبت دهی'
        verbose_name_plural = 'نوبت ها'

    def __str__(self):
        if self.saloon:
            return f"{self.user} has a visit time with {self.saloon} on {self.exact_time}"
        else:
            return f"{self.user} has a visit time with {self.artist} on {self.exact_time}"


class PaymentModel(models.Model):
    pass


class WalletModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر')
    amount = models.PositiveIntegerField(verbose_name='مبلغ')

    class Meta:
        verbose_name = 'کیف پول'
        verbose_name_plural = 'کیف پول ها'


class DiscountModel(models.Model):
    name = models.CharField(max_length=75, verbose_name='نام تخفیف')
    discount_type = models.CharField(choices=discounts, max_length=20, verbose_name='نوع تخفیف')
    discount_code = models.CharField(unique=True, max_length=8, verbose_name='کد تخفیف')
    percentage = models.IntegerField(verbose_name='درصد تخفیف')
    start_date = jmodels.jDateTimeField(verbose_name='تاریخ شروع')
    end_date = jmodels.jDateTimeField(verbose_name='تاریخ اتمام')

    class Meta:
        verbose_name = 'تخفیف'
        verbose_name_plural = 'تخفیفات'

    def generate_discount_code(self):
        self.discount_code = random_code()
        self.start_date = datetime.now()
        self.save()


class LikeModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر')
    post = models.ForeignKey(PostModel, on_delete=models.CASCADE, null=True, blank=True, verbose_name='پست')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'لایک'
        verbose_name_plural = 'لایک‌ها'

    @staticmethod
    def Like_count(post):
        return LikeModel.objects.filter(post=post).all().count()


class SliderModel(models.Model):
    slider_picture = models.FileField(upload_to='slider_images/', verbose_name='تصویر اسلایدر')
    slider_text = models.CharField(max_length=100, verbose_name='متن اسلایدر')
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        verbose_name = 'اسلایدر'
        verbose_name_plural = 'اسلایدر ها'

    def __str__(self):
        return f"This slider was created at {self.created_at}"
