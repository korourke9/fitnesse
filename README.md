# Fitnesse

AI-driven personalized fitness and nutrition application that helps users get personalized diet and exercise recommendations based on their goals, biometric indicators, and lifestyle constraints.

## Project Structure

```
fitnesse/
├── frontend/          # React + Vite frontend
├── backend/           # FastAPI backend
├── infrastructure/    # Infrastructure as Code (Terraform/CDK)
└── docs/              # Documentation
```

## Getting Started

### Prerequisites

- Node.js 20.19+ or 22.12+
- Python 3.13+
- PostgreSQL 14+

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`

### Backend Setup

1. Create a virtual environment:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Set up the database:
```bash
# Create database
createdb fitnesse

# Run migrations
alembic upgrade head
```

5. Run the development server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`
API documentation at `http://localhost:8000/docs`

## Development

### Frontend
- Built with React 19 + TypeScript
- Styled with Tailwind CSS
- Uses Vite for fast development

### Backend
- Built with FastAPI
- Uses SQLAlchemy for database ORM
- Uses Alembic for database migrations

## License

MIT

