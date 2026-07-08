from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import (
    Complaint, Profile, Vote, Notification, 
    ComplaintImage, notify_status_change, 
    notify_govt_response, notify_resolved_photo, 
    notify_new_complaint_govt
)
from .serializers import (
    ComplaintSerializer, VoteSerializer, NotificationSerializer,
    UserSerializer, ProfileSerializer, SignUpSerializer,
    ComplaintImageSerializer
)


class SignUpView(views.APIView):
    """User registration endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(views.APIView):
    """User login endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.check_password(password):
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        refresh = RefreshToken.for_user(user)
        profile = Profile.objects.get(user=user)
        
        return Response({
            'user': UserSerializer(user).data,
            'profile': ProfileSerializer(profile).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)


class UserProfileView(views.APIView):
    """Get current user profile"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
            return Response({
                'user': UserSerializer(request.user).data,
                'profile': ProfileSerializer(profile).data,
            })
        except Profile.DoesNotExist:
            return Response(
                {'error': 'Profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ComplaintViewSet(viewsets.ModelViewSet):
    """CRUD operations for complaints"""
    serializer_class = ComplaintSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'category', 'citizen']
    ordering_fields = ['created_at', 'upvotes', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user_profile = self.request.user.profile
        if user_profile.user_type == 'govt':
            # Govt users see all complaints
            return Complaint.objects.all().order_by('-created_at')
        else:
            # Citizens see their own and public feed
            return Complaint.objects.all().order_by('-created_at')
    
    def perform_create(self, serializer):
        complaint = serializer.save(citizen=self.request.user)
        # Notify govt users of new complaint
        notify_new_complaint_govt(complaint)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def update_status(self, request, pk=None):
        """Update complaint status (govt only)"""
        if request.user.profile.user_type != 'govt':
            return Response(
                {'error': 'Only government users can update complaints'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        complaint = self.get_object()
        old_status = complaint.status
        new_status = request.data.get('status')
        new_response = request.data.get('government_response')
        
        if new_status:
            complaint.status = new_status
        if new_response is not None:
            complaint.government_response = new_response
        
        if 'resolved_photo' in request.FILES:
            complaint.resolved_photo = request.FILES['resolved_photo']
        
        complaint.save()
        
        # Create notifications for changes
        if old_status != new_status:
            notify_status_change(complaint, old_status, new_status)
        if new_response and not request.data.get('_old_response'):
            notify_govt_response(complaint)
        if complaint.resolved_photo and not request.data.get('_old_resolved_photo'):
            notify_resolved_photo(complaint)
        
        return Response(
            ComplaintSerializer(complaint, context={'request': request}).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_image(self, request, pk=None):
        """Add additional image to complaint"""
        complaint = self.get_object()
        
        if complaint.citizen != request.user:
            return Response(
                {'error': 'Only complaint owner can add images'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if 'image' not in request.FILES:
            return Response(
                {'error': 'Image file required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image = ComplaintImage.objects.create(
            complaint=complaint,
            image=request.FILES['image']
        )
        
        return Response(
            ComplaintImageSerializer(image).data,
            status=status.HTTP_201_CREATED
        )


class VoteViewSet(viewsets.ViewSet):
    """Toggle upvote on complaints"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'], url_path='toggle/(?P<complaint_id>[0-9]+)')
    def toggle(self, request, complaint_id=None):
        """Toggle vote on a complaint"""
        user_profile = request.user.profile
        if user_profile.user_type != 'citizen':
            return Response(
                {'error': 'Only citizens can vote on complaints'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        complaint = get_object_or_404(Complaint, id=complaint_id)
        
        with transaction.atomic():
            vote, created = Vote.objects.get_or_create(
                user=request.user,
                complaint=complaint
            )
            
            if created:
                complaint.upvotes += 1
            else:
                vote.delete()
                complaint.upvotes -= 1
            
            complaint.save()
            
            return Response({
                'success': True,
                'voted': created,
                'upvotes': complaint.upvotes
            })


class NotificationViewSet(viewsets.ModelViewSet):
    """Manage user notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ['created_at', 'is_read']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    
    def perform_update(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        return Response({'unread_count': count})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)
        return Response({'success': True})
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark specific notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response(self.get_serializer(notification).data)
