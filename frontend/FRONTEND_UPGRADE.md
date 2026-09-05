# AKAM HEALTH Smart Scrub Vision — Frontend Upgrade

Implemented from the command-center UI specification:

- Dark clinical enterprise design system and command-center top bar
- Sidebar: Dashboard, Rooms, Cameras, Alerts, Events, Settings + backend/AI health
- Hospital → Department → Room → Camera hierarchy
- Dashboard KPI overview before room monitoring
- Dedicated Rooms page grouped by department
- Dedicated Room Monitoring page with camera filters and rich live cards
- Room and camera navigation opens in new browser tabs
- Breadcrumbs on detailed monitoring pages
- Expanded Camera Detail / AI status workspace
- Dedicated Cameras management page with add/edit/enable/disable/delete/test connection
- Expanded camera fields in UI: type, department, room, floor/area, purpose
- Alerts grouped into Critical / Attention / Informational
- Events filters for department, room, camera, user and compliance; pagination and detail modal
- Settings visual organization for cameras, AI detection, face/wash, notifications and staff

## Frontend-only metadata

The existing backend Camera schema only persists `name`, `source`, `room`, enabled state and detection toggles. Department, floor/area, camera type and purpose are therefore stored in browser localStorage for now under `akam-smart-scrub-camera-meta-v1`.

This keeps the current FastAPI API fully compatible. A future backend migration can move these fields into SQLite without changing the new UI hierarchy.

## Backend limitations shown conservatively in UI

- The camera status API does not expose a dedicated WHO step count or session timestamps. The UI does not invent those values; final readiness is used as the completed state.
- Alert `level` is currently generally `info`; obvious offline/missing/incomplete alert messages are categorized visually until backend severity is wired explicitly.
