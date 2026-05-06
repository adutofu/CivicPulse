from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.db.models import Count, Q
from .models import Complaint, Profile
from .forms import ComplaintForm
from decimal import Decimal
from .models import Complaint, ComplaintImage
from .forms import ExtraImageForm # add extraimageform


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
            return redirect('dashboard')
    else:
        form = ComplaintForm()
    return render(request, 'complaints/report.html', {'form': form})

@login_required
def update_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    if request.user.profile.user_type != 'govt':
        return redirect('dashboard')
    if request.method == 'POST':
        complaint.status = request.POST.get('status')
        complaint.government_response = request.POST.get('response')
        complaint.save()
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