from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone
from .models import (
    Complaint,
    Profile,
    Notification,
    ComplaintImage,
    Vote,
    notify_status_change,
    notify_govt_response,
    notify_new_complaint_govt,
    notify_resolved_photo,
    notify_govt_application_submitted,
    notify_govt_application_reviewed,
)
from .forms import ComplaintForm, ExtraImageForm, GovtApplicationForm
from decimal import Decimal
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from .models import Ward
import json


# ---------- Public Pages ----------
def landing_page(request):
    # Total resolved issues
    resolved_issues = Complaint.objects.filter(status='resolved').count()
    # Active citizens: distinct users who have submitted at least one complaint
    active_citizens = Complaint.objects.values('citizen').distinct().count()
    
    # Infrastructure Value Saved – if you don't have an 'estimated_cost' field, set to 0
    # Option A: if you have estimated_cost field
    # from django.db.models import Sum
    # total_saved = Complaint.objects.filter(status='resolved').aggregate(total=Sum('estimated_cost'))['total'] or 0
    total_saved = 0   # Replace with real sum when you add the field
    
    # Response rate: percentage of complaints with government_response filled
    total_complaints = Complaint.objects.count()
    responded = Complaint.objects.filter(government_response__isnull=False).count()
    response_rate = round((responded / total_complaints) * 100) if total_complaints > 0 else 0
    total_upvotes = Complaint.objects.aggregate(total=Sum('upvotes'))['total'] or 0
    active_voters = Vote.objects.values('user').distinct().count()
    top_issues = Complaint.objects.order_by('-upvotes', '-created_at')[:5]

    # Top Civic Heroes - This Month
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    top_heroes_data = Complaint.objects.filter(
        created_at__gte=start_of_month
    ).values('citizen').annotate(
        total_points=Sum('upvotes')
    ).order_by('-total_points')[:5]
    top_citizens = []
    for hero in top_heroes_data:
        user = User.objects.get(id=hero['citizen'])
        top_citizens.append({
            'user': user,
            'points': hero['total_points']
        })

    context = {
        'news': [
            "New road construction begins in Wuse Zone 2",
            "Flood alert: Abuja to experience heavy rains this week",
            "Monthly town hall meeting scheduled for May 10th"
        ],
        'weather': "🌤️ Partly cloudy, 28°C",
        'resolved_issues': resolved_issues,
        'active_citizens': active_citizens,
        'value_saved': total_saved,
        'response_rate': response_rate,
        'total_upvotes': total_upvotes,
        'active_voters': active_voters,
        'top_issues': top_issues,
        'top_citizens': top_citizens,
    }
    return render(request, 'complaints/landing.html', context)

def about(request):
    return render(request, 'complaints/about.html')

def contact(request):
    return render(request, 'complaints/contact.html')

# ---------- Authentication ----------
def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Profile will be auto-created via signal (citizen by default)
            auth_login(request, user)  # log the user in immediately
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

