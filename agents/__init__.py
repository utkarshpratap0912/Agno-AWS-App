# agents/__init__.py
from dotenv import load_dotenv
from pathlib import Path
import os

# Load .env from project root (2 levels up from agents/)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path, override=True)  # Explicit path ensures reliability

assert os.getenv("OPENAI_API_KEY"), "OPENAI_API_KEY not loaded from .env!"

