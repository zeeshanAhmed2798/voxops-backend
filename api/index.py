"""
api/index.py
============
Vercel serverless function entry point for VoxOps backend.

Vercel's Python runtime looks for an ASGI/WSGI app exported from this file.
We simply re-export the FastAPI app instance from app/main.py.
"""

from app.main import app  # noqa: F401 — Vercel picks up `app` automatically
