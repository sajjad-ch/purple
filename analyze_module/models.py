from django.db import models
from account_module.models import User
from services_module.models import VisitingTimeModel, PostModel, StoryModel
from ChatAPI.models import Conversation, Message
# Create your models here.

class MonitoringUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='user')
    user_presence_start = models.DateTimeField(verbose_name='زمان شروع حضور کاربر')
    user_presence_end = models.DateTimeField(verbose_name='زمان انتهای حضور کاربر')
    user_presence_total = models.PositiveIntegerField(verbose_name='مدت زمان حضور کاربر')
    canceled_visiting_time = models.PositiveIntegerField(verbose_name='تعداد نوبت های کنسل شده')
    second_appointment = models.BooleanField(default=False, verbose_name='نوبت دوم گرفته / نگرفته')
    conversation_number = models.PositiveIntegerField(verbose_name='تعداد گفت و گو ها')
    message_number = models.PositiveIntegerField(verbose_name='تعداد پیام ها')
    media_message_number = models.PositiveIntegerField(verbose_name='تعداد گفت و گو های رسانه ای')
    text_message_number = models.PositiveIntegerField(verbose_name='تعداد گفت و گو های متنی')
    visiting_time_message_number = models.PositiveIntegerField(verbose_name='تعداد پیام های مربوط به نوبت')
    cosultment_message_number = models.PositiveIntegerField(verbose_name='تعداد پیام های مربوط به مشاوره')
    profile_visit_number = models.PositiveIntegerField(verbose_name='بازدید از پروفایل')
    profile_picture_visit_number = models.PositiveIntegerField(verbose_name='بازدید از تصویر پروفایل')
    total_post_seen = models.PositiveIntegerField(verbose_name='بازدید پست ها')
    total_story_seen = models.PositiveIntegerField(verbose_name='بازدید استوری ها')
    no_story = models.BooleanField(default=False, verbose_name='کاربر بدون استوری')
    one_story = models.BooleanField(default=False, verbose_name='کاربر با یک استوری')
    more_than_one_story = models.BooleanField(default=False, verbose_name='کاربر با بیش از یک استوری')

    class Meta:
        verbose_name = 'مانیتور کاربر'
        verbose_name_plural = 'مانیتور کاربر ها'

    def __str__(self):
        return f'{self.user.first_name} {self.user.last_name} بررسی'


class PostVisit(models.Model):
    monitoring_user = models.ForeignKey(MonitoringUser, on_delete=models.CASCADE, related_name='post_visits', verbose_name='کاربر مانیتور شده')
    post = models.ForeignKey(PostModel, on_delete=models.CASCADE, related_name='visits', verbose_name='پست')
    visit_count = models.PositiveIntegerField(default=0, verbose_name='تعداد بازدید')
    like_count = models.PositiveIntegerField(default=0, verbose_name='تعداد لایک ها')

    class Meta:
        unique_together = ('monitoring_user', 'post')
        verbose_name = 'بازدید پست'
        verbose_name_plural = 'بازدیدهای پست‌ها'

    def __str__(self):
        return f"{self.monitoring_user.user.username} visited {self.post.id} {self.visit_count} times"


class StoryVisit(models.Model):
    monitoring_user = models.ForeignKey(MonitoringUser, on_delete=models.CASCADE, related_name='story_visits', verbose_name='کاربر مانیتور شده')
    story = models.ForeignKey(StoryModel, on_delete=models.CASCADE, related_name='visits', verbose_name='استوری')
    visit_count = models.PositiveIntegerField(default=0, verbose_name='تعداد بازدید')
    like_count = models.PositiveIntegerField(default=0, verbose_name='تعداد لایک ها')
    story_renewal = models.BooleanField(default=False, verbose_name='تمدید استوری')

    class Meta:
        unique_together = ('monitoring_user', 'story')
        verbose_name = 'بازدید استوری'
        verbose_name_plural = 'بازدیدهای استوری ها'

    def __str__(self):
        return f"{self.monitoring_user.user.username} visited {self.story.id} {self.visit_count} times"
    

