"""SynQ Backend - Main Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered swing trading analysis platform",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": settings.app_version}


# Import and include routers
# from app.routers import analyses, watchlist, alerts, user, stocks
# app.include_router(stocks.router, prefix=settings.api_prefix, tags=["Stocks"])
# app.include_router(analyses.router, prefix=settings.api_prefix, tags=["Analyses"])
# app.include_router(watchlist.router, prefix=settings.api_prefix, tags=["Watchlist"])
# app.include_router(alerts.router, prefix=settings.api_prefix, tags=["Alerts"])
# app.include_router(user.router, prefix=settings.api_prefix, tags=["User"])
