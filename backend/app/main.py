import os
from contextlib import asynccontextmanager
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from . import models
from .routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Additive migration for existing Render databases; existing reports are preserved.
    with engine.begin() as connection:
        columns = {column["name"] for column in inspect(engine).get_columns("issues")}
        if "image_data" not in columns:
            connection.execute(text("ALTER TABLE issues ADD COLUMN image_data TEXT"))
        if "classification_confidence" not in columns:
            connection.execute(text("ALTER TABLE issues ADD COLUMN classification_confidence FLOAT"))
        if "risk_score" not in columns:
            connection.execute(text("ALTER TABLE issues ADD COLUMN risk_score INTEGER NOT NULL DEFAULT 0"))
        if "risk_level" not in columns:
            connection.execute(text("ALTER TABLE issues ADD COLUMN risk_level VARCHAR(20) NOT NULL DEFAULT 'Low'"))
        if "risk_reasons" not in columns:
            connection.execute(text("ALTER TABLE issues ADD COLUMN risk_reasons JSON NOT NULL DEFAULT '[]'"))
    yield

app = FastAPI(title="INNOVEXA Smart Campus API", version="0.2.0", lifespan=lifespan)
origins = [x.strip() for x in os.getenv("FRONTEND_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "OPTIONS"], allow_headers=["Content-Type", "Authorization", "X-Staff-Key"])
app.include_router(router)

@app.get("/")
def root():
    return {"message": "INNOVEXA Smart Campus API", "docs": "/docs"}

@app.get("/health")
def health():
    """Report healthy only when the application can reach its database."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok", "database": "connected"}
