"""
Tradutor Técnico SaaS — FastAPI Backend
Entry point: main.py
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ─── App Instance ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Tradutor Técnico API",
    description="Backend do SaaS Multi-tenant de Tradução de Manuais Técnicos",
    version="0.1.0",
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


# ─── Routes ──────────────────────────────────────────────────────────────────
@app.get("/health", tags=["Infra"])
async def health_check():
    """Endpoint de validação de saúde do container — usado pelo Docker healthcheck."""
    return {
        "status": "healthy",
        "service": "tradutor-backend",
        "version": "0.1.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
    }


@app.get("/", tags=["Infra"])
async def root():
    return {"message": "Tradutor Técnico API está no ar 🚀"}
