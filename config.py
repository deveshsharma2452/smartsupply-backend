import os
import urllib.parse
from dotenv import load_dotenv

# Initialize tracking environment configuration
load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "allDS@#99")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "online_retail")

# Safely URL-encode the connection string password
SAFE_PASSWORD = urllib.parse.quote_plus(DB_PASSWORD)
DATABASE_URL = f"postgresql://{DB_USER}:{SAFE_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")