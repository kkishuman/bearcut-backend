from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import STORAGE_DIR, VIDEOS_DIR, KEYFRAMES_DIR, AUDIO_DIR, THUMBS_DIR
from app.database import engine, Base
from app.routers import projects, clips, analysis, storyline, preferences


def _migrate():
    """Idempotent ALTER TABLE migrations for new columns."""
    migrations = {
        "edit_plans": [
            ("clip_summary", "TEXT"),
            ("purpose", "TEXT"),
        ],
    }
    with engine.connect() as conn:
        for table, cols in migrations.items():
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            for name, ddl in cols:
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
        conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _migrate()
    for d in (STORAGE_DIR, VIDEOS_DIR, KEYFRAMES_DIR, AUDIO_DIR, THUMBS_DIR):
        d.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="BearCut", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(clips.router)
app.include_router(analysis.router)
app.include_router(storyline.router)
app.include_router(preferences.router)


@app.get("/health")
def health():
    return {"status": "ok"}
