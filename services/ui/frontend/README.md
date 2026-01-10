# RansomEye v1.0 SOC UI Frontend (Phase 8 - Read-Only)

**AUTHORITATIVE**: Minimal read-only frontend for Phase 8 proof-of-concept.

---

## What This Component Does

This component **ONLY** implements the minimal read-only frontend required for Phase 8 validation:

1. **Incident List**: Displays active incidents (read-only, from `v_active_incidents` view)
2. **Incident Detail View**: Displays timeline, evidence count, AI insights, policy recommendations
3. **No Edits**: No edit forms, no input fields, no save buttons
4. **No Actions**: No "acknowledge", "resolve", or "close" buttons
5. **No Action Triggers**: No buttons that execute actions

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
- Frontend only makes GET requests to backend API (no POST, PUT, DELETE, PATCH)
- UI cannot modify incidents, evidence, or any fact tables

---

## Technology Stack

- **React 18.2.0**: Frontend framework
- **Vite 5.0.0**: Build tool and dev server
- **No state management**: Simple React hooks (useState, useEffect) only
- **No forms**: No form libraries, no input validation
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

**Phase 8 requirement**: Frontend reads from backend API only (read-only).

**Endpoints Used**:
- `GET /api/incidents`: List active incidents
- `GET /api/incidents/{incident_id}`: Get incident detail

**No Writes**:
- Frontend does NOT make POST, PUT, DELETE, or PATCH requests
- Frontend does NOT send any data to backend (read-only)

---

## Component Structure

- `src/App.jsx`: Main application component (incident list and detail view)
- `src/main.jsx`: React entry point
- `index.html`: HTML template
- `vite.config.js`: Vite configuration (proxy for API)

---

## Phase 8 Limitations

**Minimal Implementation**:
- No routing (single page application)
- No authentication (Phase 8 minimal)
- No error handling UI (console errors only)
- No loading states (basic "Loading..." text)
- No pagination (displays all incidents)

These limitations do not affect Phase 8 correctness (UI is read-only, observational only).

---

**END OF README**
