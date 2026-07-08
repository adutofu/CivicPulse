from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    SignUpView, LoginView, UserProfileView,
    ComplaintViewSet, VoteViewSet, NotificationViewSet
)

router = DefaultRouter()
router.register(r'complaints', ComplaintViewSet, basename='complaint')
router.register(r'votes', VoteViewSet, basename='vote')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    # Auth endpoints
    path('auth/signup/', SignUpView.as_view(), name='api_signup'),
    path('auth/login/', LoginView.as_view(), name='api_login'),
    path('auth/profile/', UserProfileView.as_view(), name='api_profile'),
    
    # Router endpoints
    path('', include(router.urls)),
]