class custom_login(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
    def get_success_url(self):
        return reverse_lazy('dashboard')

# ---------- Protected Dashboard ----------
@login_required
def dashboard(request):
    profile = request.user.profile
    if profile.user_type == 'govt':
        complaints = Complaint.objects.all().order_by('-created_at')
        return render(request, 'complaints/govt_dashboard.html', {'complaints': complaints})
    else:
        my_complaints = Complaint.objects.filter(citizen=request.user)
        return render(request, 'complaints/citizen_dashboard.html', {'complaints': my_complaints})

@login_required
def report_complaint(request):
    if request.method == 'POST':
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.citizen = request.user
            lat_val = request.POST.get('latitude')
            lng_val = request.POST.get('longitude')
            complaint.latitude = Decimal(lat_val) if lat_val and lat_val.strip() else None
            complaint.longitude = Decimal(lng_val) if lng_val and lng_val.strip() else None

            # auto-detect Ward (and via it, LGA + State) from the submitted point
            if complaint.latitude is not None and complaint.longitude is not None:
                point = Point(float(complaint.longitude), float(complaint.latitude), srid=4326)
                complaint.location = point
                matched_ward = Ward.objects.filter(boundary__contains=point).first()
                complaint.ward = matched_ward  # stays None if point falls outside all known wards

            complaint.save()
            
            # Notify government users of new complaint
            notify_new_complaint_govt(complaint)
            
            return redirect('dashboard')
    else:
        form = ComplaintForm()
    return render(request, 'complaints/report.html', {'form': form})

# ---------- Community voting feed ----------
@login_required
def community_complaints(request):
    complaints = Complaint.objects.order_by('-upvotes', '-created_at')
    user_votes = []
    if request.user.is_authenticated:
        user_votes = list(Vote.objects.filter(user=request.user).values_list('complaint_id', flat=True))
    return render(request, 'complaints/community_complaints.html', {
        'complaints': complaints,
        'user_votes': user_votes,
    })

@login_required
def get_trending_complaints(request):
    trending = Complaint.objects.order_by('-upvotes', '-created_at')[:5]
    return JsonResponse({'trending': [
        {
            'id': complaint.id,
            'category': complaint.get_category_display(),
            'description': complaint.description[:120],
            'upvotes': complaint.upvotes,
            'status': complaint.get_status_display(),
            'created_at': complaint.created_at.strftime('%Y-%m-%d %H:%M'),
        }
        for complaint in trending
    ]})

# ---------- Nearby complaints (landing page map) ----------
def get_nearby_complaints(request):
    """API endpoint: complaints within 10km of a given lat/lng, for the landing page map"""
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    if not lat or not lng:
        return JsonResponse({'error': 'lat and lng are required'}, status=400)

    try:
        user_point = Point(float(lng), float(lat), srid=4326)
    except ValueError:
        return JsonResponse({'error': 'invalid lat/lng'}, status=400)

    nearby = (
        Complaint.objects
        .filter(location__isnull=False, location__distance_lte=(user_point, D(km=10)))
        .annotate(distance=Distance('location', user_point))
        .order_by('distance')[:20]
    )

    return JsonResponse({'complaints': [
        {
            'id': c.id,
            'category': c.get_category_display(),
            'description': c.description[:100],
            'status': c.get_status_display(),
            'lat': c.latitude,
            'lng': c.longitude,
        }
        for c in nearby
    ]})

@require_POST
@login_required


def get_ward_boundary(request):
    """API endpoint: returns the Ward polygon (GeoJSON) containing a given lat/lng"""
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    if not lat or not lng:
        return JsonResponse({'error': 'lat and lng are required'}, status=400)

    try:
        point = Point(float(lng), float(lat), srid=4326)
    except ValueError:
        return JsonResponse({'error': 'invalid lat/lng'}, status=400)

    ward = Ward.objects.filter(boundary__contains=point).first()
    if not ward:
        return JsonResponse({'ward': None})

    return JsonResponse({
        'ward': ward.ward,
        'lga': ward.lga,
        'state': ward.state,
        'boundary': json.loads(ward.boundary.geojson),
    })

def toggle_vote(request, complaint_id):
    profile = request.user.profile
    if profile.user_type != 'citizen':
        return JsonResponse({'success': False, 'error': 'Only citizens may vote on complaints.'}, status=403)

    complaint = get_object_or_404(Complaint, id=complaint_id)
    with transaction.atomic():
        vote, created = Vote.objects.get_or_create(user=request.user, complaint=complaint)
        if created:
            complaint.refresh_from_db(fields=['upvotes'])
            return JsonResponse({'success': True, 'voted': True, 'upvotes': complaint.upvotes})
        vote.delete()
        complaint.refresh_from_db(fields=['upvotes'])
        return JsonResponse({'success': True, 'voted': False, 'upvotes': complaint.upvotes})

#updating views to create notifications when government updates complaint status, adds response, or adds resolution photo. Also added citizen_dashboard and complaint_detail views to display multiple images and details for citizens.

@login_required
def update_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    
    # Authtorization check
    if request.user.profile.user_type != 'govt':
        return redirect('dashboard')

    if request.method == 'POST':
        #captures old state before update to compare and create notifications accordingly
        #we store the 'truth' of these values befroe the object is changed in memory
        old_status = complaint.status
        old_response = bool(complaint.government_response)
        old_resolved_photo = bool(complaint.resolved_photo)
        
        #update the complaint with new values from the form
        new_status = request.POST.get('status')
        new_response = request.POST.get('government_response')

        complaint.status = new_status
        complaint.government_response = new_response
        
        # Handle resolved photo upload
        if 'resolved_photo' in request.FILES:
            complaint.resolved_photo = request.FILES['resolved_photo']
        
        complaint.save()
        
        # TRIGGER NOTIFICATIONS BASED ON WHAT CHANGED
        # we compare the old and new values to determine what notifications to create
        if old_status != new_status:
            notify_status_change(complaint, old_status, new_status)
        
        if not old_response and new_response:
            notify_govt_response(complaint)
            
        if not old_resolved_photo and complaint.resolved_photo:
            notify_resolved_photo(complaint)
            
        return redirect('dashboard')
    return render(request, 'complaints/update_complaint.html', {'complaint': complaint})

# ---------- Government Officer Verification ----------

@login_required
def apply_govt_official(request):
    profile = request.user.profile

    # prevent duplicate applications while one is already pending or approved
    if profile.verification_status == 'pending':
        return render(request, 'complaints/govt_application_status.html', {'profile': profile})
    if profile.is_verified_govt():
        return redirect('dashboard')

    if request.method == 'POST':
        form = GovtApplicationForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            application = form.save(commit=False)
            application.verification_status = 'pending'
            application.applied_at = timezone.now()
            application.save()

            notify_govt_application_submitted(application)

            return render(request, 'complaints/govt_application_status.html', {'profile': application})
    else:
        form = GovtApplicationForm(instance=profile)

    return render(request, 'complaints/apply_govt_official.html', {'form': form})


@login_required
def govt_applications_list(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    applications = Profile.objects.filter(verification_status='pending').order_by('applied_at')
    return render(request, 'complaints/govt_applications_list.html', {'applications': applications})


@login_required
def review_govt_application(request, profile_id):
    if not request.user.is_staff:
        return redirect('dashboard')

    profile = get_object_or_404(Profile, id=profile_id)

    if request.method == 'POST':
        decision = request.POST.get('decision')  # 'approved' or 'rejected'

        if decision in ('approved', 'rejected'):
            profile.verification_status = decision
            profile.verified_at = timezone.now()
            profile.verified_by = request.user

            if decision == 'approved':
                profile.user_type = 'govt'

            profile.save()

            notify_govt_application_reviewed(profile)

            return redirect('govt_applications_list')

    return render(request, 'complaints/govt_application_review.html', {'profile': profile})

# citizen_dashboard for multiple image and citizen display
@login_required
def citizen_dashboard(request):
    complaints = Complaint.objects.filter(citizen=request.user).order_by('-created_at')
    top_issues = Complaint.objects.order_by('-upvotes', '-created_at')[:5]
    return render(request, 'complaints/citizen_dashboard.html', {
        'complaints': complaints,
        'top_issues': top_issues,
    })

@login_required
def complaint_detail(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    extra_images = complaint.extra_images.all()
    form = ExtraImageForm()
    is_owner = request.user == complaint.citizen
    
    if request.method == 'POST' and 'add_image' in request.POST and is_owner:
        form = ExtraImageForm(request.POST, request.FILES)
        if form.is_valid():
            extra_image = form.save(commit=False)
            extra_image.complaint = complaint
            extra_image.save()
            return redirect('complaint_detail', complaint_id=complaint.id)
    
    return render(request, 'complaints/complaint_detail.html', {
        'complaint': complaint,
        'extra_images': extra_images,
        'form': form,
        'is_owner': is_owner,
    })


# ---------- Notification API Views ----------

@login_required
def get_notifications(request):
    """API endpoint to get user's notifications"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:20]
    data = []
    for notification in notifications:
        data.append({
            'id': notification.id,
            'type': notification.notification_type,
            'title': notification.title,
            'message': notification.message,
            'is_read': notification.is_read,
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M'),
            'complaint_id': notification.complaint.id if notification.complaint else None,
        })
    return JsonResponse({'notifications': data})

@login_required
def get_unread_count(request):
    """API endpoint to get unread notification count"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'unread_count': count})

@require_POST
@login_required
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'})

@require_POST
@login_required
def mark_all_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})