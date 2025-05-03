from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin
# Register your models here.
# admin.site.register(User)
# admin.site.register(NormalUserModel)
# admin.site.register(SaloonModel)
# admin.site.register(ArtistModel)
# admin.site.register(NormalUserFollow)
# admin.site.register(SaloonFollow)
# admin.site.register(ArtistFollow)
# admin.site.register(UnregisteredUser)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('phone_number', 'username', 'is_active', 'status', 'last_login')
    search_fields = ('phone_number', 'username', 'first_name', 'last_name')
    list_filter = ('is_active', 'status')
    readonly_fields = ('last_login', 'total_active_time', 'code_generated_at')
    fieldsets = (
        (None, {'fields': ('phone_number', 'username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'birth_date', 'city', 'profile_picture')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Security', {'fields': ('last_login', 'total_active_time', 'code_generated_at')}),
        ('Bank Info', {'fields': ('bank_account_number',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'username', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser')
        }),
    )

@admin.register(NormalUserModel)
class NormalUserAdmin(admin.ModelAdmin):
    list_display = ('normal_user', 'interests')
    search_fields = ('normal_user__phone_number', 'normal_user__username')

@admin.register(SaloonModel)
class SaloonAdmin(admin.ModelAdmin):
    list_display = ('name', 'management', 'saloon_rank')
    search_fields = ('name', 'management')
    list_filter = ('saloon_rank',)

@admin.register(ArtistModel)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ('artist', 'years_of_work', 'saloon_artists')
    search_fields = ('artist__phone_number', 'artist__username')
    list_filter = ('years_of_work',)

@admin.register(UnregisteredUser)
class UnregisteredUserAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'name')
    search_fields = ('phone_number', 'name')

@admin.register(NormalUserFollow)
class NormalUserFollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'followed_user', 'created_at')
    search_fields = ('follower__normal_user__phone_number', 'followed_user__phone_number')
    list_filter = ('created_at',)

@admin.register(SaloonFollow)
class SaloonFollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'followed_user', 'created_at')
    search_fields = ('follower__name', 'followed_user__phone_number')
    list_filter = ('created_at',)

@admin.register(ArtistFollow)
class ArtistFollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'followed_user', 'created_at')
    search_fields = ('follower__artist__phone_number', 'followed_user__phone_number')
    list_filter = ('created_at',)
