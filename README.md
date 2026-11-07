<div align="center">

# 🏙️ CivicPulse

**A community-driven civic issue reporting and accountability platform for Nigeria.**

Report it. Track it. Get it fixed.

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-DRF-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![PostGIS](https://img.shields.io/badge/PostGIS-3.4-336791)
![Status](https://img.shields.io/badge/status-MVP-brightgreen)

[· [Screenshots](#-screenshots) · [Getting Started](#-getting-started) · [Roadmap](#-roadmap)

</div>

---

## 📖 About

Citizens across Nigeria run into broken roads, failed streetlights, uncollected waste and water problems every day, but have no reliable way to report them or see whether anyone acted. Government agencies, in turn, receive complaints through scattered, untracked channels (calls, social media, word of mouth) that are hard to prioritise.

**CivicPulse** replaces that with a transparent, auditable process:

- **Citizens** report an issue with a photo, description, category and location, then follow it through to resolution.
- **Government officials** get a scoped dashboard to review, prioritise and respond to complaints in their coverage area.
- **Admins** moderate content, verify officials and oversee the whole platform.

The pilot area is **Ibadan, Oyo State**.

> CivicPulse is a non-emergency reporting tool. For emergencies, contact the relevant emergency services directly.

---

## ✨ Features

### For citizens
- 📸 Submit complaints with photo(s), description, category and location
- 📍 Automatic location capture via browser geolocation, with manual map fallback
- 🗺️ Automatic **ward detection** from the reported coordinates (PostGIS)
- 👍 Community upvoting to surface high-impact issues and reduce duplicates
- 💬 Nested comment threads on complaints
- 🔔 In-app notifications when a report's status changes
- 🏆 Leaderboard of active contributors
- 👤 Profile with engagement history, picture, bio and role-aware settings

### For government officials
- 🧭 Dashboard scoped to the official's assigned coverage area (wards)
- 🔎 Review complaints, update status, add responses and resolution photos
- 🗺️ Coverage map of assigned areas

### For admins
- 🛡️ Separate admin dashboard with platform-wide statistics
- 🧹 Moderation queue and government application review
- 👥 User management (activate / deactivate) and CSV export
- Full Django admin registration of all core models

### Platform
- 🌍 GeoDjango + PostGIS with a ward boundary layer (GRID3 dataset)
- 🔐 Role-based access control (citizen / government / admin)
- 🎨 Light glassmorphism design system with reusable components
- 📊 Live landing-page statistics, map preview and weather widget (Open-Meteo)

---

## 🔄 How It Works

| Stage | What happens | Actor |
| --- | --- | --- |
| 1. Report | Citizen submits a complaint with evidence and location | Citizen |
| 2. Validate | Others upvote and comment | Community |
| 3. Route | Complaint is matched to a ward / coverage area | System |
| 4. Respond | Official updates status and attaches progress or resolution evidence | Government |
| 5. Notify | Citizen is notified of each status change | System |

Status lifecycle: **Pending → Acknowledged → In Progress → Resolved**

---

## 🛠️ Tech Stack

| Layer | Technology |
| --- | --- |
| Language | Python |
| Backend | Django, Django REST Framework |
| Database | PostgreSQL 16 + PostGIS 3.4 (SQL, spatial queries via GeoDjango) |
| Geospatial data | GRID3 / HDX Nigeria ward boundaries |
| Config | `django-environ` (`.env`) |
| Frontend | Django templates, custom CSS design system, vanilla JavaScript |
| Mapping | Leaflet.js |
| Icons | Ionicons v7 |
| Weather | Open-Meteo API |

---

## 📸 Screenshots

> Add screenshots to a `docs/screenshots/` folder and update the paths below.

| Landing page | Report an issue |
| --- | --- |
| ![Landing](docs/screenshots/landing.png) | ![Report](docs/screenshots/report.png) |

| Citizen dashboard | Government dashboard |
| --- | --- |
| ![Citizen](docs/screenshots/citizen-dashboard.png) | ![Government](docs/screenshots/govt-dashboard.png) |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.x
- PostgreSQL 16 with the **PostGIS 3.4** extension
- GDAL / GEOS system libraries (required by GeoDjango)
- Git

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install postgresql postgis gdal-bin libgdal-dev libgeos-dev
```

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/CivicPulse.git
cd CivicPulse
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Create the database

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE civicpulse;
CREATE USER civicpulse_user WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE civicpulse TO civicpulse_user;
\c civicpulse
CREATE EXTENSION postgis;
```

### 4. Configure environment variables

Create a `.env` file in the project root (next to `manage.py`):

```env
SECRET_KEY=your-generated-secret-key
DEBUG=True
DATABASE_URL=postgis://civicpulse_user:your-password@localhost:5432/civicpulse
```

Generate a secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

> Never commit `.env`. Make sure it is listed in `.gitignore`.

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Load ward boundary data

CivicPulse uses the GRID3 ward boundary dataset to detect the ward of each complaint.

```bash
# TODO: add the exact command / script used to load the ward data
```

> Current dataset coverage: 15 of 37 states, including **Oyo** (the pilot area). Outside covered states, ward detection returns nothing and the manual address field is used as a fallback.

### 7. Create a superuser

```bash
python manage.py createsuperuser
```

### 8. Start the development server

```bash
python manage.py runserver
```

Open <http://127.0.0.1:8000>.

---

## 👥 User Roles

| Role | Capabilities |
| --- | --- |
| **Citizen** | Report, track, upvote, comment, receive notifications, appear on the leaderboard |
| **Government official** | Manage complaints within an assigned coverage area, update status, add responses |
| **Admin** | Moderate content, review government applications, manage users, export data |

Role routing: staff accounts always take priority over `user_type` when routing to dashboards. Government accounts are soft-deactivated (never hard-deleted) to preserve the audit trail.

---

## 📁 Project Structure

```
CivicPulse/
├── civicpulse/          # Project settings, URLs, ASGI/WSGI
├── complaints/          # Main app
│   ├── models.py        # Complaint, Ward, Notification, etc.
│   ├── views.py         # Page views
│   ├── api_views.py     # REST API views
│   ├── api_urls.py      # API routes
│   ├── serializers.py   # DRF serializers
│   ├── forms.py
│   ├── signals.py
│   ├── management/commands/
│   ├── templatetags/
│   └── templates/complaints/
├── templates/registration/   # Login & signup
├── static/                   # Static assets
├── media/                    # User uploads (not committed)
├── manage.py
└── requirements.txt
```

---

## 🧪 Testing

```bash
python manage.py test
```

---

## 🗺️ Roadmap

- [x] Citizen, government and admin roles
- [x] Complaint reporting, upvoting, nested comments, notifications
- [x] PostGIS migration with ward boundary detection
- [x] Admin dashboard, moderation and CSV export
- [ ] Contractor assignment and issue-progress tracking
- [ ] Full national ward coverage (all 37 states)
- [ ] Structured Agency model
- [ ] Celery + Redis task queue
- [ ] SMS / email gateway
- [ ] Two-factor authentication for staff
- [ ] Public deployment
- [ ] Accessibility review (WCAG)

---

## 🤝 Contributing

Contributions, issues and feature requests are welcome.

1. Fork the repository
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 🙏 Acknowledgements

- [GRID3](https://grid3.org/) / HDX for Nigeria ward boundary data
- [Open-Meteo](https://open-meteo.com/) for the weather API
- [Leaflet](https://leafletjs.com/) and [Ionicons](https://ionic.io/ionicons)
- Inspiration from Japan's *My City Report*, Decidim and similar civic-tech platforms

---

## 👤 Author

**Aduroja Oluwatofunmi**
Full-Stack Developer (Python / Django)

- Portfolio: [aduroja-portfolio.onrender.com](https://aduroja-portfolio.onrender.com)
- GitHub: [@your-username](https://github.com/your-username)
- LinkedIn: [your-profile](https://linkedin.com/in/your-profile)

---

## 📄 License

Add a license (for example MIT) by creating a `LICENSE` file, then update this section.
