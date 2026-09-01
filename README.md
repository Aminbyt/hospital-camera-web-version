# AKAM Health — Smart Scrub Vision

AI-powered hospital hand-hygiene and PPE compliance monitoring. Web-based
rewrite of the original PyQt5 desktop kiosk app — same computer-vision
pipeline, ported line-for-line where it mattered, running behind a FastAPI
backend and a React frontend instead of a single-machine Qt app.

Each camera watches one hand-wash sink and, for every staff member who
steps up:

1. **Face recognition** (InsightFace, `antelopev2`) identifies them against
   a photo database and logs them in.
2. **PPE detection** (YOLOv8, OpenVINO-exported) checks for mask and
   surgical hat.
3. **Hand tracking** (MediaPipe Hands) watches for two-hand scrubbing
   inside a calibrated sink zone.
4. **WHO step classification** (a CNN‑LSTM ONNX model) scores which of the
   6 WHO hand-washing steps are being performed, over a rolling 30-frame
   window.
5. On logout, the visit is written to the `events` table and a Bale bot
   notification is sent.

The web rewrite adds: a dynamic camera registry (add/remove/edit cameras
from Settings, no code changes or restarts), a live settings store
(thresholds editable at runtime), MJPEG streaming to the browser, and a
browser-based ROI drawer that replaces the old PyQt calibration dialog.

---

## Architecture

```
┌───────────────────────┐        HTTP / MJPEG        ┌──────────────────────────────┐
│  Frontend (Vite/React) │ ─────────────────────────▶ │  Backend — FastAPI (Uvicorn)  │
│  :5173                 │ ◀───────────────────────── │  :8080                        │
└───────────────────────┘        JSON REST API        └──────────────┬────────────────┘
                                                                      │
                     ┌────────────────────────────────────────────────┼────────────────────────────────────┐
                     │                                                │                                    │
            ┌────────▼────────┐                            ┌─────────▼──────────┐                ┌─────────▼─────────┐
            │  SQLite (app.db)  │                            │  camera_manager     │                │  scheduler (APS)   │
            │  Camera / Event /  │                            │  one CameraStream   │                │  heartbeat (1h),   │
            │  AlertLog /        │                            │  thread per enabled │                │  daily summary,    │
            │  SettingKV         │                            │  camera             │                │  monthly report    │
            └────────────────────┘                            └─────────┬───────────┘                └─────────────────────┘
                                                                          │
                                                                ┌─────────▼──────────┐
                                                                │   AI pipeline (ai/)  │
                                                                │  InsightFace ·        │
                                                                │  YOLOv8 (OpenVINO) ·  │
                                                                │  MediaPipe Hands ·    │
                                                                │  WHO CNN-LSTM (ONNX)  │
                                                                └───────────────────────┘
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router 6, Vite 5, plain CSS |
| Backend | FastAPI, Uvicorn, SQLAlchemy, SQLite, `pydantic-settings`, APScheduler, `pandas` (Excel export) |
| Face recognition | InsightFace (`antelopev2`), ONNX Runtime, CPUExecutionProvider |
| PPE detection | Ultralytics YOLOv8, exported to OpenVINO IR |
| Hand tracking | MediaPipe Hands + MediaPipe Face Detection |
| WHO step classifier | Custom CNN‑LSTM, exported to ONNX |
| Notifications | Bale bot API (`sendMessage` / `sendDocument`) |
| Streaming | MJPEG over HTTP |

---

## Repository layout

```
backend/
└── app/
    ├── main.py                    # app factory, CORS, router registration, startup/shutdown
    ├── config.py                  # EnvSettings (.env) + DEFAULT_SETTINGS seed values
    ├── database.py                # SQLAlchemy engine/session, Base
    ├── models.py                  # Camera, Event, AlertLog, SettingKV
    ├── schemas.py                 # Pydantic request/response models
    ├── routers/
    │   ├── cameras.py             # CRUD + calibrate + status  → /api/cameras
    │   ├── stream.py              # MJPEG feed                → /api/stream/sink/{id}/live
    │   ├── events.py              # history + Excel export     → /api/events
    │   ├── alerts.py              # bot notification log       → /api/alerts
    │   ├── settings.py            # live settings               → /api/settings
    │   └── registration.py        # staff face capture          → /api/registration
    ├── services/
    │   ├── camera_manager.py      # dynamic registry: start/stop/restart CameraStream per camera
    │   ├── camera_worker.py       # CameraStream — ported CameraWorker main loop
    │   ├── data_logger.py         # DataLogger + UserSessionManager
    │   ├── settings_store.py      # DB-backed live config, cached in memory
    │   └── scheduler.py           # heartbeat / daily / monthly APScheduler jobs
    └── ai/
        ├── ai_models.py           # InsightFace + YOLO + MediaPipe + WHO ONNX
        ├── hand_wash_detector.py  # bubble-zone + WHO step timing logic
        └── sink_calibration.py    # auto-detect sink line (Hough transform)

