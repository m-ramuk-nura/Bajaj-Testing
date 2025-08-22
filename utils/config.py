import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEYS = os.getenv("GOOGLE_API_KEYS") or os.getenv("GOOGLE_API_KEY")
