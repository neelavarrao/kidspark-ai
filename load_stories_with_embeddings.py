import json
import os
import time
from supabase import create_client
from openai import OpenAI

# Initialize Supabase client

from dotenv import load_dotenv

# Load environment variables
load_dotenv()
supabase_url = os.environ.get("SUPABASE_URL", "your_supabase_url")
supabase_key = os.environ.get("SUPABASE_KEY", "your_supabase_anon_key")

# Initialize OpenAI client
openai_api_key = os.environ.get("OPENAI_API_KEY", "your_openai_api_key")

# Create clients
supabase = create_client(supabase_url, supabase_key)
openai_client = OpenAI(api_key=openai_api_key)

def generate_embedding(text):
    """Generate an embedding for the given text using OpenAI API"""
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        # Extract the embedding from the response
        embedding = response.data[0].embedding
        return embedding
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        return None

def load_stories():
    try:
        # Read the JSON file
        with open("./data/bedtime_stories_dataset.json", "r") as file:
            stories = json.load(file)

        print(f"Found {len(stories)} stories to import")

        # Transform data to match our table schema
        formatted_stories = []

        for idx, story in enumerate(stories):
            print(f"Processing story {idx + 1}/{len(stories)}: {story['story_title']}")

            # Combine text fields for embedding
            text_for_embedding = f"{story['story_text']} {story['moral_lesson']} {story['lesson_summary']}"

            # Generate embedding
            embedding = generate_embedding(text_for_embedding)

            if embedding:
                formatted_stories.append({
                    "story_title": story["story_title"],
                    "moral_lesson": story["moral_lesson"],
                    "lesson_summary": story["lesson_summary"],
                    "age_range_min": story["age_range"]["min"],
                    "age_range_max": story["age_range"]["max"],
                    "characters": story["characters"],
                    "setting": story["setting"],
                    "duration_minutes": story["duration_minutes"],
                    "story_text": story["story_text"],
                    "discussion_questions": story["discussion_questions"],
                    "embedding": embedding
                })
                # Add a small delay to avoid rate limits
                time.sleep(0.5)
            else:
                print(f"Skipping story {story['story_title']} due to embedding error")

        # Check if we have stories to insert
        if not formatted_stories:
            print("No stories to insert after embedding generation")
            return False

        # Insert data into Supabase
        result = supabase.table("stories").insert(formatted_stories).execute()

        print(f"Successfully imported {len(formatted_stories)} stories with embeddings!")
        return True

    except Exception as e:
        print(f"Error importing stories: {str(e)}")
        return False

if __name__ == "__main__":
    # Check if environment variables are set
    missing_vars = []
    if supabase_url == "your_supabase_url":
        missing_vars.append("SUPABASE_URL")
    if supabase_key == "your_supabase_anon_key":
        missing_vars.append("SUPABASE_KEY")
    if openai_api_key == "your_openai_api_key":
        missing_vars.append("OPENAI_API_KEY")

    if missing_vars:
        print(f"Please set the following environment variables: {', '.join(missing_vars)}")
        print("Or update the values directly in the script")
        exit(1)

    # Execute the load function
    load_stories()