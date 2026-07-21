from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login as auth_login
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.db.models import Count, Sum, Count, Q, Avg, F, Sum
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
    Comment,
    Flag,
    ComplaintFollower,
    notify_status_change,
    notify_govt_response,
    notify_new_complaint_govt,
    notify_resolved_photo,
    notify_govt_application_submitted,
    notify_govt_application_reviewed,
)
from django.contrib.auth.decorators import login_required
from .forms import ComplaintForm, ExtraImageForm, GovtApplicationForm
from decimal import Decimal
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from .models import Ward
from .utils import send_notification, notify_mentions
import json
from django.core.paginator import Paginator
from itertools import chain
from django.conf import settings
from .models import Repost, CATEGORY_CHOICES
from datetime import timedelta
from django.db.models.functions import TruncDate



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


def analytics_dashboard(request):
    # ─── Date range filter ───
    range_param = request.GET.get('range', '30')
    try:
        days = int(range_param)
    except ValueError:
        days = 30
    if days <= 0:
        days = 30
    start_date = timezone.now() - timedelta(days=days)

    # ─── Base querysets ───
    complaints_qs = Complaint.objects.filter(created_at__gte=start_date)
    resolved_qs = complaints_qs.filter(status='resolved')
    pending_qs = complaints_qs.filter(status__in=['pending', 'acknowledged', 'in_progress'])
    escalated_qs = complaints_qs.filter(status='escalated')

    # ─── Total counts ───
    total_complaints = complaints_qs.count()
    total_resolved = resolved_qs.count()
    total_pending = pending_qs.count()
    total_escalated = escalated_qs.count()
    total_upvotes = Vote.objects.filter(complaint__created_at__gte=start_date).count()
    total_comments = Comment.objects.filter(complaint__created_at__gte=start_date).count()
    total_reposts = Repost.objects.filter(complaint__created_at__gte=start_date).count()
    total_follows = ComplaintFollower.objects.filter(complaint__created_at__gte=start_date).count()

    # ─── Category breakdown ───
    category_data = (
        complaints_qs
        .values('category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    category_labels = []
    category_counts = []
    for item in category_data:
        # get display name from CHOICES
        label = dict(CATEGORY_CHOICES).get(item['category'], item['category'])
        category_labels.append(label)
        category_counts.append(item['count'])

    # ─── Status breakdown ───
    status_data = (
        complaints_qs
        .values('status')
        .annotate(count=Count('id'))
        .order_by('status')
    )
    status_labels = [s['status'].replace('_', ' ').title() for s in status_data]
    status_counts = [s['count'] for s in status_data]

    # ─── Daily trend (last days) ───
    daily_data = (
        complaints_qs
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    dates = [d['date'].strftime('%Y-%m-%d') for d in daily_data]
    daily_counts = [d['count'] for d in daily_data]

    # ─── Average response time (for resolved) ───
    avg_seconds = None
    if resolved_qs.exists():
        total_seconds = 0
        for c in resolved_qs:
            if c.updated_at and c.created_at:
                delta = c.updated_at - c.created_at
                total_seconds += delta.total_seconds()
        avg_seconds = total_seconds / resolved_qs.count()
        days_avg = avg_seconds // 86400
        hours_avg = (avg_seconds % 86400) // 3600
        minutes_avg = (avg_seconds % 3600) // 60
        avg_response_time = f"{int(days_avg)}d {int(hours_avg)}h {int(minutes_avg)}m"
    else:
        avg_response_time = "N/A"

    # ─── Top 5 upvoted complaints ───
    top_complaints = complaints_qs.filter(is_hidden=False).order_by('-upvotes')[:5]

    # ─── Most active citizens ───
    from django.contrib.auth.models import User
    active_citizens = (
        User.objects
        .filter(complaint__isnull=False)
        .annotate(reports=Count('complaint'))
        .order_by('-reports')[:5]
    )

    # ─── Engagement metrics ───
    avg_comments = Comment.objects.filter(complaint__created_at__gte=start_date).count() / total_complaints if total_complaints else 0
    avg_upvotes = Vote.objects.filter(complaint__created_at__gte=start_date).count() / total_complaints if total_complaints else 0

    context = {
        'total_complaints': total_complaints,
        'total_resolved': total_resolved,
        'total_pending': total_pending,
        'total_escalated': total_escalated,
        'total_upvotes': total_upvotes,
        'total_comments': total_comments,
        'total_reposts': total_reposts,
        'total_follows': total_follows,
        'category_labels': category_labels,
        'category_counts': category_counts,
        'status_labels': status_labels,
        'status_counts': status_counts,
        'dates': dates,
        'daily_counts': daily_counts,
        'avg_response_time': avg_response_time,
        'top_complaints': top_complaints,
        'active_citizens': active_citizens,
        'avg_comments': round(avg_comments, 1),
        'avg_upvotes': round(avg_upvotes, 1),
        'selected_range': days,
    }
    return render(request, 'complaints/analytics_dashboard.html', context)

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

            notify_mentions(complaint.description, request.user, complaint)
            
            # Notify government users of new complaint
            notify_new_complaint_govt(complaint)
            
            return redirect('dashboard')
    else:
        form = ComplaintForm()
    return render(request, 'complaints/report.html', {'form': form})

def notify_mentions(text, sender, complaint):
    import re
    usernames = re.findall(r'@(\w+)', text)
    for username in usernames:
        try:
            user = User.objects.get(username=username)
            send_notification(user, f"{sender.username} mentioned you in a comment on complaint #{complaint.id}")
        except User.DoesNotExist:
            pass

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

#Display: Show repost count on complaint cards and a list of who reposted
@login_required
def repost_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    if request.method == 'POST':
        comment = request.POST.get('comment', '')
        Repost.objects.get_or_create(complaint=complaint, user=request.user, defaults={'comment': comment})
        # Update repost count (cached or via signal)
        return redirect('complaint_detail', complaint_id=complaint.id)



# Flag Report features
@login_required
def flag_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    if request.method == 'POST':
        reason = request.POST.get('reason')
        description = request.POST.get('description')
        Flag.objects.create(
            complaint=complaint,
            reported_by=request.user,
            reason=reason,
            description=description
        )
        # Notify staff / admins (could be via email or in-app)
        # Optionally, hide the complaint from public view until reviewed
        return redirect('complaint_detail', complaint_id=complaint.id)


# Escalation features
#An “Escalate” button visible on complaint details if status hasn’t progressed.
@login_required
def escalate_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    if request.method == 'POST':
        reason = request.POST.get('reason')
        target_authority = request.POST.get('target_authority')
        Escalation.objects.create(
            complaint=complaint,
            escalated_by=request.user,
            reason=reason,
            target_authority=target_authority
        )
        # Change complaint status to 'escalated'
        complaint.status = 'escalated'
        complaint.save()
        # Notify relevant authorities
        return redirect('complaint_detail', complaint_id=complaint.id)

@login_required
def toggle_follow(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    follower, created = ComplaintFollower.objects.get_or_create(complaint=complaint, user=request.user)
    if not created:
        follower.delete()  # unfollow
    return redirect('complaint_detail', complaint_id=complaint.id)


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

@login_required
def community_complaints(request):
    complaints = Complaint.objects.filter(is_hidden=False).order_by('-created_at')
    paginator = Paginator(complaints, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'complaints/community_complaints.html', {'page_obj': page_obj})



@login_required
@require_POST
def api_upvote(request):
    complaint_id = request.POST.get('complaint_id')
    complaint = get_object_or_404(Complaint, id=complaint_id)
    vote, created = Vote.objects.get_or_create(complaint=complaint, user=request.user)
    if not created:
        vote.delete()
        upvoted = False
    else:
        upvoted = True
    
    complaint.refresh_from_db()  # get fresh upvotes count
    threshold = getattr(settings, 'COMMUNITY_PRIORITY_THRESHOLD', 5)
    
    if complaint.upvotes >= threshold and complaint.status != 'community_priority':
        complaint.status = 'community_priority'
        complaint.save()
        # Notify staff
        from django.contrib.auth.models import User
        staff_users = User.objects.filter(is_staff=True)
        for staff in staff_users:
            send_notification(
                staff,
                complaint,
                'community_priority',
                f"Complaint #{complaint.id} reached {threshold} upvotes and is now a Community Priority."
            )
    
    return JsonResponse({'upvotes': complaint.upvotes, 'upvoted': upvoted})


from .models import Repost

@login_required
def toggle_repost(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    repost, created = Repost.objects.get_or_create(complaint=complaint, user=request.user)
    if not created:
        repost.delete()  # un‑repost
    else:
        # Notify complaint owner (if not the reposter)
        if complaint.citizen != request.user:
            send_notification(
                complaint.citizen,
                complaint,
                'repost',
                f"{request.user.username} reposted your complaint #{complaint.id}"
            )
    return redirect('complaint_detail', complaint_id=complaint.id)

@login_required
@require_POST
def api_repost(request):
    complaint_id = request.POST.get('complaint_id')
    complaint = get_object_or_404(Complaint, id=complaint_id)
    repost, created = Repost.objects.get_or_create(complaint=complaint, user=request.user)
    if not created:
        repost.delete()
        reposted = False
    else:
        reposted = True
        if complaint.citizen != request.user:
            send_notification(
                complaint.citizen,
                complaint,
                'repost',
                f"{request.user.username} reposted your complaint #{complaint.id}"
            )
    return JsonResponse({
        'reposted': reposted,
        'count': complaint.reposts.count()
    })

@login_required
@require_POST
def api_follow(request):
    complaint_id = request.POST.get('complaint_id')
    complaint = get_object_or_404(Complaint, id=complaint_id)
    follower, created = ComplaintFollower.objects.get_or_create(complaint=complaint, user=request.user)
    if not created:
        follower.delete()
        following = False
    else:
        following = True
    return JsonResponse({'following': following})

@login_required
@require_POST
def api_comment(request):
    complaint_id = request.POST.get('complaint_id')
    text = request.POST.get('text')
    parent_id = request.POST.get('parent_id')
    complaint = get_object_or_404(Complaint, id=complaint_id)
    parent = Comment.objects.get(id=parent_id) if parent_id else None
    comment = Comment.objects.create(
        complaint=complaint,
        author=request.user,
        text=text,
        parent=parent
    )
    # Notify owner, parent, mentions
    if complaint.citizen != request.user:
        send_notification(complaint.citizen, complaint, 'comment_added',
                          f"New comment on {complaint.id} from {request.user.username}")
    if parent and parent.author != request.user:
        send_notification(parent.author, complaint, 'comment_reply',
                          f"{request.user.username} replied to your comment")
    notify_mentions(text, request.user, complaint)
    return JsonResponse({
        'id': comment.id,
        'author': comment.author.username,
        'text': comment.text,
        'created_at': comment.created_at.strftime('%b %d, %Y %H:%M'),
        'parent_id': comment.parent.id if comment.parent else None
    })

@login_required
@require_POST
def api_flag_complaint(request):
    complaint_id = request.POST.get('complaint_id')
    reason = request.POST.get('reason')
    description = request.POST.get('description', '')
    complaint = get_object_or_404(Complaint, id=complaint_id)
    Flag.objects.create(complaint=complaint, reported_by=request.user,reason=reason, description=description)
    return JsonResponse({'status': 'flagged'})

@login_required
@require_POST
def api_flag_comment(request):
    comment_id = request.POST.get('comment_id')
    reason = request.POST.get('reason')
    description = request.POST.get('description', '')
    comment = get_object_or_404(Comment, id=comment_id)
    CommentFlag.objects.create(comment=comment, reported_by=request.user,reason=reason, description=description)
    return JsonResponse({'status': 'flagged'})


@login_required
def add_comment(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    if request.method == 'POST':
        text = request.POST.get('text')
        parent_id = request.POST.get('parent_id')
        parent = Comment.objects.get(id=parent_id) if parent_id else None
        comment = Comment.objects.create(
            complaint=complaint,
            author=request.user,
            text=text,
            parent=parent
        )
        # Notify complaint owner (if not the comment author)
        if complaint.citizen != request.user:
            send_notification(
                complaint.citizen,
                complaint,
                'comment_added',
                f"New comment on your complaint #{complaint.id}"
            )
        # Notify parent comment author (if any)
        if parent and parent.author != request.user:
            send_notification(
                parent.author,
                complaint,
                'comment_reply',
                f"{request.user.username} replied to your comment"
            )
        notify_mentions(text, request.user, complaint)
        
        return redirect('complaint_detail', complaint_id=complaint.id)


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



@login_required
def activity_feed(request):
    # Get recent complaints
    complaints = Complaint.objects.filter(is_hidden=False).order_by('-created_at')[:10]
    # Get recent comments
    comments = Comment.objects.order_by('-created_at')[:10]
    # Get recent upvotes
    votes = Vote.objects.select_related('complaint', 'user').order_by('-created_at')[:10]
    # Get recent follows
    follows = ComplaintFollower.objects.select_related('complaint', 'user').order_by('-created_at')[:10]
    reposts = Repost.objects.select_related('complaint', 'user').order_by('-created_at')[:10]
    
    activities = []
    
    for c in complaints:
        activities.append({
            'type': 'complaint',
            'created_at': c.created_at,
            'object': c,
            'message': f"{c.citizen.username} reported a new issue: {c.get_category_display()}",
            'url': f"/complaint/{c.id}/",
            'user': c.citizen,
        })
    
    for c in comments:
        activities.append({
            'type': 'comment',
            'created_at': c.created_at,
            'object': c,
            'message': f"{c.author.username} commented on complaint #{c.complaint.id}: {c.text[:50]}...",
            'url': f"/complaint/{c.complaint.id}/",
            'user': c.author,
        })
    
    for v in votes:
        activities.append({
            'type': 'upvote',
            'created_at': v.created_at,
            'object': v,
            'message': f"{v.user.username} upvoted complaint #{v.complaint.id}",
            'url': f"/complaint/{v.complaint.id}/",
            'user': v.user,
        })
    
    for f in follows:
        activities.append({
            'type': 'follow',
            'created_at': f.created_at,
            'object': f,
            'message': f"{f.user.username} started following complaint #{f.complaint.id}",
            'url': f"/complaint/{f.complaint.id}/",
            'user': f.user,
        })
    
    for r in reposts:
        activities.append({
            'type': 'repost',
            'created_at': r.created_at,
            'object': r,
            'message': f"{r.user.username} reposted complaint #{r.complaint.id}",
            'url': f"/complaint/{r.complaint.id}/",
            'user': r.user,
        })

    # Sort by created_at descending (most recent first)
    activities = sorted(activities, key=lambda x: x['created_at'], reverse=True)[:30]
    
    return render(request, 'complaints/feeds.html', {'activities': activities})



from django.utils import timezone

@login_required
def escalate_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id, citizen=request.user)  # only owner can escalate
    if complaint.status == 'resolved':
        # Cannot escalate a resolved complaint
        messages.error(request, "This complaint is already resolved.")
        return redirect('complaint_detail', complaint_id=complaint.id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, "Please provide a reason for escalation.")
            return redirect('complaint_detail', complaint_id=complaint.id)
        
        complaint.status = 'escalated'
        complaint.escalation_reason = reason
        complaint.escalated_at = timezone.now()
        complaint.escalated_by = request.user
        complaint.save()
        
        # Notify all staff users (higher authority)
        from django.contrib.auth.models import User
        staff_users = User.objects.filter(is_staff=True)
        for staff in staff_users:
            send_notification(
                staff,
                complaint,
                'escalation',
                f"Complaint #{complaint.id} has been escalated by {request.user.username}. Reason: {reason[:60]}..."
            )
        
        messages.success(request, "Complaint escalated successfully. Higher authorities have been notified.")
        return redirect('complaint_detail', complaint_id=complaint.id)
    
    # GET request: show a simple form (or redirect to detail with modal)
    return render(request, 'complaints/escalate_modal.html', {'complaint': complaint})


@login_required
def toggle_repost(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    repost, created = Repost.objects.get_or_create(complaint=complaint, user=request.user)
    if not created:
        repost.delete()  # un‑repost
        reposted = False
    else:
        reposted = True
        # Notify complaint owner (if not the reposter)
        if complaint.citizen != request.user:
            send_notification(
                complaint.citizen,
                complaint,
                'repost',
                f"{request.user.username} reposted your complaint #{complaint.id}"
            )
    return redirect('complaint_detail', complaint_id=complaint.id)


@login_required
@require_POST
def api_repost(request):
    complaint_id = request.POST.get('complaint_id')
    complaint = get_object_or_404(Complaint, id=complaint_id)
    repost, created = Repost.objects.get_or_create(complaint=complaint, user=request.user)
    if not created:
        repost.delete()
        reposted = False
    else:
        reposted = True
        # Notify complaint owner
        if complaint.citizen != request.user:
            send_notification(
                complaint.citizen,
                complaint,
                'repost',
                f"{request.user.username} reposted your complaint #{complaint.id}"
            )
    repost_count = complaint.reposts.count()
    return JsonResponse({'reposted': reposted, 'count': repost_count})


@staff_member_required
def moderation_queue(request):
    complaint_flags = Flag.objects.filter(resolved=False).select_related('complaint', 'reported_by')
    comment_flags = Flag.objects.filter(resolved=False, comment__isnull=False).select_related('comment', 'reported_by')
    return render(request, 'admin/moderation.html', {'complaints_flags': complaint_flags, 'comment_flags': comment_flags})



@staff_member_required
def resolve_flag(request, flag_id):
    flag = get_object_or_404(Flag, id=flag_id)
    action = request.POST.get('action')  # 'hide', 'delete', 'ignore'
    if action == 'hide':
        flag.complaint.is_hidden = True
        flag.complaint.save()
    elif action == 'delete':
        flag.complaint.delete()
    flag.resolved = True
    flag.save()
    return redirect('moderation_queue')



@staff_member_required
def resolve_comment_flag(request, flag_id):
    flag = get_object_or_404(Flag, id=flag_id)
    action = request.POST.get('action')  # 'delete' or 'ignore'
    if action == 'delete':
        flag.comment.delete()  # remove the offensive comment
    # 'ignore' just resolves the flag without deleting
    flag.resolved = True
    flag.save()
    return redirect('moderation_queue')