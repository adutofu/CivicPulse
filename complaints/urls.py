from django.urls import path
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views
from . import views
urlpatterns = [
    path('', views.landing_page, name='landing'),           # Landing page (public)
    path('dashboard/', views.dashboard, name='dashboard'),  # User dashboard (login required)
    path('report/', views.report_complaint, name='report_complaint'), # Complaint form (login req)
    path('update/<int:complaint_id>/', views.update_complaint, name='update_complaint'), # Govt update page

# Government Officer Verification
    path('apply-govt/', views.apply_govt_official, name='apply_govt_official'),  # citizen applies to become govt officer
    path('govt-applications/', views.govt_applications_list, name='govt_applications_list'),  # admin: pending applications queue
    path('govt-applications/<int:profile_id>/review/', views.review_govt_application, name='review_govt_application'),  # admin: approve/reject

    path('signup/', views.signup, name='signup'),           # Signup form (public)
    path('login/', views.custom_login.as_view(), name='login'),       # Custom login view
    path('logout/', LogoutView.as_view(next_page='landing', http_method_names=['get', 'post']), name='logout'),
    path('about/', views.about, name='about'),              # About page
    path('contact/', views.contact, name='contact'),        # Contact page
    path('my-complaints/', views.citizen_dashboard, name='citizen_dashboard'),  # citizen view of all own complaints
    path('community/', views.community_complaints, name='community_complaints'),
    path('complaint/<int:complaint_id>/', views.complaint_detail, name='complaint_detail'),  # detailed complaint view for citizens

    # Community voting API endpoints
    path('api/vote/<int:complaint_id>/', views.toggle_vote, name='toggle_vote'),
    path('api/trending/', views.get_trending_complaints, name='get_trending_complaints'),
    # ---------- Map and spatial endpoints ----------
    path('api/nearby-complaints/', views.get_nearby_complaints, name='get_nearby_complaints'),
    # Notification API endpoints
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notifications/unread-count/', views.get_unread_count, name='get_unread_count'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('api/ward-boundary/', views.get_ward_boundary, name='get_ward_boundary'),
    
    # Moderation endpoints (Admin / Superuser only)
    path('moderation/', views.moderation_queue, name='moderation_queue'),
    path('moderation/resolve/<int:flag_id>/', views.resolve_flag, name='resolve_flag'),

]

