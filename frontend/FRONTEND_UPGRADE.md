# AKAM Health frontend upgrade — weekly operations + room registry

This frontend update adds the requested hospital operations workflow without requiring backend schema changes.

## New behavior

- **Room Registry in Settings**: define rooms (ICU, CCU, Surgery, etc.) before assigning cameras.
- **Camera creation requires a registered room**.
- Existing camera room names are automatically imported into the registry as `Imported / Unassigned` so current installations keep working.
- **Dashboard is week-based** (Monday–Sunday) and can display the current week plus 1, 2, or 3 weeks ago.
- Weekly dashboard analytics include:
  - daily hand-wash/session detections
  - compliant sessions
  - most-detected employees
  - sessions by room
- Room overview remains live and opens each room in a new browser tab.
- **Live Cameras** is a dedicated compact camera wall showing only cameras currently online across all rooms.
- Camera tiles show room, department, current user/authentication, PPE and wash state.
- **AKAM Health logo** is included in the sidebar/mobile command header.
- Camera administration remains separate from Live Cameras.

## Storage note

The FastAPI Camera model currently stores `room` but not a standalone Room table. Therefore the Room Registry and camera metadata (department/type/purpose) are stored in browser `localStorage` for now. Camera `room` itself continues to be saved to the backend, so events can still be associated with a camera and resolved to its room in the frontend.

A future backend migration can move the Room Registry into SQLite/FastAPI without changing the page structure.

## Run

```bat
cd frontend
npm install
npm run dev
```

Backend remains on `http://localhost:8080` unless `VITE_API_BASE` is changed.
