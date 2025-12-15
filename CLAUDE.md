# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KidSpark AI is an intelligent parenting assistant built with FastAPI that provides three core features:
1. **Activity Suggester** - Context-aware activity recommendations for children
2. **Bedtime Story Generator** - Personalized, age-appropriate stories
3. **"Why?" Question Answerer** - Child-friendly explanations for curious minds

The project is currently in Phase 1, focused on user authentication and basic chat interface. The agent functionality is under development.

## Development Commands

### Setup and Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Start the application (development mode)
uvicorn app.backend.main:app --reload --host 0.0.0.0 --port 8000

# Or use the convenience script
bash start_app.sh
```

### Environment Configuration

Create a `.env` file in the root directory with the following variables:

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
OPENAI_API_KEY=your_openai_api_key
SUPABASE_ACCESS_TOKEN=your_supabase_access_token
SUPABASE_PROJECT_REF=your_supabase_project_ref
```

## Architecture Overview

### Directory Structure

```
app/
├── backend/
│   ├── models/       # Pydantic models
│   ├── routers/      # API routes
│   ├── services/     # Service layer
│   ├── agents/       # AI agents
│   └── main.py       # FastAPI application
├── frontend/
│   ├── static/
│   │   ├── css/      # Stylesheets
│   │   └── js/       # JavaScript files
│   └── templates/    # HTML templates
supabase/
└── *.sql             # SQL scripts for database setup
```

### Key Components

1. **FastAPI Backend**
   - User authentication with JWT
   - API endpoints for chat and agent interactions
   - WebSocket support for real-time chat

2. **Agent System**
   - Intent router to classify user requests
   - Specialized agents for activities, stories, and questions (under development)
   - Initial implementation uses OpenAI's API

3. **Supabase Integration**
   - PostgreSQL database for user data and chat history
   - Row-level security for data protection
   - Future: Vector database for RAG implementation

4. **Frontend**
   - Simple HTML/CSS/JS interface
   - Authentication flows (login/register)
   - Chat interface with real-time updates
   - Story viewer with reading mode

## Implementation Details

### Authentication Flow

The application uses JWT-based authentication:
1. User registers via `/api/register` endpoint
2. User logs in via `/api/token` endpoint, receiving a JWT
3. JWT is used for subsequent authenticated requests
4. Protected routes use the `get_current_user` dependency

### Intent Classification

The system classifies user messages into intents:
1. `IntentRouter` class determines what the user is asking for
2. Uses regex patterns and LLM classification as fallback
3. Maps to `IntentType` enum: ACTIVITY, STORY, WHY, GREETING, or UNKNOWN
4. Each intent routes to a specialized agent (when implemented)

### Agent Processing Pipeline

1. Detect user intent via `IntentRouter`
2. Route to appropriate specialized agent based on intent
3. Apply input guardrails (planned)
4. Process with agent-specific logic
5. Apply output guardrails (planned)
6. Return response to user

### Database Schema

**Users Table:**
- id (UUID)
- email (VARCHAR, unique)
- name (VARCHAR)
- password (VARCHAR)
- created_at (TIMESTAMPTZ)

**Chat Messages Table:**
- id (UUID)
- user_id (UUID, foreign key to users)
- content (TEXT)
- sender (VARCHAR) - 'user' or 'assistant'
- timestamp (TIMESTAMPTZ)

## Future Development Areas

The codebase is in Phase 1, with several areas for future implementation:

1. **Agent Implementation**
   - Complete the specialized agent implementations
   - Implement RAG pipeline with vector search
   - Add guardrails for child-appropriate content

2. **Enhanced Security**
   - Password hashing (currently stored in plaintext)
   - Improved JWT handling with refresh tokens
   - Rate limiting implementation

3. **Frontend Enhancements**
   - Mobile-responsive design improvements
   - Activity and explanation visualizations
   - User profiles for multiple children

4. **Monitoring and Analytics**
   - Implement logging for intent detection
   - Add metrics for agent performance
   - Create user engagement analytics

## Development Best Practices

When working on this codebase:

1. **Intent Classification**
   - Keep intent patterns updated in `IntentRouter` class
   - Maintain high-confidence thresholds for accuracy

2. **Agent Implementation**
   - Follow the existing pattern of specialized agents
   - Ensure all output is child-appropriate
   - Implement robust error handling

3. **Frontend Modifications**
   - Maintain the responsive design
   - Follow existing CSS patterns and variables
   - Update JavaScript event listeners for new features

4. **Testing**
   - Test intent classification with diverse inputs
   - Verify agent responses for appropriateness
   - Check WebSocket performance for real-time chat