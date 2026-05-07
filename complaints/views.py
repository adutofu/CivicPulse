from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .models import (
    Complaint,
    Profile,
    Notification,
    ComplaintImage,
    notify_status_change,
    notify_govt_response,
    notify_new_complaint_govt,
    notify_resolved_photo,
)
from .forms import ComplaintForm, ExtraImageForm
from decimal import Decimal


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
    
    context = {
        'news': [
            "New road construction begins in Wuse Zone 2",
            "Flood alert: Abuja to experience heavy rains this week",
            "Monthly town hall meeting scheduled for May 10th"
        ],
        'weather': "🌤️ Partly cloudy, 28°C",
        # The dynamic counters
        'resolved_issues': resolved_issues,
        'active_citizens': active_citizens,
        'value_saved': total_saved,
        'response_rate': response_rate,
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
            complaint.save()
            
            # Notify government users of new complaint
            notify_new_complaint_govt(complaint)
            
            return redirect('dashboard')
    else:
        form = ComplaintForm()
    return render(request, 'complaints/report.html', {'form': form})

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

# citizen_dashboard for multiple image and citizen display
@login_required
def citizen_dashboard(request):
    complaints = Complaint.objects.filter(citizen=request.user).order_by('-created_at')
    return render(request, 'complaints/citizen_dashboard.html', {'complaints': complaints})

@login_required
def complaint_detail(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id, citizen=request.user)
    extra_images = complaint.extra_images.all()
    form = ExtraImageForm()
    
    if request.method == 'POST' and 'add_image' in request.POST:
        form = ExtraImageForm(request.POST, request.FILES)
        if form.is_valid():
            extra_image = form.save(commit=False)
            extra_image.complaint = complaint
            extra_image.save()
            return redirect('complaint_detail', complaint_id=complaint.id)
    
    return render(request, 'complaints/complaint_detail.html', {
        'complaint': complaint,
        'extra_images': extra_images,
        'form': form,})


# ---------- Notification API Views ----------
from django.http import JsonResponse
from django.views.decorators.http import require_POST

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