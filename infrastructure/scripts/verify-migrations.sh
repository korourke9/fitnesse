#!/bin/bash
# Script to verify database migrations by checking if tables exist

set -e

AWS_REGION=${AWS_REGION:-us-east-2}
CLUSTER_NAME="fitnesse-cluster"
SECRET_NAME="fitnesse-database-url"

echo "🔍 Verifying database migrations..."
echo ""

# Get database URL from Secrets Manager
echo "📦 Retrieving database URL from Secrets Manager..."
DATABASE_URL=$(aws secretsmanager get-secret-value \
    --secret-id ${SECRET_NAME} \
    --region ${AWS_REGION} \
    --query SecretString \
    --output text)

if [ -z "$DATABASE_URL" ]; then
    echo "❌ Failed to retrieve database URL"
    exit 1
fi

# Extract database connection info
DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
DB_USER=$(echo $DATABASE_URL | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
DB_PASS=$(echo $DATABASE_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

echo "✅ Database connection info retrieved"
echo ""

# Get subnet and security group from the ECS service
echo "📦 Getting network configuration from ECS service..."
SERVICE_INFO=$(aws ecs describe-services \
    --cluster ${CLUSTER_NAME} \
    --services fitnesse-backend-service \
    --region ${AWS_REGION} \
    --query 'services[0].{Subnets:networkConfiguration.awsvpcConfiguration.subnets[0],SecurityGroups:networkConfiguration.awsvpcConfiguration.securityGroups[0]}' \
    --output json)

SUBNET_ID=$(echo $SERVICE_INFO | jq -r '.Subnets')
SECURITY_GROUP_ID=$(echo $SERVICE_INFO | jq -r '.SecurityGroups')

# Get the task definition ARN
TASK_DEF_ARN=$(aws ecs describe-services \
    --cluster ${CLUSTER_NAME} \
    --services fitnesse-backend-service \
    --region ${AWS_REGION} \
    --query 'services[0].taskDefinition' \
    --output text)

# Run a verification task
echo "🚀 Starting verification task..."
TASK_ARN=$(aws ecs run-task \
    --cluster ${CLUSTER_NAME} \
    --task-definition ${TASK_DEF_ARN} \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_ID}],securityGroups=[${SECURITY_GROUP_ID}],assignPublicIp=ENABLED}" \
    --overrides "{
        \"containerOverrides\": [{
            \"name\": \"backend\",
            \"command\": [\"python\", \"-c\", \"from sqlalchemy import create_engine, inspect; import os; engine = create_engine(os.environ['DATABASE_URL']); inspector = inspect(engine); tables = inspector.get_table_names(); print('Tables found:', ', '.join(tables) if tables else 'No tables found'); expected = ['users', 'conversations', 'messages', 'alembic_version']; missing = [t for t in expected if t not in tables]; print('Expected tables:', ', '.join(expected)); print('Missing tables:', ', '.join(missing) if missing else 'None'); exit(0 if not missing else 1)\"],
            \"environment\": [{\"name\": \"DATABASE_URL\", \"value\": \"${DATABASE_URL}\"}]
        }]
    }" \
    --region ${AWS_REGION} \
    --query 'tasks[0].taskArn' \
    --output text)

if [ -z "$TASK_ARN" ] || [ "$TASK_ARN" == "None" ]; then
    echo "❌ Failed to start verification task"
    exit 1
fi

echo "✅ Verification task started: ${TASK_ARN}"
echo "⏳ Waiting for task to complete..."

# Wait for task to complete
aws ecs wait tasks-stopped \
    --cluster ${CLUSTER_NAME} \
    --tasks ${TASK_ARN} \
    --region ${AWS_REGION}

# Get logs
echo ""
echo "📋 Verification results:"
aws logs tail /aws/ecs/fitnesse-backend --since 2m --region ${AWS_REGION} --format short | grep -E "(Tables found|Expected tables|Missing tables)" | tail -5

# Get task exit code
EXIT_CODE=$(aws ecs describe-tasks \
    --cluster ${CLUSTER_NAME} \
    --tasks ${TASK_ARN} \
    --region ${AWS_REGION} \
    --query 'tasks[0].containers[0].exitCode' \
    --output text)

if [ "$EXIT_CODE" == "0" ]; then
    echo ""
    echo "✅ All expected tables exist!"
else
    echo ""
    echo "⚠️  Some tables may be missing. Check the logs above."
fi

