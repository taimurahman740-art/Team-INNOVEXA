import os
from contextlib import asynccontextmanager
from sqlalchemy import inspect, text
from fastapi import FastAPI
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
    return {"status": "ok"}
