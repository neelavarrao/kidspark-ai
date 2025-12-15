import json
import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# Initialize Supabase client
# Replace with your Supabase URL and anon key or set them as environment variables
supabase_url = os.environ.get("SUPABASE_URL", "your_supabase_url")
supabase_key = os.environ.get("SUPABASE_KEY", "your_supabase_anon_key")

# Create Supabase client
supabase = create_client(supabase_url, supabase_key)

def load_activities():
    try:
        # Read the JSON file
        with open("toddler_activities_dataset.json", "r") as file:
            activities = json.load(file)

        print(f"Found {len(activities)} activities to import")

        # Transform data to match our table schema
        formatted_activities = []
        for activity in activities:
            formatted_activities.append({
                "activity_name": activity["activity_name"],
                "activity_category": activity["activity_category"],
                "materials": activity["materials"],
                "age_range_min": activity["age_range"]["min"],
                "age_range_max": activity["age_range"]["max"],
                "duration_minutes": activity["duration_minutes"],
                "prep_time_minutes": activity["prep_time_minutes"],
                "description": activity["description"],
                "parent_instruction": activity["parent_instruction"],
                "variations": activity["variations"]
            })

        # Insert data into Supabase
        result = supabase.table("activities").insert(formatted_activities).execute()

        # Print success message with count of inserted rows
        print(f"Successfully imported {len(formatted_activities)} activities!")
        return True

    except Exception as e:
        print(f"Error importing activities: {str(e)}")
        return False

if __name__ == "__main__":
    # Check if environment variables are set
    if supabase_url == "your_supabase_url" or supabase_key == "your_supabase_anon_key":
        print("Please set your SUPABASE_URL and SUPABASE_KEY environment variables")
        print("Or update the values directly in the script")
        exit(1)

    # Execute the load function
    load_activities()