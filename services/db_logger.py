from datetime import datetime
from supabase import create_client, Client
import requests

from utils.config import SUPABASE_URL, SUPABASE_KEY 

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_geo_location(ip: str) -> str:
    try:
        if ip.startswith("127.") or ip.lower() == "localhost":
            return "Localhost"
        resp = requests.get(f"https://ipapi.co/{ip}/json/", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            city = data.get("city")
            region = data.get("region")
            country = data.get("country_name")
            parts = [part for part in [city, region, country] if part]
            return ", ".join(parts) if parts else "Unknown"
    except Exception:
        pass
    return "Unknown"



def log_query(document_source: str, question: str, answer: str,
              ip_address: str, response_time,
              user_agent: str = None):
    """Insert Q&A log into Supabase with IP, Geo, and User Agent."""
    now_str = datetime.utcnow().isoformat()
    geo_location = get_geo_location(ip_address)

    try:
        response_time_sec = round(float(response_time), 2)
    except (TypeError, ValueError):
        response_time_sec = 0.0

    try:
        supabase.table("qa_logs").insert({
            "document_source": document_source,
            "question": question,
            "answer": answer,
            "ip_address": ip_address,
            "geo_location": geo_location,
            "user_agent": user_agent or "Unknown",
            "response_time_sec": response_time_sec,
            "created_at": now_str
        }).execute()
    except Exception as e:
        print(f"Failed to log query to Supabase: {e}")

