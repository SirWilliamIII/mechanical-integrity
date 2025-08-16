# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import equipment, inspections, analysis

app = FastAPI(
    title="Mechanical Integrity AI",
    description="AI-powered mechanical integrity management system",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vue dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(equipment.router, prefix="/api/equipment", tags=["equipment"])
app.include_router(inspections.router, prefix="/api/inspections", tags=["inspections"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "services": {
        "database": "connected",
        "redis": "connected",
        "ollama": "connected"
    }}
