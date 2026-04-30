# CivicPulse

**CivicPulse** is a web application that bridges the gap between citizens and local government. It allows residents to report civic issues (roads, streetlights, flooding, waste, corruption signals, water problems) by uploading a photo, dropping a pin on a map, and writing a description. Government officials can log into a dedicated dashboard, update complaint statuses, post responses, and show resolution progress.

The goal is to create a transparent, accountable civic engagement tool – think "311 for Nigerian cities".

## Features

### Citizens
- Report issues in under 2 minutes
- Attach photo and precise location (Leaflet map)
- Track complaint status: *Reported → Under Review → In Progress → Resolved*
- View personal complaint history

### Government Officers
- Dashboard showing all complaints, sorted by date
- Update status and add official responses
- See citizen‑submitted photos and locations
- (Planned) Transparency score, budget updates, before/after photos

### Tech Stack
- **Backend**: Django (Python)
- **Database**: SQLite (development) / can be swapped for PostgreSQL + PostGIS
- **Frontend**: Bootstrap 5 + Leaflet.js (open‑street maps)
- **Authentication**: Django’s built‑in auth with role‑based dashboards (Citizen / Govt)

## Getting Started

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
4. Install dependencies: `pip install django pillow`
5. Run migrations: `python manage.py migrate`
6. Create a superuser: `python manage.py createsuperuser`
7. (Optional) Give your superuser a profile:  
   `python manage.py shell` →  
   `from complaints.models import Profile; Profile.objects.create(user=user, user_type='govt')`
8. Run the server: `python manage.py runserver`
9. Visit `http://127.0.0.1:8000/`

## Future Plans
- Add upvoting to prioritise issues
- Public map showing resolved complaints
- SMS/WhatsApp reporting for non‑internet users
- Transparency score per local government area

## License
no license
