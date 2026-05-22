"""
Tradutor Técnico SaaS — FastAPI Backend
Entry point: main.py — v0.2.0
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.documentos import router as documentos_router
from app.routers.documentos import glossario_router

# ─── App Instance ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Tradutor Técnico API",
    description="Backend do SaaS Multi-tenant de Tradução de Manuais Técnicos",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ────────────────────────────────────────────────────────────────────
allowed_origins_raw = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,https://tradutor.transformafuturo.com.br",
)
allowed_origins = [o.strip() for o in allowed_origins_raw.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(documentos_router, prefix="/api/v1")
app.include_router(glossario_router,  prefix="/api/v1")


# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/health", tags=["Infra"])
async def health_check():
    return {
        "status": "healthy",
        "service": "tradutor-backend",
        "version": "0.2.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
    }


@app.get("/", tags=["Infra"])
async def root():
    return {"message": "Tradutor Técnico API v0.2.0 🚀"}
