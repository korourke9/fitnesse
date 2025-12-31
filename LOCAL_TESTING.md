# Local Testing Guide

## Quick Start

### 1. Run the Setup Script
```bash
cd fitnesse
./backend/scripts/dev-setup.sh
```

This script will:
- Start PostgreSQL in Docker
- Create/verify your `.env` file
- Create/verify your Python virtual environment
- Install backend dependencies

### 2. Run Database Migrations
```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

### 3. Start Backend
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at: **http://localhost:8000**
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### 4. Start Frontend (in a new terminal)
```bash
cd frontend
npm run dev
```

The frontend will be available at: **http://localhost:5173**

## Testing the Onboarding Agent

1. Open http://localhost:5173 in your browser
2. You'll be redirected to the onboarding page
3. Start chatting! The agent will:
   - Have natural conversations
   - Extract your information (goals, biometrics, lifestyle)
   - Save data to the database automatically

## Prerequisites

- Docker Desktop installed and running
- Node.js 20.19+ or 22.12+ installed
- Python 3.13+ installed
- AWS credentials configured for Bedrock access

The `dev-setup.sh` script will handle:
- ✅ Starting PostgreSQL (via Docker Compose)
- ✅ Creating `.env` file with local database configuration
- ✅ Creating Python virtual environment
- ✅ Installing backend dependencies

You'll still need to:
- ✅ Run database migrations (`alembic upgrade head`)
- ✅ Install frontend dependencies (`npm install` in `frontend/` directory)

## AWS Credentials

Make sure you have AWS credentials configured for Bedrock access:

```bash
aws configure
# Or set environment variables:
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-2
```

## Troubleshooting

### Backend won't start
- Check PostgreSQL is running: `docker-compose ps`
- Check `.env` file exists with correct `DATABASE_URL`
- Check migrations: `alembic current`

### Frontend can't connect to backend
- Verify backend is running on port 8000
- Check browser console for CORS errors
- Verify `VITE_API_BASE_URL` is not set (should use default `http://localhost:8000`)

### Bedrock errors
- Verify AWS credentials are configured
- Check Bedrock is enabled in your AWS account
- Verify model ID is correct: `anthropic.claude-3-5-sonnet-20241022-v2:0`
- Check you have permissions to invoke Bedrock models

## Viewing Data

To see what data was saved:

```bash
cd backend
source venv/bin/activate
python -c "
from app.core.database import engine
from app.models.user_profile import UserProfile
from app.models.goal import Goal
from sqlalchemy.orm import sessionmaker

Session = sessionmaker(bind=engine)
db = Session()

profile = db.query(UserProfile).filter(UserProfile.user_id == 'temp-user-123').first()
if profile:
    print('Profile:', profile.__dict__)

goals = db.query(Goal).filter(Goal.user_id == 'temp-user-123').all()
for goal in goals:
    print(f'Goal: {goal.description} - {goal.target}')
"
```

