import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import env, ensure_directories
from app.database import Base, engine
from app.services import settings_store, camera_manager, scheduler
from app.routers import cameras, stream, events, alerts, settings as settings_router, registration

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")

ensure_directories()
Base.metadata.create_all(bind=engine)
settings_store.seed_defaults()

app = FastAPI(title="Hospital Camera AI")

# NOTE: allow_origins=["*"] + allow_credentials=True is invalid per the CORS spec
# and browsers will silently reject it. We don't use cookies/auth here, so
# allow_credentials stays False and "*" is fine for local dev. If you later add
# cookie-based auth, switch this back to an explicit origin list and set
# allow_credentials=True.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cameras.router)
app.include_router(stream.router)
app.include_router(events.router)
app.include_router(alerts.router)
app.include_router(settings_router.router)
app.include_router(registration.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def on_startup():
    logging.info("Starting camera workers for all enabled cameras...")
    camera_manager.start_all_enabled()
    scheduler.start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    camera_manager.stop_all()
    scheduler.stop_scheduler()