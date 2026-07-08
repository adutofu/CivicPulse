from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Complaint, Profile, Vote, Notification, 
    ComplaintImage, GovernmentUpdate
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Profile
        fields = ['id', 'user', 'user_type', 'agency']
        read_only_fields = ['id', 'user']


class ComplaintImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintImage
        fields = ['id', 'image', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class ComplaintSerializer(serializers.ModelSerializer):
    citizen_name = serializers.CharField(source='citizen.username', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    extra_images = ComplaintImageSerializer(many=True, read_only=True)
    has_voted = serializers.SerializerMethodField()
    
    class Meta:
        model = Complaint
        fields = [
            'id', 'citizen', 'citizen_name', 'category', 'category_display',
            'description', 'photo', 'latitude', 'longitude', 'address_text',
            'status', 'status_display', 'upvotes', 'created_at', 'updated_at',
            'government_response', 'resolved_photo', 'extra_images', 'has_voted'
        ]
        read_only_fields = ['id', 'citizen', 'upvotes', 'created_at', 'updated_at']
    
    def get_has_voted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.has_vote_from(request.user)
        return False


class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ['id', 'user', 'complaint', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    complaint_id = serializers.IntegerField(source='complaint.id', read_only=True, allow_null=True)
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', read_only=True
    )
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'complaint_id', 'notification_type', 
            'notification_type_display', 'title', 'message', 'is_read', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']


class GovernmentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernmentUpdate
        fields = ['id', 'title', 'content', 'before_after_photos', 'published_at']
        read_only_fields = ['id', 'published_at']


class SignUpSerializer(serializers.ModelSerializer):
    user_type = serializers.CharField(write_only=True, default='citizen')
    agency = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'user_type', 'agency']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def create(self, validated_data):
        user_type = validated_data.pop('user_type', 'citizen')
        agency = validated_data.pop('agency', '')
        
        user = User.objects.create_user(**validated_data)
        Profile.objects.create(user=user, user_type=user_type, agency=agency)
        
        return user
