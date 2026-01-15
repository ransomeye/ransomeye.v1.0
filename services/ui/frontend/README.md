# RansomEye v1.0 SOC UI Frontend (Phase 4 - Authenticated + RBAC)

**AUTHORITATIVE**: Authenticated frontend with RBAC-aware rendering.

---

## What This Component Does

This component implements authenticated, RBAC-aware read-only visibility for production:

1. **Login Flow**: Username/password login with JWT access + refresh tokens
2. **Incident List**: Displays active incidents (read-only, from `v_active_incidents` view)
3. **Incident Detail View**: Displays timeline, evidence count, AI insights, policy recommendations
4. **No Edits**: No edit forms, no input fields, no save buttons
5. **No Actions**: No "acknowledge", "resolve", or "close" buttons

---

## UI is Read-Only

**CRITICAL PRINCIPLE**: UI is **READ-ONLY** and **OBSERVATIONAL ONLY**.

**Read-Only Enforcement**:
- ❌ **NO edits**: No edit forms, no input fields, no save buttons
- ❌ **NO actions**: No "acknowledge", "resolve", or "close" buttons
- ❌ **NO action triggers**: No buttons that execute actions
- ✅ **ONLY display**: UI displays data from backend API (observational only)

**Read-Only Proof**:
- Frontend has no edit forms, no save buttons, no action buttons
- Frontend uses GET for data and POST for auth only
- UI cannot modify incidents, evidence, or any fact tables

---

## Technology Stack

- **React 18.2.0**: Frontend framework
- **Vite 5.0.0**: Build tool and dev server
- **No state management**: Simple React hooks (useState, useEffect) only
- **Minimal forms**: Login form only
- **No actions**: No action buttons, no command execution

---

## Run Instructions

### Development

```bash
# Install dependencies
npm install

# Set environment variable (optional)
export VITE_API_BASE_URL="http://localhost:8080"

# Run development server
npm run dev
```

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

---

## Environment Variables

**Optional**:
- `VITE_API_BASE_URL`: Backend API URL (default: `http://localhost:8080`)

---

## API Integration

**Phase 4 requirement**: Frontend reads from backend API only (read-only).

**Endpoints Used**:
- `POST /auth/login`: Login
- `POST /auth/refresh`: Refresh access token
- `POST /auth/logout`: Logout
- `GET /auth/permissions`: Permission list for RBAC rendering
- `GET /api/incidents`: List active incidents
- `GET /api/incidents/{incident_id}`: Get incident detail

## Authentication & Session

- Access token stored in memory (never localStorage)
- Refresh token stored in HttpOnly cookie
- Session refresh on startup and when API returns 401
- Logout revokes refresh token server-side

## RBAC Rendering

- UI sections hidden if permission missing
- Permissions loaded from `/auth/permissions`
- Backend enforcement is mandatory; UI hiding is advisory only

**No Writes**:
- Frontend does NOT make POST, PUT, DELETE, or PATCH requests beyond auth
- Frontend does NOT send any data to backend (read-only)

---

## Component Structure

- `src/App.jsx`: Main application component (incident list and detail view)
- `src/main.jsx`: React entry point
- `index.html`: HTML template
- `vite.config.js`: Vite configuration (proxy for API)

---

## Current Limitations

- No routing (single page application)
- Minimal error UI (console errors only)
- No pagination (displays all incidents)

These limitations do not affect read-only correctness (UI is observational only).

---

**END OF README**
