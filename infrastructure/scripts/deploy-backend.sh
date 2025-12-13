#!/bin/bash
set -ex

# Configuration
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

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Login to ECR
echo "📦 Logging in to Amazon ECR..."
# Login to ECR using default Docker config
# We'll handle the credential helper error by grepping it out
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${ECR_REPO} 2>&1 | grep -v "error storing credentials" || true

# Build Docker image for linux/amd64 (ECS Fargate architecture)
echo "🔨 Building Docker image for linux/amd64..."
cd ${PROJECT_ROOT}

# Use buildx to build for linux/amd64 and push directly
# Note: Using default Docker config (DOCKER_CONFIG not set) so buildx works properly
echo "Building and pushing with buildx for linux/amd64..."
docker buildx build \
    --platform linux/amd64 \
    --file ${PROJECT_ROOT}/infrastructure/docker/Dockerfile \
    --tag ${ECR_REPO}:${IMAGE_TAG} \
    --push \
    ${PROJECT_ROOT}

# Force ECS service update
echo "🔄 Updating ECS service..."
aws ecs update-service \
    --cluster fitnesse-cluster \
    --service fitnesse-backend-service \
    --force-new-deployment \
    --region ${AWS_REGION} > /dev/null

echo ""
echo "✅ Backend deployment initiated!"
echo "⏳ Waiting for service to stabilize..."
aws ecs wait services-stable \
    --cluster fitnesse-cluster \
    --services fitnesse-backend-service \
    --region ${AWS_REGION}

echo ""
echo "🎉 Backend deployment complete!"

