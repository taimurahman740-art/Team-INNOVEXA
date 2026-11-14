import os, secrets
from contextlib import asynccontextmanager
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from . import models
from .routes import router
from .account_routes import router as account_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        columns = {column["name"] for column in inspect(engine).get_columns("issues")}
        if "tracking_code" not in columns:
            connection.execute(text("ALTER TABLE issues ADD COLUMN tracking_code VARCHAR(32)"))
        rows = connection.execute(text("SELECT id FROM issues WHERE tracking_code IS NULL")).scalars().all()
        for issue_id in rows:
            connection.execute(text("UPDATE issues SET tracking_code = :code WHERE id = :issue_id"), {"code":"INX-"+secrets.token_hex(16).upper(),"issue_id":issue_id})
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_issues_tracking_code ON issues (tracking_code)"))
        if "assigned_staff_id" not in columns:
            connection.execute(text("ALTER TABLE issues ADD COLUMN assigned_staff_id INTEGER"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_issues_assigned_staff_id ON issues (assigned_staff_id)"))
        for name, definition in [("image_data","TEXT"),("classification_confidence","FLOAT"),("risk_score","INTEGER NOT NULL DEFAULT 0"),("risk_level","VARCHAR(20) NOT NULL DEFAULT 'Low'"),("risk_reasons","JSON NOT NULL DEFAULT '[]'")]:
            if name not in columns: connection.execute(text(f"ALTER TABLE issues ADD COLUMN {name} {definition}"))
    yield

app = FastAPI(title="INNOVEXA Smart Campus API", version="0.3.0", lifespan=lifespan)
origins = [x.strip() for x in os.getenv("FRONTEND_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET","POST","PATCH","OPTIONS"], allow_headers=["Content-Type","Authorization"])
app.include_router(router)
app.include_router(account_router)

@app.get("/")
def root(): return {"message":"INNOVEXA Smart Campus API","docs":"/docs"}

@app.get("/health")
def health():
    try:
        with engine.connect() as connection: connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc: raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status":"ok","database":"connected"}
