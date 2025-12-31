#!/bin/bash
# Quick setup script for local development

set -e

echo "🚀 Setting up local development environment..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"

# Start PostgreSQL
echo "📦 Starting PostgreSQL container..."
cd ${PROJECT_ROOT}
docker-compose up -d postgres

echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 3

# Check if .env exists
if [ ! -f "${BACKEND_DIR}/.env" ]; then
    echo "📝 Creating .env file..."
    cat > "${BACKEND_DIR}/.env" << EOF
# Database - Local PostgreSQL via Docker Compose
DATABASE_URL=postgresql://fitnesse:fitnesse_dev_password@localhost:5432/fitnesse

# Application
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
EOF
    echo "✅ Created .env file"
else
    echo "✅ .env file already exists"
    echo "⚠️  Make sure DATABASE_URL points to local PostgreSQL if testing migrations"
fi

# Check if virtual environment exists
if [ ! -d "${BACKEND_DIR}/venv" ]; then
    echo "📦 Creating virtual environment..."
    cd ${BACKEND_DIR}
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

echo ""
echo "✅ Local development environment is ready!"
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: cd backend && source venv/bin/activate"
echo "  2. Run migrations: alembic upgrade head"
echo "  3. Configure AWS credentials (for Bedrock):"
echo "     - Run: aws configure"
echo "     - Or set: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
echo "  4. Start backend: uvicorn app.main:app --reload"
echo ""
echo "To stop PostgreSQL: docker-compose down"
echo "To view PostgreSQL logs: docker-compose logs -f postgres"

