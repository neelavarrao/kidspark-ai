from dotenv import load_dotenv
import os
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Supabase configuration
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Try to query the users table
try:
    response = supabase.table("users").select("*").limit(1).execute()
    if response.data is not None:
        print("Users table exists. Found data:", response.data)
    else:
        print("Users table exists but no data found.")
except Exception as e:
    print(f"Error accessing users table: {e}")
    print("Users table might not exist. Please create it.")