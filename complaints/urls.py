from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),           # Landing page (public)
    path('dashboard/', views.dashboard, name='dashboard'),  # User dashboard (login required)
    path('report/', views.report_complaint, name='report_complaint'), # Complaint form (login req)
    path('update/<int:complaint_id>/', views.update_complaint, name='update_complaint'), # Govt update page
    path('signup/', views.signup, name='signup'),           # Signup form (public)
    path('login/', views.custom_login.as_view, name='login'),       # Custom login view
    path('logout/', auth_views.LogoutView.as_view(next_page='landing'), name='logout'),
    path('about/', views.about, name='about'),              # About page
    path('contact/', views.contact, name='contact'),        # Contact page
]
