from supabase import create_client, Client
import os
from dotenv import load_dotenv
from functools import lru_cache

# Load environment variables
load_dotenv()

@lru_cache()
def get_supabase_client() -> Client:
    """
    Creates and returns a Supabase client.
    Uses caching for efficiency.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError("Supabase URL and key must be set in environment variables")

    return create_client(supabase_url, supabase_key)

def create_tables_if_not_exist():
    """
    Creates the necessary tables in Supabase if they don't exist.
    """
    supabase = get_supabase_client()

    # This is a simplified version. In a real application, we would use migrations
    # or a more robust way to manage database schema changes.

    # Check if users table exists and create it if it doesn't
    try:
        # Use RPC to execute SQL (not available in Python client by default)
        # This is just a placeholder. In a real app, you'd use proper migrations
        # or Supabase's SQL editor to create tables
        pass
    except Exception as e:
        print(f"Error creating tables: {e}")
        pass