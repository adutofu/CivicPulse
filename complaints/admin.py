
# Register your models here.
from django.contrib import admin
from .models import (
    Profile,
    Complaint,
    ComplaintImage,
    GovernmentUpdate,
    Notification,
    Vote,
    Ward,
    Comment,
    Flag,
    Escalation,
    Repost,
    ComplaintFollower,
)

# Register your models here.

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'verification_status', 'agency', 'assigned_state', 'assigned_lga')
    list_filter = ('user_type', 'verification_status')
    search_fields = ('user__username', 'user__email', 'agency')
    autocomplete_fields = ('user',)


class ComplaintImageInline(admin.TabularInline):
    model = ComplaintImage
    extra = 0


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('id', 'citizen', 'category', 'status', 'upvotes', 'is_hidden', 'ward', 'created_at')
    list_filter = ('status', 'category', 'is_hidden', 'created_at')
    search_fields = ('description', 'citizen__username', 'address_text')
    autocomplete_fields = ('citizen', 'ward', 'escalated_by')
    date_hierarchy = 'created_at'
    inlines = [ComplaintImageInline]


@admin.register(GovernmentUpdate)
class GovernmentUpdateAdmin(admin.ModelAdmin):
    list_display = ('title', 'published_at')
    search_fields = ('title', 'content')
    date_hierarchy = 'published_at'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('user__username', 'title', 'message')
    autocomplete_fields = ('user', 'complaint')
    date_hierarchy = 'created_at'


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'complaint', 'created_at')
    search_fields = ('user__username',)
    autocomplete_fields = ('user', 'complaint')
    date_hierarchy = 'created_at'


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ('ward', 'lga', 'state', 'country', 'area_sqkm')
    list_filter = ('state', 'lga')
    search_fields = ('ward', 'lga', 'state')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'complaint', 'is_approved', 'created_at')
    list_filter = ('is_approved',)
    search_fields = ('author__username', 'text')
    autocomplete_fields = ('complaint', 'author', 'parent')
    date_hierarchy = 'created_at'


@admin.register(Flag)
class FlagAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'reported_by', 'reason', 'resolved', 'created_at')
    list_filter = ('reason', 'resolved')
    search_fields = ('reported_by__username', 'description')
    autocomplete_fields = ('complaint', 'reported_by', 'comment')
    date_hierarchy = 'created_at'


@admin.register(Escalation)
class EscalationAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'escalated_by', 'target_authority', 'created_at')
    search_fields = ('escalated_by__username', 'target_authority', 'reason')
    autocomplete_fields = ('complaint', 'escalated_by')
    date_hierarchy = 'created_at'


@admin.register(Repost)
class RepostAdmin(admin.ModelAdmin):
    list_display = ('user', 'complaint', 'created_at')
    search_fields = ('user__username',)
    autocomplete_fields = ('user', 'complaint')
    date_hierarchy = 'created_at'


@admin.register(ComplaintFollower)
class ComplaintFollowerAdmin(admin.ModelAdmin):
    list_display = ('user', 'complaint', 'created_at')
    search_fields = ('user__username',)
    autocomplete_fields = ('user', 'complaint')
    date_hierarchy = 'created_at'