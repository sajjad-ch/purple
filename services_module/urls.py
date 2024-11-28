from django.urls import path
from .views import *

urlpatterns = [
    # HomePage User URLs
    path('sliders/', SliderView.as_view(), name='sliderr'),
    path('service/', ServicesView.as_view(), name='service'),
    path('service_artist/<int:service_code>', ServiceFilterArtistView.as_view(), name='service_filter_artist'),
    path('service_saloon/<int:service_code>', ServiceFilterSaloonView.as_view(), name='service_filter_saloon'),
    path('best_user/', BestUserView.as_view(), name='best-user'),

    # HomePage Saloon or Artist URLs
    path('managing_financial/', ManagingFinancialView.as_view(), name='managing-financial'),
    path('getting_financial/', GettingFinancialView.as_view(), name='getting-financial'),
    path('calculate_payment/', CalculatePaymentView.as_view(), name='calculate-payment'),
    path('user_service/', UserServicesView.as_view(), name='user-service'),
    path('manage_artist/', ManageArtistTeamView.as_view(), name='manage-artist-team'),
    path('active_artist/', ActiveArtistView.as_view(), name='active-artist'),

    # Post URLs
    path('posts/', PostAPIView.as_view(), name='post-list-create'),
    path('posts/<int:pk>/', PostAPIView.as_view(), name='post-detail-update-delete'),

    # Story URLs
    path('stories/', StoryAPIView.as_view(), name='story-list-create'),
    path('stories/<int:pk>/', StoryAPIView.as_view(), name='story-detail-update-delete'),

    # Like URLs
    path('posts/<int:post_id>/like/', LikeAPIView.as_view(), name='like-post'),
    path('posts/<int:post_id>/unlike/', LikeAPIView.as_view(), name='unlike-post'),

    # Visiting Time URLs
    path('visits/requesting/saloon/', SaloonVisitsAPIView.as_view(), name='saloons'),
    path('visits/requesting/artist/', ArtistVisitsAPIView.as_view(), name='artists'),
    path('visits-saloon/<int:user_id>/request/', RequestVisitingTimeSaloonAPIView.as_view(), name='request-visiting-time-saloon'),
    path('visits-artist/<int:user_id>/request/', RequestVisitingTimeArtistAPIView.as_view(), name='request-visiting-time-artist'),
    path('visits/', GetConfirmVisitAPIView.as_view(), name='confirm-visit'),
    path('visits/<int:visit_id>/confirm/', PostConfirmVisitAPIView.as_view(), name='post_confirm_visit'),

    # Payment Notification URL
    path('visits/payment/', Payments.as_view(), name='payment'),
    path('visits/<int:visit_id>/payment/', PaymentNotificationAPIView.as_view(), name='payment-notification'),

    # Grade Notification URL
    path('visits/<int:visit_id>/grade/', GradeNotificationAPIView.as_view(), name='grade-notification'),
    path('visits/grade/', GradingAPIView.as_view(), name='grading'),

    # filtering Saloon and Artist
    path('filter/saloon/', FilterSaloonAPIView.as_view(), name='filter-saloon'),
    path('filter/artist/', FilterArtistAPIView.as_view(), name='filter-artist'),

# Wallet URLs
    path('wallet/', WalletAPIView.as_view(), name='wallet'),

    # Discount URLs
    path('discounts/', DiscountsAPIView.as_view(), name='discounts-list-create'),
]
