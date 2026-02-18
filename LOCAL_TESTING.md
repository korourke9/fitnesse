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

Chat agents (Nutritionist, Trainer) and plan generation use AWS Bedrock. Configure credentials first:

**Option A – SSO / temporary credentials (e.g. `aws login`):**
```bash
aws login
# or: aws sso login
# Restart the backend after logging in. Credentials expire; re-run when you see "session has expired".
```

**Option B – Long‑lived keys:**
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

**"Your session has expired or credentials have changed. Please reauthenticate using 'aws login'"**

If you use AWS SSO or temporary credentials, they expire. Re-authenticate:

```bash
aws login
# or, for SSO:
aws sso login
```

Then restart the backend so it picks up the new credentials.

**Other Bedrock issues**
- Verify AWS credentials: `aws sts get-caller-identity`
- Check Bedrock is enabled in your AWS account and in the same region as `AWS_REGION`
- Verify model ID in `.env` or config (e.g. `anthropic.claude-3-5-sonnet-20241022-v2:0`)
- Ensure your IAM user/role has `bedrock:InvokeModel` (and optional `bedrock:InvokeModelWithResponseStream`) for the model you use

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

