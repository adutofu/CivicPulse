# CivicPulse React Frontend

This is the React Single Page Application (SPA) for CivicPulse.

## Setup Instructions

### 1. Install Node.js & npm
If not already installed:
```bash
# macOS with Homebrew
brew install node

# Ubuntu/Debian
sudo apt-get install nodejs npm

# Windows
# Download from https://nodejs.org/
```

### 2. Install Dependencies
```bash
cd frontend
npm install
```

### 3. Create .env File
Create a `.env` file in the `frontend` directory:
```
VITE_API_BASE_URL=http://localhost:8000/api
```

### 4. Run Development Server
```bash
npm run dev
```

The app will run on `http://localhost:5173`

Vite is configured to proxy `/api` requests to the Django backend at `http://localhost:8000`.

### 5. Build for Production
```bash
npm run build
```

This creates an optimized build in the `dist/` folder ready for deployment.

## Project Structure

```
frontend/
├── src/
│   ├── components/       # Reusable UI components
│   ├── pages/           # Page components (Login, Dashboard, etc.)
│   ├── services/        # API client & services
│   ├── context/         # React Context for state (Auth, etc.)
│   ├── styles/          # CSS files & theme
│   ├── App.jsx          # Main app component
│   └── main.jsx         # React entry point
├── index.html           # HTML template
├── vite.config.js       # Vite configuration
└── package.json         # Dependencies
```

## Features Being Built

- ✅ Auth (Login/Signup with JWT)
- ✅ API Client with token management
- ⏳ Citizen Dashboard
- ⏳ Report Complaint Form
- ⏳ Community Voting Feed
- ⏳ Government Dashboard
- ⏳ Notifications
- ⏳ Map Integration (React-Leaflet)

## API Integration

All API calls go through `src/services/apiClient.js` which handles:
- JWT token attachment
- CORS
- Error handling
- Token refresh (when implemented)

## Styling

- CSS Variables defined in `src/styles/globals.css`
- Theme colors match original Django templates
- Responsive design for mobile/tablet/desktop
- Can be extended with Tailwind CSS

## Next Steps

1. Run `npm install` to install all dependencies
2. Start dev server: `npm run dev`
3. Test login at `http://localhost:5173/login`
4. Build components for all pages
5. Test against Django backend API