frontend/
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── main.jsx
    ├── App.jsx                    # router + layout (Sidebar + Topbar + page outlet)
    ├── styles.css                 # AKAM Health dark theme design system
    ├── api/
    │   └── client.js              # fetch wrapper — the real API contract
    ├── components/
    │   ├── Sidebar.jsx
    │   ├── Topbar.jsx
    │   ├── CameraCard.jsx
    │   └── RoiDrawer.jsx          # browser-based scrub-zone drawing
    ├── pages/
    │   ├── Dashboard.jsx          # ward-wide KPI overview + camera grid
    │   ├── LiveCameras.jsx        # all cameras, filterable
    │   ├── CameraDetail.jsx       # single camera: live feed, AI status, recent sessions
    │   ├── Alerts.jsx
    │   ├── Events.jsx             # filterable visit history + Excel export
    │   └── Settings.jsx           # camera CRUD, detection defaults, thresholds, bot config, staff registration
    └── utils/
        └── compliance.js          # shared "is this visit compliant" rule
```

---

## Prerequisites

- Python 3.10–3.11 (match whatever your `insightface` / `onnxruntime` /
  `mediapipe` builds were installed against)
- Node.js 18+ and npm
- Model artifacts, placed where `config.py` expects them:
  - `YOLO_MODEL_PATH` (default `./models/best_openvino_model/`) — YOLOv8 PPE detector, OpenVINO export
  - `WHO_MODEL_PATH` (default `./models/who_cnn_lstm_model.onnx`) — WHO step classifier
  - InsightFace `antelopev2` pack, auto-downloaded to `~/.insightface/models/antelopev2/` on first run
- A `REGISTER_PERSONS` folder of staff reference photos under `DATA_ROOT`
  (one subfolder per person, `FIRST_LAST/angle_1.jpg`, `angle_2.jpg`, …,
  optionally a `user_info.json` with `{"role": "..."}`)

---

## Setup

### Backend

```bash
cd backend
python -m venv exe_env
exe_env\Scripts\activate          # Windows
pip install -r requirements.txt
```

`.env` (all optional — defaults shown are from `config.py`):

```
DATA_ROOT=./data
DATABASE_URL=sqlite:///./data/hospital_ai.db
YOLO_MODEL_PATH=./models/best_openvino_model/
WHO_MODEL_PATH=./models/who_cnn_lstm_model.onnx
FRONTEND_ORIGIN=http://localhost:5173
BOT_API_URL=
BOT_CHAT_ID=
BOT_TIMEOUT=3
```

> `FRONTEND_ORIGIN` is read but not currently applied — `main.py` hardcodes
> `allow_origins=["*"]` on the CORS middleware. Harmless for local dev since
> no cookies/auth are used; worth wiring up if you ever tighten this.

Run it:

```bash
uvicorn app.main:app --reload --port 8080
```

⚠️ See **Known issues** below before using `--reload` with real cameras —
it's the likely cause of the multi-minute stalls in your log.

Bot credentials, wash thresholds, and detection defaults are **not** set
via `.env` — they're seeded from `DEFAULT_SETTINGS` into the `settings`
table on first boot and from then on are only editable live from the
Settings page (`GET`/`PUT /api/settings`).

### Frontend

```bash
cd frontend
npm install
```

```
# frontend/.env
VITE_API_BASE=http://localhost:8080
```

```bash
npm run dev      # http://localhost:5173
npm run build    # production build → frontend/dist
```

---

## Data model

Four tables, replacing the old per-user + master-daily Excel files:

- **Camera** — `id`, `name` (unique), `source` (webcam index or RTSP/HTTP
  URL), `enabled`, **`room`** (free-text location label), `check_mask`,
  `check_hat`, `check_wash`, `manual_roi` (normalized `[x1,y1,x2,y2]`),
  `sink_y_start`.
- **Event** — one row per completed visit: `camera_id`/`camera_name`,
  `date`, `time`, `first_name`, `last_name`, `role`, `mask`/`hat`/
  `washing_complete`/`all_who_steps` (`"YES"`/`"NO"`), `wash_duration`.
- **AlertLog** — one row per bot notification: `camera_name`, `message`,
  `level` (`info`/`warning`/`error` — **currently always `"info"`, see
  Known issues**), `delivered`.
- **SettingKV** — key/value store backing the live Settings page.

---

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/cameras` | List all cameras (with live `connected` status) |
| POST | `/api/cameras` | Create a camera — starts it immediately if `enabled` |
| PATCH | `/api/cameras/{id}` | Update a camera; applies toggles/ROI/enable live, restarts the stream if `source`/`name` changed |
| DELETE | `/api/cameras/{id}` | Stop and remove a camera |
| POST | `/api/cameras/{id}/calibrate` | Clear manual ROI, fall back to auto zone |
| GET | `/api/cameras/{id}/status` | Live AI status (auth, mask, hat, wash timer, master_ready) |
| GET | `/api/stream/sink/{id}/live` | MJPEG video stream — **see Known issues, frontend calls the wrong path** |
| GET | `/api/events` | Filterable visit history (`camera_id`, `date_from`, `date_to`, `user`, `compliant_only`) |
| GET | `/api/events/export` | Excel export of the same filtered set |
| GET | `/api/alerts` | Bot notification log (`limit`, default 100) |
| GET | `/api/settings` | Current live thresholds/defaults |
| PUT | `/api/settings` | Update thresholds/defaults; applies detection-default toggles to all running cameras |
| POST | `/api/registration/capture` | Grab the current live frame from a camera and save it as a new staff reference photo |
| GET | `/api/registration/staff` | List registered staff + photo counts |
| POST | `/api/registration/reset-cache` | Force-rebuild the face embedding cache |

