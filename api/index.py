"""Vercel Serverless Function entrypoint for FastAPI application."""

import sys
from pathlib import Path

# Add repository root to python search path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from web.app import app
