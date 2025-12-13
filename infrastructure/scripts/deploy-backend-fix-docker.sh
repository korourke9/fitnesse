#!/bin/bash
# Alternative deployment script that handles Docker issues

set -e

AWS_REGION=${AWS_REGION:-us-east-2}
# Get account ID from AWS if not set
if [ -z "$AWS_ACCOUNT_ID" ]; then
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        echo "❌ AWS_ACCOUNT_ID not set and could not be determined from AWS CLI"
        echo "Please set AWS_ACCOUNT_ID environment variable or configure AWS CLI"
        exit 1
    fi
fi
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/fitnesse-backend"
IMAGE_TAG=${IMAGE_TAG:-latest}

echo "🚀 Deploying Fitnesse Backend to AWS ECS"
echo "Region: ${AWS_REGION}"
echo "Account: ${AWS_ACCOUNT_ID}"
echo ""

# Check Docker
if ! docker info > /dev/null 2>&1; then
    echo "⚠️  Docker daemon not responding. Trying to fix..."
    echo "Please ensure Docker Desktop is running and try again."
    echo ""
    echo "You can also try:"
    echo "  - Restart Docker Desktop"
    echo "  - Check Docker Desktop status in the menu bar"
    exit 1
fi

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Login to ECR (without custom DOCKER_CONFIG to avoid issues)
echo "📦 Logging in to Amazon ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${ECR_REPO} 2>&1 | \
    grep -v "error storing credentials" || true

# Build Docker image for linux/amd64 (ECS Fargate architecture)
echo "🔨 Building Docker image for linux/amd64..."
cd ${PROJECT_ROOT}

# Use buildx to build for linux/amd64 and push directly
# Use the default desktop-linux builder which supports multi-platform builds
echo "Building and pushing with buildx for linux/amd64..."

# Verify buildx is available
if ! command -v docker > /dev/null 2>&1; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

# Try buildx first (preferred method for cross-platform builds)
if docker buildx version > /dev/null 2>&1; then
    echo "Using Docker buildx for cross-platform build..."
    docker buildx build \
        --platform linux/amd64 \
        --file "${PROJECT_ROOT}/infrastructure/docker/Dockerfile" \
        --tag "${ECR_REPO}:${IMAGE_TAG}" \
        --push \
        "${PROJECT_ROOT}"
else
    echo "⚠️  Docker buildx not available. Using standard docker build..."
    echo "Note: This may not work correctly on ARM64 Macs for ECS Fargate (AMD64)"
    echo "Consider installing/updating Docker Desktop to get buildx support."
    
    # Fallback: try with DOCKER_DEFAULT_PLATFORM (may not work on all Docker versions)
    DOCKER_DEFAULT_PLATFORM=linux/amd64 docker build \
        -f "${PROJECT_ROOT}/infrastructure/docker/Dockerfile" \
        -t "${ECR_REPO}:${IMAGE_TAG}" \
        "${PROJECT_ROOT}" || {
        echo "❌ Standard docker build failed. Please use Docker Desktop with buildx support."
        exit 1
    }
    docker push "${ECR_REPO}:${IMAGE_TAG}"
fi

# Image is already pushed by buildx above

# Force ECS service update
echo "🔄 Updating ECS service..."
aws ecs update-service \
    --cluster fitnesse-cluster \
    --service fitnesse-backend-service \
    --force-new-deployment \
    --region ${AWS_REGION} > /dev/null

echo ""
echo "✅ Backend deployment initiated!"
echo "⏳ Waiting for service to stabilize (this may take a few minutes)..."
aws ecs wait services-stable \
    --cluster fitnesse-cluster \
    --services fitnesse-backend-service \
    --region ${AWS_REGION} || echo "⚠️  Service may still be starting. Check ECS console."

echo ""
echo "🎉 Backend deployment complete!"


