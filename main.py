"""
TradeFlow Journal - FastAPI Application Entry Point
Configures CORS, mounts all routers, and starts the ASGI server.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, Base
from app.routers import auth, trades, dashboard, charts, ai


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup (dev only - use Alembic in prod)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="TradeFlow Journal API",
    description="Professional Trading Journal Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://trade-flow-frontend.vercel.app"], # Your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(trades.router, prefix="/trades", tags=["Trades"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(charts.router, prefix="/trades", tags=["Charts"])
app.include_router(ai.router, prefix="/ai", tags=["AI Chatbot"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
