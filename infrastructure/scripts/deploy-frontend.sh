#!/bin/bash
set -e

# Configuration
AWS_REGION=${AWS_REGION:-us-east-2}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}
S3_BUCKET="fitnesse-frontend-${AWS_ACCOUNT_ID}"

echo "🚀 Deploying Fitnesse Frontend to AWS S3/CloudFront"
echo "Region: ${AWS_REGION}"
echo "S3 Bucket: ${S3_BUCKET}"
echo ""

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"

# Check if npm is available
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install Node.js and npm."
    exit 1
fi

# Get CloudFront domain for API URL (API requests go through CloudFront)
echo "🔍 Getting CloudFront domain..."
CLOUDFRONT_DOMAIN=$(aws cloudfront list-distributions \
    --query "DistributionList.Items[?Comment=='fitnesse frontend distribution'].DomainName" \
    --output text \
    --region ${AWS_REGION})

if [ -z "$CLOUDFRONT_DOMAIN" ]; then
    echo "⚠️  CloudFront distribution not found. Using default API URL."
    API_URL="http://localhost:8000"
else
    # API requests go through CloudFront at /api/* path
    API_URL="https://${CLOUDFRONT_DOMAIN}"
    echo "✅ Using API URL: ${API_URL}"
fi

# Build frontend with API URL
echo "🔨 Building frontend..."
cd ${FRONTEND_DIR}
VITE_API_BASE_URL="${API_URL}" npm run build

if [ ! -d "dist" ]; then
    echo "❌ Build failed - dist directory not found"
    exit 1
fi

# Upload to S3
echo "⬆️  Uploading to S3..."
aws s3 sync dist/ s3://${S3_BUCKET} \
    --delete \
    --cache-control "public, max-age=31536000, immutable" \
    --exclude "*.html" \
    --exclude "*.json"

# Upload HTML files with shorter cache
aws s3 sync dist/ s3://${S3_BUCKET} \
    --delete \
    --cache-control "public, max-age=0, must-revalidate" \
    --include "*.html" \
    --include "*.json"

# Get CloudFront distribution ID
echo "🔍 Finding CloudFront distribution..."
DISTRIBUTION_ID=$(aws cloudfront list-distributions \
    --query "DistributionList.Items[?Comment=='fitnesse frontend distribution'].Id" \
    --output text \
    --region ${AWS_REGION})

if [ -z "$DISTRIBUTION_ID" ]; then
    echo "⚠️  CloudFront distribution not found. Skipping cache invalidation."
else
    echo "🔄 Invalidating CloudFront cache..."
    INVALIDATION_ID=$(aws cloudfront create-invalidation \
        --distribution-id ${DISTRIBUTION_ID} \
        --paths "/*" \
        --query "Invalidation.Id" \
        --output text \
        --region ${AWS_REGION})
    
    echo "✅ Cache invalidation created: ${INVALIDATION_ID}"
    echo "⏳ This may take a few minutes to complete..."
fi

echo ""
echo "🎉 Frontend deployment complete!"
echo "🌐 Your site will be available at the CloudFront URL shortly."


