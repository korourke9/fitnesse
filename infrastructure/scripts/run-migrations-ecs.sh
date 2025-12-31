#!/bin/bash
# Script to run database migrations using a one-off ECS task

set -e

AWS_REGION=${AWS_REGION:-us-east-2}
CLUSTER_NAME="fitnesse-cluster"
TASK_DEFINITION="fitnesse-backend"
SUBNET_ID=""  # Will be fetched from ECS service
SECURITY_GROUP_ID=""  # Will be fetched from ECS service

echo "🔄 Running database migrations via ECS task..."
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

if [ -z "$SUBNET_ID" ] || [ "$SUBNET_ID" == "null" ]; then
    echo "❌ Failed to get subnet ID from ECS service"
    exit 1
fi

echo "✅ Using subnet: ${SUBNET_ID}"
echo "✅ Using security group: ${SECURITY_GROUP_ID}"
echo ""

# Get the task definition ARN
echo "📦 Getting task definition..."
TASK_DEF_ARN=$(aws ecs describe-services \
    --cluster ${CLUSTER_NAME} \
    --services fitnesse-backend-service \
    --region ${AWS_REGION} \
    --query 'services[0].taskDefinition' \
    --output text)

if [ -z "$TASK_DEF_ARN" ]; then
    echo "❌ Failed to get task definition"
    exit 1
fi

echo "✅ Task definition: ${TASK_DEF_ARN}"
echo ""

# Get database URL for the migration task
echo "📦 Retrieving database URL from Secrets Manager..."
DATABASE_URL=$(aws secretsmanager get-secret-value \
    --secret-id fitnesse-database-url \
    --region ${AWS_REGION} \
    --query SecretString \
    --output text)

if [ -z "$DATABASE_URL" ]; then
    echo "❌ Failed to retrieve database URL"
    exit 1
fi

# Run the migration task
echo "🚀 Starting migration task..."
TASK_ARN=$(aws ecs run-task \
    --cluster ${CLUSTER_NAME} \
    --task-definition ${TASK_DEF_ARN} \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_ID}],securityGroups=[${SECURITY_GROUP_ID}],assignPublicIp=ENABLED}" \
    --overrides "{
        \"containerOverrides\": [{
            \"name\": \"backend\",
            \"command\": [\"alembic\", \"upgrade\", \"head\"],
            \"environment\": [{\"name\": \"DATABASE_URL\", \"value\": \"${DATABASE_URL}\"}]
        }]
    }" \
    --region ${AWS_REGION} \
    --query 'tasks[0].taskArn' \
    --output text)

if [ -z "$TASK_ARN" ] || [ "$TASK_ARN" == "None" ]; then
    echo "❌ Failed to start migration task"
    exit 1
fi

echo "✅ Migration task started: ${TASK_ARN}"
# Extract task ID from ARN (format: arn:aws:ecs:region:account:task/cluster/task-id)
TASK_ID=$(echo ${TASK_ARN} | cut -d'/' -f3)
echo "⏳ Waiting for task to complete (Task ID: ${TASK_ID})..."

# Wait for task to complete
aws ecs wait tasks-stopped \
    --cluster ${CLUSTER_NAME} \
    --tasks ${TASK_ARN} \
    --region ${AWS_REGION}

# Get task exit code
EXIT_CODE=$(aws ecs describe-tasks \
    --cluster ${CLUSTER_NAME} \
    --tasks ${TASK_ARN} \
    --region ${AWS_REGION} \
    --query 'tasks[0].containers[0].exitCode' \
    --output text)

# Get logs - find log stream for this specific task
echo ""
echo "📋 Migration task logs:"
# Log stream format is typically: ecs/container-name/task-id
# Try multiple possible log stream name formats
LOG_STREAM=$(aws logs describe-log-streams \
    --log-group-name /ecs/fitnesse \
    --log-stream-name-prefix "ecs/backend/${TASK_ID}" \
    --region ${AWS_REGION} \
    --query 'logStreams[0].logStreamName' \
    --output text 2>/dev/null)

# If not found, try without the ecs/ prefix
if [ -z "$LOG_STREAM" ] || [ "$LOG_STREAM" == "None" ]; then
    LOG_STREAM=$(aws logs describe-log-streams \
        --log-group-name /ecs/fitnesse \
        --log-stream-name-prefix "backend/${TASK_ID}" \
        --region ${AWS_REGION} \
        --query 'logStreams[0].logStreamName' \
        --output text 2>/dev/null)
fi

if [ -n "$LOG_STREAM" ] && [ "$LOG_STREAM" != "None" ]; then
    echo "📄 Log stream: ${LOG_STREAM}"
    aws logs get-log-events \
        --log-group-name /ecs/fitnesse \
        --log-stream-name "${LOG_STREAM}" \
        --region ${AWS_REGION} \
        --query 'events[*].message' \
        --output text 2>/dev/null | tail -30
else
    # Fallback: get most recent log streams and check for our task
    echo "📄 Searching for task logs..."
    aws logs tail /ecs/fitnesse --since 5m --region ${AWS_REGION} --format short 2>/dev/null | grep -A 10 -B 5 "${TASK_ID}\|alembic\|migration\|upgrade" | tail -30 || \
    aws logs tail /ecs/fitnesse --since 5m --region ${AWS_REGION} --format short 2>/dev/null | tail -30
fi

if [ "$EXIT_CODE" == "0" ]; then
    echo ""
    echo "✅ Migrations completed successfully!"
else
    echo ""
    echo "❌ Migration task failed with exit code: ${EXIT_CODE}"
    echo "Check the logs above for details."
    exit 1
fi

