"""
Central configuration for the RAG PDF Chatbot.

All tunable settings live here so the rest of the codebase never
hardcodes a path, model name, or threshold. Import this module instead
of re-reading environment variables in multiple places.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# -----------------------------------
# Load Environment Variables
# -----------------------------------
load_dotenv()

# -----------------------------------
# Paths
# -----------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
PDF_DIR = DATA_DIR / "pdfs"
IMAGE_DIR = DATA_DIR / "extracted_images"

FAISS_DIR = BASE_DIR / "faiss_index"
MANIFEST_PATH = DATA_DIR / "processed_documents.json"

PDF_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
FAISS_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------
# API Configuration
# -----------------------------------
# GOOGLE_API_KEY is read lazily via get_google_api_key() so the app can
# show a friendly setup screen instead of crashing on import when the
# key is missing.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


def get_google_api_key() -> str | None:
    """Return the configured Google API key, re-reading the environment
    in case it was set after this module was first imported. Trims
    surrounding whitespace so a stray space/newline from copy-pasting
    the key doesn't cause an opaque authentication failure."""
    key = os.getenv("GOOGLE_API_KEY")
    if key is None:
        return None
    key = key.strip()
    return key or None


# -----------------------------------
# Gemini Models
# -----------------------------------
# "gemini-flash-latest" and "gemini-embedding-001" are Google's rolling
# aliases for their current-generation stable Flash and embedding
# models. Using the alias (rather than a dated model id such as
# "gemini-2.0-flash") means this project keeps working as Google
# retires older dated model versions, without needing code changes.
LLM_MODEL = "gemini-flash-latest"

EMBEDDING_MODEL = "gemini-embedding-001"

# -----------------------------------
# Chunking Configuration
# -----------------------------------
CHUNK_SIZE = 1000

CHUNK_OVERLAP = 150

# -----------------------------------
# Retrieval Configuration
# -----------------------------------
TOP_K_RESULTS = 4

# -----------------------------------
# Image Configuration
# -----------------------------------
MIN_IMAGE_WIDTH = 120

MIN_IMAGE_HEIGHT = 120

# -----------------------------------
# Project Information
# -----------------------------------
PROJECT_NAME = "RAG PDF Chatbot"

VERSION = "2.1.0"


def check_setup() -> list[str]:
    """
    Run basic environment checks and return a list of human-readable
    problem descriptions. An empty list means the app is ready to run.
    Used by app.py to show a setup screen instead of a stack trace.
    """
    issues = []

    if not get_google_api_key():
        issues.append(
            "No GOOGLE_API_KEY found. Create a `.env` file in the "
            "project root (copy `.env.example`) and paste in a key "
            "from https://aistudio.google.com/apikey."
        )

    return issues
