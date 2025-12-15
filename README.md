# KidSpark AI

KidSpark AI is an intelligent parenting assistant that combines three essential child-focused capabilities:

1. **Activity Suggester** - Context-aware activity recommendations
2. **Bedtime Story Generator** - Personalized, age-appropriate stories
3. **"Why?" Question Answerer** - Child-friendly explanations for curious minds

This repository contains Phase 1 of the KidSpark AI application, focusing on user authentication and a basic chat interface.

## Project Structure

```
app/
├── backend/
│   ├── models/       # Pydantic models
│   ├── routers/      # API routes
│   ├── services/     # Service layer
│   └── main.py       # FastAPI application
├── frontend/
│   ├── static/
│   │   ├── css/      # Stylesheets
│   │   └── js/       # JavaScript files
│   └── templates/    # HTML templates
supabase/
└── create_users_table.sql    # SQL script to create users table
```

## Prerequisites

- Python 3.8+
- Supabase account with project set up
- Environment variables configured

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
OPENAI_API_KEY=your_openai_api_key
SUPABASE_ACCESS_TOKEN=your_supabase_access_token
SUPABASE_PROJECT_REF=your_supabase_project_ref
```

## Database Setup

1. Log in to your Supabase dashboard
2. Navigate to the SQL Editor
3. Execute the SQL scripts from the `supabase` directory:
   - `create_users_table.sql` - Creates the users table
   - `create_chat_messages_table.sql` - Creates the chat messages table

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/kidspark.git
cd kidspark
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

```bash
uvicorn app.backend.main:app --reload
```

The application will be available at http://127.0.0.1:8000

## Usage

### Registration
1. Navigate to http://127.0.0.1:8000/register
2. Fill in your details to create an account
3. You will be automatically logged in and redirected to the chat interface

### Login
1. Navigate to http://127.0.0.1:8000/
2. Enter your email and password
3. Upon successful login, you will be redirected to the chat interface

### Chat Interface
1. Type your message in the input field
2. Press Enter or click Send to submit your message
3. The AI assistant will respond with a helpful message

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/register` | POST | Register a new user |
| `/api/token` | POST | Login and get access token |
| `/api/users/me` | GET | Get current user profile |
| `/api/chat/messages` | POST | Send a message |
| `/api/chat/messages/history` | GET | Get chat history |
| `/api/chat/ws/{client_id}` | WebSocket | Real-time chat connection |

## Next Steps (Future Phases)

- Implement the Activity Suggester Agent
- Implement the Bedtime Story Generator Agent
- Implement the "Why?" Question Answerer Agent
- Add user profiles for multiple children
- Enhance guardrails implementation
- Develop mobile interface
- Add voice interface support

## License

MIT