---

## Known issues

1. **Camera feeds 404 — frontend/backend route mismatch (confirmed).**
   `frontend/src/api/client.js` builds stream URLs as `/api/stream/{id}`,
   but `stream.py` only registers `/api/stream/sink/{id}/live`. Every
   `<img>` tag pointed at a camera feed gets a 404, forever — this is
   exactly the `GET /api/stream/1 404 Not Found` / `GET /api/stream/2 404`
   lines in your log. Fix is one line on either side: change
   `client.js`'s `streamUrl()` to match the real path, or add a matching
   `@router.get("/{camera_id}")` alias in `stream.py`. Say the word and
   I'll make the change.

2. **`--reload` likely causes the multi-minute stalls you saw when adding
   a camera (probable, not yet confirmed).** `DATA_ROOT` defaults to
   `./data`, inside the same backend folder `uvicorn --reload` watches
   with WatchFiles. Every camera you add writes to the SQLite DB under
   `data/`; every face captured writes a photo and rewrites
   `face_cache.pkl`. Any of those look like a source change to the
   reloader, which restarts the whole process — wiping the in-memory
   InsightFace cache, the loaded YOLO/MediaPipe models, and every running
   camera thread. That forces a full "first time" 60-person face database
   rebuild and camera reconnect on the *next* request, which is what
   produced the repeated `[INFO] Building face database (first time)...`
   blocks and cascading `[WATCHDOG] stream hung, restarting...` warnings
   in your log. Fix: run with `--reload-dir app` (only watch source, not
   `data/`), or point `DATA_ROOT` outside the backend source tree during
   development, or simply don't use `--reload` once cameras are running.

3. **Alert severity infrastructure exists but is unused.** `AlertLog.level`
   and `AlertOut.level` are already there — no schema change needed to add
   real Critical/Attention/Informational grouping to the Alerts page.
   `data_logger.send_bot_notification()` just always writes `level="info"`.
   Wiring this up is a `data_logger.py` change (set level from what
   triggered the alert) plus a small frontend grouping change.

4. **`room` is fully supported on the backend but not exposed in the
   frontend's "Add a camera" form.** `Camera.room`, `CameraCreate.room`,
   `CameraUpdate.room`, and `CameraOut.room` are all there — the Settings
   page just doesn't have an input for it yet, so every camera has
   `room = null` today. Quick frontend-only addition.

---

## Roadmap

- [ ] Fix the `/api/stream` path mismatch (frontend or backend, one line)
- [ ] Exclude `data/` from the `--reload` watch, or relocate `DATA_ROOT`,
      to stop the face-cache/camera-thread resets during dev
- [ ] Add a `room` input to the "Add a camera" form and show it on camera
      cards
- [ ] Set real `level` values on alerts and group Alerts by severity in
      the UI
- [ ] Surface "camera warming up" distinctly from "offline" once streaming
      is fixed

---

## Credits

Ported from the original PyQt5 desktop kiosk. All detection algorithms —
face recognition, PPE detection, hand-wash bubble-zone logic, WHO step
classification, sink auto-calibration — are unchanged from the original;
only the application layer (Qt → FastAPI/React, hardcoded config → live
DB-backed settings, Excel logging → SQLite) was rewritten.
