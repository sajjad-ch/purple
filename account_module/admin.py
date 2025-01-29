from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(User)
admin.site.register(NormalUserModel)
admin.site.register(SaloonModel)
admin.site.register(ArtistModel)
admin.site.register(NormalUserFollow)
admin.site.register(SaloonFollow)
admin.site.register(ArtistFollow)
admin.site.register(UnregisteredUser)