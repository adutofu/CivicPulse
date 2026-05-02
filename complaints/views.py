from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .models import Complaint, Profile
from .forms import ComplaintForm

# ---------- Public Pages ----------
def landing_page(request):
    context = {
        'news': [
            "New road construction begins in Wuse Zone 2",
            "Flood alert: Abuja to experience heavy rains this week",
            "Monthly town hall meeting scheduled for May 10th"
        ],
        'weather': "🌤️ Partly cloudy, 28°C",
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
            complaint.latitude = request.POST.get('latitude')
            complaint.longitude = request.POST.get('longitude')
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