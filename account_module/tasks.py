from celery import shared_task
from account_module.models import User, NormalUserModel

@shared_task
def update_to_normal_users():
    users_to_update = User.objects.filter(saloon__isnull=True, artist__isnll=True)
    for user in users_to_update:
        if not hasattr(user, 'normal_user'):
            NormalUserModel.objects.create(normal_user=user, interests="")