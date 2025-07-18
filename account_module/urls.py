from django.urls import path
from . import views

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
urlpatterns = [
    path('', views.HomeAPIView.as_view(), name='Home-page'),
    path('token/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('is_authenticated/<str:token>/', views.verify_authenticattion, name='is_authenticated'),
    path('user_public_key/', views.GetPublickKeyForUser.as_view(), name='get-public-key'),
    path('sign_up/', views.SignUpAPIView.as_view(), name='signup-page'),
    path('verify/', views.VerifyKeyView.as_view(), name='verify-page'),
    path('profile/', views.ProfileView.as_view(), name='profile-page'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('saloon_profile/<int:user_id>/', views.ViewSaloonProfile.as_view(), name='saloon-profile'),
    path('artist_profile/<int:user_id>/', views.ViewArtistProfile.as_view(), name='artist-profile'),
    path('follow/<int:user_id>/', views.FollowView.as_view(), name='follow'),
    path('check_follow/', views.CheckFollowAPIView.as_view(), name='check-follow'),
    path('key_setter/', views.PublicAndPrivateKeySetter.as_view(), name='key-setter'),
    path('user_list/', views.user_list, name='user_list'),
    path('get_provinces/', views.get_provinces, name='get-provinces'),
    path('get_cities/', views.get_cities, name='get-cities'),
]
