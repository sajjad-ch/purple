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
    path('profile_posts/<int:user_id>/', ProfilePostAPIView.as_view(), name='profile-post'),
    path('posts/posts-likes/<int:post_id>/', ReturnLikeAPIView.as_view(), name='post-likes'),
    path('add_media/', AddMediaPostView.as_view(), name='add_media'),
    path('post_media_update/<int:media_id>/', UpdateMediaPostView.as_view(), name='media-update'),
    path('post_media_delete/<int:media_id>/', DeleteMediaPostView.as_view(), name='media-delete'),

    # Saved Post
    path('saved_post/', SavedPostView.as_view(), name='saved-post'),
    path('check_post_saved/<int:post_id>/', CheckSavedThePostByUser.as_view(), name='check-post-saved-by-user'),

    # Certificate URLs
    path('certificates/', CertificateAPIView.as_view(), name='certificate-list-create'),
    path('certificates/<int:pk>/', CertificateAPIView.as_view(), name='certificate-detail-update-delete'),
    path('profile_certificates/<int:user_id>/', ProfileCertificateAPIView.as_view(), name='profile-certificates'),
    path('user-certificate/', GetCertificates.as_view(), name='user-certificates'),

    # Story URLs
    path('stories/', StoryAPIView.as_view(), name='story-list-create'),
    path('stories/<int:pk>/', StoryAPIView.as_view(), name='story-detail-update-delete'),

    # Highlight  URLs
    path('highlights/', HighlightAPIView.as_view(), name='highlight-list-create'),
    path('highlights/<int:pk>/', HighlightAPIView.as_view(), name='highlight-detail-update-delete'),
    path('highlight_media_delete/<int:media_id>/', DeleteHighlighMediaView.as_view(), name='media-delete'),
    path('add_highlight_media/', AddMediaHighlightView.as_view(), name='add_media'),

    # Like URLs
    path('posts/<int:post_id>/like/', LikeAPIView.as_view(), name='like-post'),
    path('posts/<int:post_id>/unlike/', LikeAPIView.as_view(), name='unlike-post'),

    # Visiting Time URLs
    path('visits/select-artist/<int:saloon_id>/', GetAllArtistsFromSaloon.as_view(), name='saloon-artists'),
    path('visits/select-service/<int:saloon_id>/', GetAllServicesFromSaloon.as_view(), name='saloon-service'),
    path('visits/select-supservice/<int:artist_id>/', GetSupservicesFromArtist.as_view(), name='artist-service'),
    path('visits/select-supservice/<int:saloon_id>/<int:service_id>/', GetSupserviceFromServiceAndSaloon.as_view(), name='supservice-service-saloon'),
    path('visits/select-artist/<int:saloon_id>/<int:supservice_id>/', GetArtistFromSaloonAndSupservice.as_view(), name='supservice-saloon-supservice'),
    path('visits/select-supservice-artist/<int:artist_id>/<int:service_id>/', GetSupserviceFromArtistAndService.as_view(), name='supservice-artist-service'),
    path('visits/select-service-artist/<int:artist_id>/', GetServiceFromArtist.as_view(), name='service-artist'),
    path('visits/requesting/saloon/', SaloonVisitsAPIView.as_view(), name='saloons'),
    path('visits/requesting/artist/', ArtistVisitsAPIView.as_view(), name='artists'),
    path('visits-saloon/<int:user_id>/request/', RequestVisitingTimeSaloonAPIView.as_view(), name='request-visiting-time-saloon'),
    path('visits-artist/<int:user_id>/request/', RequestVisitingTimeArtistAPIView.as_view(), name='request-visiting-time-artist'),
    path('confirmed-visits-user/', UserConfirmedVisitingTimeAPIView.as_view(), name='user-confirmed-visiting-time'),
    path('other-visits-user/', UserOtherVisitingTimeAPIView.as_view(), name='user-other-visiting-time'),
    path('completed-visits-user/', UserCompletedVisitingTimeAPIView.as_view(), name='user-completed-visiting-time'),
    path('visits/', GetConfirmVisitAPIView.as_view(), name='confirm-visit'),
    path('visits/select-supservice/', SupserviceFromArtistAPIView.as_view(), name='supservice-from-artist'),
    path('visits/<int:visit_id>/confirm/', PostConfirmVisitAPIView.as_view(), name='post_confirm_visit'),
    path('visits/handing-visit/', HandingVisitingView.as_view(), name='handing-visiting'),
    path('visits/select-artist-visits/', GetArtsitsFromSaloonAPIView.as_view(), name='artist-visits'),
    path('visits/select-visits/<int:artist_id>/', GetVisitsFromArtistAPIView.as_view(), name='visits-artist'),

    # changing states for visits
    path('visits/change-states/confirmed-to-complete/', ChangeConfirmedToCompleted.as_view(), name='confirmed-to-complete'),
    path('visits/change-states/waiting-for-deposit-to-rejected-sa/', ChangeWaitingForDepositToRejectedByArtistOrSaloon.as_view(), name='waiting-for-deposit-to-rejected-sa'),
    path('visits/change-states/waiting-for-deposit-to-rejected-user/', ChangeWaitingForDepositToRejectedByUser.as_view(), name='waiting-for-deposit-to-rejected-user'),


    # Payment Notification URL
    path('visits/payment/', UserVisitAPIView.as_view(), name='user-visits'),
    path('visits/<int:visit_id>/payment/', PaymentHandlingAPIView.as_view(), name='payment-handling'),

    # Grade Notification URL
    path('visits/<int:visit_id>/grade/', GradeNotificationAPIView.as_view(), name='grade-notification'),
    path('visits/grade/', GradingAPIView.as_view(), name='grading'),
    path('visits/grade/<int:visit_id>/', GradingAPIView.as_view(), name='grading-post'),

    # filtering Saloon and Artist
    path('filter/saloon/', FilterSaloonAPIView.as_view(), name='filter-saloon'),
    path('filter/artist/', FilterArtistAPIView.as_view(), name='filter-artist'),

    # Wallet URLs
    path('wallet/', WalletAPIView.as_view(), name='wallet'),

    # Discount URLs
    path('discounts/', DiscountsAPIView.as_view(), name='discounts-list-create'),
]
