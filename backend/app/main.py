"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import log_function_call  # Initialize logging config
from app.api import chat, state, plans, logs

app = FastAPI(
    title="Fitnesse API",
    description="AI-driven personalized fitness and nutrition application",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router)
app.include_router(state.router)
app.include_router(plans.router)
app.include_router(logs.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Fitnesse API", "version": "0.1.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

